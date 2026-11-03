"""Runtime contract for the SDK test worker interface."""
import sys
from types import ModuleType
from unittest.mock import patch

import duckdb
import pandas as pd
import pytest

from vortexify import Database, DatabaseTable, Input, Secret, Table, TransformOutput, vxfy_api, vxfy_transform
from vortexify.testing import discover_tests, run_tests, vxfy_mocks, vxfy_test


def module(*functions):
    result = ModuleType("resource_tests")
    result.__dict__.update({str(i): fn for i, fn in enumerate(functions)})
    return result


def check(resource, factory, body=None, **kwargs):
    factory = vxfy_mocks(factory)
    if body is None:
        def body(run):
            return run()
    test = vxfy_test(mocks=factory)(body)
    return run_tests([module(resource, test)], **kwargs)[0]


def test_fresh_mocks_repeated_execution_defaults_and_optional_inputs():
    generated = []

    @vxfy_transform(inputs={"rows": Table("shopify.upstream"), "count": Input(int, default=2), "optional": Input(str, required=False)})
    def resource(rows, count, optional):
        assert count == 2 and optional is None
        rows.loc[0, "x"] += 10
        return rows

    def factory():
        rows = pd.DataFrame({"x": [1]})
        generated.append(rows)
        return {"rows": rows}

    def body(run):
        assert run().iloc[0].x == 11
        assert run().iloc[0].x == 11

    result = check(resource, factory, body)
    assert result.status == "passed"
    assert result.run_count == 2
    assert generated[0] is not generated[1]
    assert result.duration_seconds >= 0


def test_discovery_cross_module_reexports_and_explicit_resource():
    @vxfy_api("/example")
    def resource():
        return 5

    @vxfy_mocks
    def factory():
        return {}

    @vxfy_test(mocks=factory)
    def body(run):
        assert run() == 5

    suite = discover_tests([module(body), module(body, resource)])
    assert suite.tests == (body,)
    assert suite.mocks == (factory,)
    assert suite.resources == (resource,)
    assert run_tests([module(body)], resource=resource)[0].status == "passed"

    @vxfy_api("/other")
    def other():
        pass

    with pytest.raises(ValueError, match="exactly one"):
        run_tests([module(body, resource, other)])
    with pytest.raises(ValueError, match="exactly one"):
        run_tests([module(body)])
    with pytest.raises(TypeError, match="resource must"):
        run_tests([module(body)], resource=factory)
    with pytest.raises(TypeError, match="imported"):
        discover_tests(["not_a_module"])


def test_same_process_patch_using_stable_imported_module(monkeypatch):
    target = ModuleType("sample_resource")
    monkeypatch.setitem(sys.modules, target.__name__, target)
    exec('''
from vortexify import vxfy_api
from vortexify.testing import vxfy_mocks, vxfy_test
from unittest.mock import patch

def supplier():
    return True

@vxfy_api("/supplier")
def resource():
    return supplier()

@vxfy_mocks
def factory():
    return {}

@vxfy_test(mocks=factory)
def test_outage(run):
    with patch("sample_resource.supplier", return_value=False):
        assert run() is False
    assert run() is True
''', target.__dict__)
    result = run_tests([target])[0]
    assert result.status == "passed"
    assert result.run_count == 2
    assert target.supplier() is True


@pytest.mark.parametrize("supplied, message", [
    ([], "dictionary"), ({}, "Missing mock"),
    ({"n": 2, "extra": 1}, "Undeclared"),
    ({"n": True}, "must be int"), ({"n": None}, "must be int"),
])
def test_input_validation_without_live_resolution(supplied, message):
    @vxfy_api("/n", inputs={"n": Input(int)})
    def resource(n):
        pytest.fail("Invalid mocks must not execute the resource")

    result = check(resource, lambda: supplied)
    assert result.status == "error"
    assert result.error.phase == "inputs"
    assert message in result.error.message
    assert result.error.traceback


def test_all_input_declarations_accept_explicit_mock_values():
    class FakeDB:
        def execute(self, sql):
            return "fake"

    @vxfy_transform(inputs={
        "rows": Table("shopify.source"), "previous": TransformOutput("upstream"),
        "db_rows": DatabaseTable("ops.orders"),
        "db": Database("ops", tables=["orders"]),
        "secret": Secret("token"),
    })
    def resource(rows, previous, db_rows, db, secret):
        assert all(isinstance(x, pd.DataFrame) for x in (rows, previous, db_rows))
        assert db.execute("select 1") == "fake"
        assert secret == "fake-token"
        return rows

    def factory():
        return {"rows": pd.DataFrame(), "previous": pd.DataFrame(), "db_rows": pd.DataFrame(),
                "db": FakeDB(), "secret": "fake-token"}

    result = check(resource, factory)
    assert result.status == "passed"
    assert isinstance(result.result, pd.DataFrame)
    assert '"result"' not in result.model_dump_json()


