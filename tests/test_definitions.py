import pytest
from pydantic import ValidationError

from vortexify import (
    Database,
    DatabaseTable,
    Input,
    Secret,
    Table,
    TransformOutput,
)

from vortexify.types.definitions import (
    ApiDefinition,
    TestDefinition as VortexifyTestDefinition,
    TransformDefinition,
    ValidationDefinition,
)


def test_transform_definition_defaults():
    definition = TransformDefinition()

    assert definition.engine == "pandas"
    assert definition.inputs == {}
    assert definition.schedule == []
    assert definition.compute is None


def test_transform_definition_accepts_all_input_types():
    definition = TransformDefinition(
        inputs={
            "orders": Table("shopify.orders"),
            "forecast": TransformOutput(
                "forecast"
            ),
            "database_orders": DatabaseTable("operations.orders"),
            "database": Database(
                "operations",
                tables=[
                    "orders",
                ],
            ),
            "api_key": Secret("api_key"),
            "horizon": Input(int),
        },
    )

    assert len(definition.inputs) == 6

    assert isinstance(
        definition.inputs["orders"],
        Table,
    )

    assert isinstance(
        definition.inputs["forecast"],
        TransformOutput,
    )

    assert isinstance(
        definition.inputs["database_orders"],
        DatabaseTable,
    )

    assert isinstance(
        definition.inputs["database"],
        Database,
    )

    assert isinstance(
        definition.inputs["api_key"],
        Secret,
    )

    assert isinstance(
        definition.inputs["horizon"],
        Input,
    )


def test_transform_definition_rejects_invalid_input():
    with pytest.raises(
        ValidationError,
        match="Invalid transform input",
    ):
        TransformDefinition(
            inputs={
                "orders": object(),
            },
        )


def test_transform_definition_accepts_supported_engines():
    for engine in (
        "pandas",
        "duckdb",
        "pyspark",
    ):
        definition = TransformDefinition(
            engine=engine,
        )

        assert definition.engine == engine


def test_transform_definition_rejects_invalid_engine():
    with pytest.raises(ValidationError):
        TransformDefinition(
            engine="invalid",
        )


def test_api_definition_defaults():
    definition = ApiDefinition(
        path="/orders",
    )

    assert definition.path == "/orders"
    assert definition.engine == "pandas"
    assert definition.inputs == {}
    assert definition.compute is None


def test_api_definition_accepts_supported_engines():
    for engine in (
        "pandas",
        "duckdb",
    ):
        definition = ApiDefinition(
            path="/orders",
            engine=engine,
        )

        assert definition.engine == engine


def test_api_definition_rejects_pyspark():
    with pytest.raises(ValidationError):
        ApiDefinition(
            path="/orders",
            engine="pyspark",
        )


def test_api_definition_accepts_database_inputs():
    definition = ApiDefinition(
        path="/orders",
        inputs={
            "orders": DatabaseTable("operations.orders"),
            "database": Database(
                "operations",
                tables=[
                    "orders",
                ],
            ),
        },
    )

    assert isinstance(
        definition.inputs["orders"],
        DatabaseTable,
    )

    assert isinstance(
        definition.inputs["database"],
        Database,
    )


def test_api_definition_rejects_invalid_input():
    with pytest.raises(
        ValidationError,
        match="Invalid API input",
    ):
        ApiDefinition(
            path="/orders",
            inputs={
                "orders": object(),
            },
        )


def test_validation_definition():
    definition = ValidationDefinition(
        engine="duckdb",
    )

    assert definition.engine == "duckdb"


def test_validation_definition_defaults():
    definition = ValidationDefinition()

    assert definition.engine is None


def test_test_definition():
    def mocks():
        return {}

    definition = VortexifyTestDefinition(mocks=mocks)
    assert definition.mocks is mocks
