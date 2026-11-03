from typing import Any, Callable, Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from ..database import (
    Database,
    DatabaseTable,
)

from .compute import (
    ApiCompute,
    TransformCompute,
    TransformSparkCompute,
)

from .inputs import (
    Input,
    Secret,
    Table,
    TransformOutput,
)

from .schedules import Schedule


TransformEngine = Literal[
    "pandas",
    "duckdb",
    "pyspark",
]

ApiEngine = Literal[
    "pandas",
    "duckdb",
]


class TransformDefinition(BaseModel):
    """
    Configuration attached to a function decorated with `vxfy_transform`.
    """

    engine: TransformEngine = "pandas"
    """
    Execution engine used by the Transform.

    `pandas` resolves tabular inputs as pandas DataFrames.
    `pyspark` resolves tabular inputs as Spark DataFrames.
    `duckdb` registers tabular inputs in an injected DuckDB connection.
    """

    inputs: dict[str, Any] = Field(
        default_factory=dict
    )
    """
    Mapping of function argument names to Vortexify input declarations.
    """

    schedule: list[Schedule] = Field(
        default_factory=list
    )
    """
    Cron or trigger schedules that automatically run the Transform.
    """

    compute: (
        TransformCompute
        | TransformSparkCompute
        | None
    ) = None
    """
    Optional compute configuration for the Transform.
    """

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, inputs):
        allowed = (
            Table,
            TransformOutput,
            DatabaseTable,
            Database,
            Secret,
            Input,
        )

        for name, value in inputs.items():
            if not isinstance(value, allowed):
                raise ValueError(
                    f"Invalid transform input '{name}'. "
                    "Expected Table, TransformOutput, DatabaseTable, "
                    "Database, Secret, or Input."
                )

        return inputs


class ApiDefinition(BaseModel):
    """
    Configuration attached to a function decorated with `vxfy_api`.
    """

    path: str
    """
    Route path exposed by the API.
    """

    engine: ApiEngine = "pandas"
    """
    Execution engine used by the API.

    `pandas` resolves tabular inputs as pandas DataFrames.
    `duckdb` registers tabular inputs in an injected DuckDB connection.
    """

    inputs: dict[str, Any] = Field(
        default_factory=dict
    )
    """
    Mapping of function argument names to Vortexify input declarations.
    """

    compute: ApiCompute | None = None
    """
    Optional compute configuration for the API.
    """

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, inputs):
        allowed = (
            Table,
            TransformOutput,
            DatabaseTable,
            Database,
            Secret,
            Input,
        )

        for name, value in inputs.items():
            if not isinstance(value, allowed):
                raise ValueError(
                    f"Invalid API input '{name}'. "
                    "Expected Table, TransformOutput, DatabaseTable, "
                    "Database, Secret, or Input."
                )

        return inputs


class ValidationDefinition(BaseModel):
    """
    Configuration attached to a function decorated with `vxfy_validate`.
    """

    engine: TransformEngine | None = None
    """
    Optional engine used to validate tabular output.

    Leave unset when validating a non-tabular result such as an API response.
    """


class TestDefinition(BaseModel):
    """
    Configuration attached to a function decorated with `vxfy_test`.
    """

    mocks: Callable[[], dict[str, Any]]
    """
    Decorated factory that produces fresh mock inputs for each run.
    """

    model_config = {"arbitrary_types_allowed": True}
