from .types.definitions import (
    ApiDefinition,
    TransformDefinition,
    ValidationDefinition,
)
from .testing import vxfy_mocks, vxfy_test


def vxfy_transform(
    *,
    engine="pandas",
    inputs=None,
    schedule=None,
    compute=None,
):
    """
    Define a Vortexify transform.

    Transforms run background or scheduled compute and produce tabular output.

    Args:
        engine: Execution engine used by the transform. Supported values are
            "pandas", "duckdb", and "pyspark".
        inputs: Mapping of function argument names to Vortexify input
            declarations such as Table, TransformOutput, Secret, or Input.
        schedule: Optional CronSchedule, TriggerSchedule, or list of schedules.
        compute: Optional compute configuration for the transform.
    """
    inputs = inputs or {}

    if schedule is None:
        schedules = []
    elif isinstance(schedule, list):
        schedules = schedule
    else:
        schedules = [schedule]

    def decorator(func):
        func.__vxfy_type__ = "transform"

        func.__vxfy_definition__ = TransformDefinition(
            engine=engine,
            inputs=inputs,
            schedule=schedules,
            compute=compute,
        )

        return func

    return decorator


def vxfy_api(
    path: str,
    *,
    engine="pandas",
    inputs=None,
    compute=None,
):
    """
    Define a Vortexify API.

    APIs run synchronous request-response logic and are exposed as POST
    endpoints by Vortexify.

    Args:
        path: API route path.
        engine: Execution engine used by the API. Supported values are
            "pandas" and "duckdb".
        inputs: Mapping of function argument names to Vortexify input
            declarations such as Table, TransformOutput, Secret, or Input.
        compute: Optional compute configuration for the API.
    """
    inputs = inputs or {}

    def decorator(func):
        func.__vxfy_type__ = "api"

        func.__vxfy_definition__ = ApiDefinition(
            path=path,
            engine=engine,
            inputs=inputs,
            compute=compute,
        )

        return func

    return decorator


def vxfy_validate(
    *,
    engine=None,
):
    """
    Define validation logic for the resource in the current directory.

    A directory can contain at most one validation function. The platform runs
    it on production transform output and records the ValidationResult without
    blocking publication on findings or validator exceptions. Deployed APIs skip
    automatic validation. Direct calls and SDK mock tests do not invoke it
    automatically; tests may call it explicitly.

    Args:
        engine: Optional execution engine for tabular validation. Supported
            values are "pandas", "duckdb", and "pyspark". Leave unset for
            validation that operates directly on a non-tabular result, such
            as an API response.
    """
    def decorator(func):
        func.__vxfy_type__ = "validation"

        func.__vxfy_definition__ = ValidationDefinition(
            engine=engine,
        )

        return func

    return decorator
