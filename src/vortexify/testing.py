"""Mock-based tests for imported transform and API modules.

The platform owns module imports and worker isolation. This runner executes tests
serially in the current process so normal Python monkey-patching works.
"""

import inspect
import time
import traceback
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, ClassVar, Iterable, Literal

import pandas as pd
from pydantic import BaseModel, Field

from .database import Database, DatabaseTable
from .types.definitions import TestDefinition
from .types.inputs import Input, Secret, Table, TransformOutput

__all__ = [
    "vxfy_mocks", "vxfy_test", "discover_tests", "run_tests",
    "TestingSuite", "TestResult", "TestError",
]


def _sync_function(func):
    if not inspect.isfunction(func) or inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func) or inspect.isgeneratorfunction(func):
        raise TypeError("Expected a synchronous Python function, not a generator.")


def vxfy_mocks(func):
    """Register a zero-argument factory returning a dictionary of mock inputs."""
    _sync_function(func)
    inspect.signature(func).bind()
    func.__vxfy_type__ = "mocks"
    return func


def vxfy_test(*, mocks):
    """Register a test accepting run(), associated with a @vxfy_mocks factory."""
    if getattr(mocks, "__vxfy_type__", None) != "mocks":
        raise TypeError("mocks must reference a @vxfy_mocks function.")

    def decorate(func):
        _sync_function(func)
        inspect.signature(func).bind(run=lambda: None)
        func.__vxfy_type__ = "test"
        func.__vxfy_definition__ = TestDefinition(mocks=mocks)
        # These tests require our run callable, rather than a pytest fixture.
        func.__test__ = False
        return func

    return decorate


def _name(func):
    return f"{func.__module__}.{func.__qualname__}"


@dataclass(frozen=True)
class TestingSuite:
    """Discovered functions, deduplicated across imported module namespaces."""

    __test__: ClassVar[bool] = False
    resources: tuple[Callable, ...]
    mocks: tuple[Callable, ...]
    tests: tuple[Callable, ...]


def discover_tests(modules: Iterable[ModuleType]) -> TestingSuite:
    """Inspect supplied modules; no filename conventions or global registry.

    Re-exported functions are deduplicated by identity. Associated mock factories
    are included even when their defining module isn't in modules.
    """
    found = {}
    for module in modules:
        if not isinstance(module, ModuleType):
            raise TypeError("Discovery requires imported Python modules.")
        for value in vars(module).values():
            if inspect.isfunction(value) and getattr(value, "__vxfy_type__", None) in {"api", "transform", "mocks", "test"}:
                found[id(value)] = value
                if value.__vxfy_type__ == "test":
                    factory = value.__vxfy_definition__.mocks
                    found[id(factory)] = factory
    ordered = sorted(found.values(), key=_name)
    names = [_name(func) for func in ordered]
    if len(set(names)) != len(names):
        raise ValueError("Ambiguous function identities; import modules under unique, stable names.")
    return TestingSuite(
        resources=tuple(f for f in ordered if f.__vxfy_type__ in {"api", "transform"}),
        mocks=tuple(f for f in ordered if f.__vxfy_type__ == "mocks"),
        tests=tuple(f for f in ordered if f.__vxfy_type__ == "test"),
    )


class TestError(BaseModel):
    __test__: ClassVar[bool] = False
    phase: Literal["mocks", "inputs", "resource", "test"]
    type: str
    message: str
    traceback: str


class TestResult(BaseModel):
    __test__: ClassVar[bool] = False
    name: str
    module: str
    mocks: str
    status: Literal["passed", "failed", "error"]
    duration_seconds: float
    run_count: int
    error: TestError | None = None
    # Available to an in-process caller, excluded from serializable reports.
    result: Any = Field(default=None, exclude=True, repr=False)


def _checked_return(value):
    if inspect.isawaitable(value) or inspect.isgenerator(value) or inspect.isasyncgen(value):
        if inspect.iscoroutine(value) or inspect.isgenerator(value):
            value.close()
        raise TypeError("Testing supports synchronous functions returning values.")
    return value