@pytest.mark.parametrize("declaration,value", [
    (Table("shopify.orders"), []),
    (Database("ops", tables=[]), "connection-string"), (Secret("secret"), None),
])
def test_invalid_managed_input_mocks(declaration, value):
    @vxfy_api("/mock", inputs={"value": declaration})
    def resource(value):
        pytest.fail("Must not reach resource")

    result = check(resource, lambda: {"value": value})
    assert result.status == "error" and result.error.phase == "inputs"


@pytest.mark.parametrize("phase,kind", [("mocks", AssertionError), ("resource", AssertionError), ("test", AssertionError), ("test", ValueError)])
def test_error_classification_and_continuation(phase, kind):
    @vxfy_api("/example")
    def resource():
        if phase == "resource":
            raise kind("oops")

    @vxfy_mocks
    def factory():
        if phase == "mocks":
            raise kind("oops")
        return {}

    @vxfy_test(mocks=factory)
    def a_fails(run):
        if phase == "test":
            raise kind("oops")
        run()

    @vxfy_test(mocks=factory)
    def z_passes(run):
        pass

    failed, passed = run_tests([module(resource, a_fails, z_passes)])
    assert failed.status == ("failed" if phase == "test" and kind is AssertionError else "error")
    assert failed.error.phase == phase
    assert failed.error.type == kind.__name__
    assert failed.error.message == "oops"
    assert passed.status == "passed" and passed.run_count == 0


def test_expected_resource_exceptions_keep_original_type():
    @vxfy_api("/example")
    def resource():
        raise ValueError("expected")

    def body(run):
        with pytest.raises(ValueError, match="expected"):
            run()

    assert check(resource, lambda: {}, body).status == "passed"


@pytest.mark.parametrize("lazy", [False, True])
def test_duckdb_registration_scalars_materialized_output_and_cleanup(lazy):
    connections = []

    @vxfy_transform(engine="duckdb", inputs={"orders": Table("shopify.different_alias"), "minimum": Input(int, default=2)})
    def resource(conn, minimum):
        connections.append(conn)
        sql = "select * from orders where amount >= ?"
        return conn.sql(sql, params=[minimum]) if lazy else conn.execute(sql, [minimum])

    def body(run):
        output = run()
        assert output.amount.tolist() == [3]

    result = check(resource, lambda: {"orders": pd.DataFrame({"amount": [1, 3]})}, body)
    assert result.status == "passed"
    with pytest.raises(duckdb.ConnectionException):
        connections[0].execute("select 1")


def test_duckdb_cleanup_on_failure():
    connections = []

    @vxfy_api("/fail", engine="duckdb")
    def resource(conn):
        connections.append(conn)
        raise RuntimeError("failure")

    assert check(resource, lambda: {}).error.phase == "resource"
    with pytest.raises(duckdb.ConnectionException):
        connections[0].execute("select 1")


def test_spark_requires_explicit_session_without_starting_jvm():
    @vxfy_transform(engine="pyspark", inputs={"rows": Table("shopify.orders")})
    def resource(rows):
        return rows

    factory = lambda: {"rows": pd.DataFrame({"n": [1]})}
    result = check(resource, factory)
    assert result.status == "error"
    assert "spark_session" in result.error.message

    class FakeSession:
        def createDataFrame(self, value):
            return ("converted", value.n.tolist())

    result = check(resource, factory, spark_session=FakeSession())
    assert result.status == "passed" and result.result == ("converted", [1])


def test_decorator_contracts_and_synchronous_only():
    with pytest.raises(TypeError, match="@vxfy_mocks"):
        vxfy_test(mocks=lambda: {})
    with pytest.raises(TypeError):
        vxfy_test(case="old-contract")
    with pytest.raises(TypeError):
        vxfy_mocks(lambda required: {})

    @vxfy_mocks
    def factory():
        return {}

    with pytest.raises(TypeError):
        vxfy_test(mocks=factory)(lambda output: None)

    async def asynchronous():
        return {}

    with pytest.raises(TypeError, match="synchronous"):
        vxfy_mocks(asynchronous)

    def generator():
        yield {}

    with pytest.raises(TypeError, match="synchronous"):
        vxfy_mocks(generator)


def test_discovery_rejects_ambiguous_module_identities():
    def make_resource():
        @vxfy_api("/example")
        def resource():
            return {}
        return resource

    first, second = make_resource(), make_resource()
    with pytest.raises(ValueError, match="Ambiguous"):
        discover_tests([module(first, second)])


def test_async_resource_is_reported_as_error_without_creating_coroutine():
    @vxfy_api("/example")
    async def resource():
        return {}

    result = check(resource, lambda: {})
    assert result.status == "error" and result.error.phase == "resource"
    assert "synchronous" in result.error.message


def test_factory_exception_remains_catchable():
    @vxfy_api("/example")
    def resource():
        pytest.fail("Factory failure should prevent execution")

    def factory():
        raise LookupError("mock failed")

    def body(run):
        with pytest.raises(LookupError, match="mock failed"):
            run()

    result = check(resource, factory, body)
    assert result.status == "passed" and result.run_count == 1