def _mock_inputs(definition, supplied):
    if not isinstance(supplied, dict):
        raise TypeError("Mock factory must return a dictionary of resource inputs.")
    unexpected = supplied.keys() - definition.inputs.keys()
    if unexpected:
        raise ValueError(f"Undeclared mock inputs: {sorted(unexpected, key=str)}")
    values = dict(supplied)
    for name, declaration in definition.inputs.items():
        if name not in values:
            if isinstance(declaration, Input) and (declaration.default is not None or not declaration.required):
                values[name] = declaration.default
            else:
                raise ValueError(f"Missing mock input: {name}")
        value = values[name]
        if isinstance(declaration, Input):
            if value is None and not declaration.required:
                continue
            if type(value) is not declaration.type:
                raise TypeError(f"Mock input '{name}' must be {declaration.type.__name__}.")
        elif isinstance(declaration, (Table, TransformOutput, DatabaseTable)):
            if definition.engine == "pyspark":
                from pyspark.sql import DataFrame as SparkDataFrame
                valid = isinstance(value, (pd.DataFrame, SparkDataFrame))
            else:
                valid = isinstance(value, pd.DataFrame)
            if not valid:
                raise TypeError(f"Mock input '{name}' must be a DataFrame.")
        elif isinstance(declaration, Database):
            if not any(callable(getattr(value, method, None)) for method in ("cursor", "execute")):
                raise TypeError(f"Mock input '{name}' must be a database connection or test double.")
        elif isinstance(declaration, Secret) and value is None:
            raise TypeError(f"Mock secret '{name}' cannot be None.")
    return values


def _execute(resource, values, spark_session):
    definition = resource.__vxfy_definition__
    _sync_function(resource)
    tables = {name for name, value in definition.inputs.items() if isinstance(value, (Table, TransformOutput, DatabaseTable))}
    if definition.engine == "duckdb":
        import duckdb

        if "conn" in definition.inputs:
            raise ValueError("DuckDB input name 'conn' is reserved for the injected connection.")
        with duckdb.connect(":memory:") as conn:
            for name in tables:
                conn.register(name, values[name])
            kwargs = {name: value for name, value in values.items() if name not in tables}
            result = _checked_return(resource(conn=conn, **kwargs))
            # Materialize lazy results before closing the per-run connection.
            if isinstance(result, (duckdb.DuckDBPyRelation, duckdb.DuckDBPyConnection)):
                return result.df()
            if type(result).__module__.startswith("pyarrow") and callable(getattr(result, "read_all", None)):
                return result.read_all()
            return result
    if definition.engine == "pyspark":
        for name in tables:
            if isinstance(values[name], pd.DataFrame):
                if spark_session is None:
                    raise ValueError("Pandas mocks for pyspark require a caller-supplied spark_session.")
                values[name] = spark_session.createDataFrame(values[name])
    return _checked_return(resource(**values))


def run_tests(modules: Iterable[ModuleType], *, resource=None, spark_session=None) -> list[TestResult]:
    """Run discovered tests serially, using fresh mocks on every run() call.

    Supply one transform/API, either discovered or explicitly selected. No live
    input resolution, publishing, or production validation is performed. The
    caller owns worker isolation, timeouts, imports and any Spark session.
    """
    suite = discover_tests(modules)
    if resource is None:
        if len(suite.resources) != 1:
            raise ValueError("Expected exactly one transform or API; select resource explicitly otherwise.")
        resource = suite.resources[0]
    if getattr(resource, "__vxfy_type__", None) not in {"api", "transform"}:
        raise TypeError("resource must be a @vxfy_transform or @vxfy_api function.")
    results = []
    for test in suite.tests:
        factory = test.__vxfy_definition__.mocks
        started = time.perf_counter()
        run_count = 0
        run_errors = []

        def run():
            nonlocal run_count
            run_count += 1
            phase = "mocks"
            try:
                supplied = _checked_return(factory())
                phase = "inputs"
                values = _mock_inputs(resource.__vxfy_definition__, supplied)
                phase = "resource"
                return _execute(resource, values, spark_session)
            except Exception as exc:
                # Preserve original exception types for normal assert/raises use.
                run_errors.append((exc, phase))
                raise

        status, error, result = "passed", None, None
        try:
            result = _checked_return(test(run=run))
        except Exception as exc:
            phase = next((phase for recorded, phase in run_errors if recorded is exc), "test")
            status = "failed" if phase == "test" and isinstance(exc, AssertionError) else "error"
            error = TestError(phase=phase, type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
        results.append(TestResult(
            name=test.__name__, module=test.__module__, mocks=_name(factory),
            status=status, duration_seconds=time.perf_counter() - started,
            run_count=run_count, error=error, result=result,
        ))
    return results
