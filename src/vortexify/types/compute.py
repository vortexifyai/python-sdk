from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar, Literal

from pydantic import BaseModel, model_validator


ComputeSize = Literal["xsmall", "small", "medium", "large", "xlarge"]


class _ComputeConfig(BaseModel):
    size: ComputeSize | None = None
    """Optional SDK preset; explicit resource values override its defaults."""

    PRESETS: ClassVar[Mapping[ComputeSize, Mapping[str, int]]]

    @model_validator(mode="before")
    @classmethod
    def resolve_preset(cls, data):
        if not isinstance(data, dict):
            return data
        size = data.get("size")
        if not isinstance(size, str) or size not in cls.PRESETS:
            return data
        resolved = dict(data)
        for field, value in cls.PRESETS[size].items():
            if resolved.get(field) is None:
                resolved[field] = value
        return resolved


def _presets(values: dict[ComputeSize, dict[str, int]]):
    # Expose defaults for inspection without allowing shared presets to mutate.
    return MappingProxyType({size: MappingProxyType(fields) for size, fields in values.items()})


class TransformCompute(_ComputeConfig):
    """
    Compute configuration for a non-Spark Transform or Sync.
    """

    PRESETS = _presets({
        "xsmall": {"memory": 1024, "cores": 1, "disk": 2048},
        "small": {"memory": 2048, "cores": 1, "disk": 4096},
        "medium": {"memory": 4096, "cores": 2, "disk": 8192},
        "large": {"memory": 8192, "cores": 4, "disk": 16384},
        "xlarge": {"memory": 16384, "cores": 8, "disk": 32768},
    })

    memory: int | None = None
    """
    Memory allocated to the runtime, in MiB.
    """

    cores: int | None = None
    """
    Number of CPU cores allocated to the runtime.
    """

    disk: int | None = None
    """
    Ephemeral disk storage allocated to the runtime, in MiB.
    """


class TransformSparkCompute(_ComputeConfig):
    """
    Compute configuration for a PySpark Transform.
    """

    PRESETS = _presets({
        "xsmall": {
            "driver_memory": 1024, "driver_cores": 1, "driver_disk": 4096,
            "executor_memory": 2048, "executor_cores": 1, "executor_disk": 4096,
            "executor_instances": 1,
        },
        "small": {
            "driver_memory": 2048, "driver_cores": 1, "driver_disk": 8192,
            "executor_memory": 4096, "executor_cores": 2, "executor_disk": 8192,
            "executor_instances": 2,
        },
        "medium": {
            "driver_memory": 4096, "driver_cores": 2, "driver_disk": 16384,
            "executor_memory": 8192, "executor_cores": 2, "executor_disk": 16384,
            "executor_instances": 2,
        },
        "large": {
            "driver_memory": 8192, "driver_cores": 4, "driver_disk": 32768,
            "executor_memory": 16384, "executor_cores": 4, "executor_disk": 32768,
            "executor_instances": 4,
        },
        "xlarge": {
            "driver_memory": 16384, "driver_cores": 4, "driver_disk": 65536,
            "executor_memory": 32768, "executor_cores": 8, "executor_disk": 65536,
            "executor_instances": 8,
        },
    })

    driver_memory: int | None = None
    """
    Memory allocated to the Spark driver, in MiB.
    """

    driver_cores: int | None = None
    """
    Number of CPU cores allocated to the Spark driver.
    """

    driver_disk: int | None = None
    """
    Ephemeral disk storage allocated to the Spark driver, in MiB.
    """

    executor_memory: int | None = None
    """
    Memory allocated to each Spark executor, in MiB.
    """

    executor_cores: int | None = None
    """
    Number of CPU cores allocated to each Spark executor.
    """

    executor_disk: int | None = None
    """
    Ephemeral disk storage allocated to each Spark executor, in MiB.
    """

    executor_instances: int | None = None
    """
    Number of Spark executor instances to run.
    """


class ApiCompute(_ComputeConfig):
    """
    Compute configuration for a Vortexify API.
    """

    PRESETS = _presets({
        "xsmall": {"memory": 256, "storage": 512},
        "small": {"memory": 512, "storage": 512},
        "medium": {"memory": 1024, "storage": 1024},
        "large": {"memory": 2048, "storage": 2048},
        "xlarge": {"memory": 4096, "storage": 4096},
    })

    memory: int | None = None
    """
    Memory allocated to each API invocation, in MiB.
    """

    storage: int | None = None
    """
    Ephemeral storage allocated to each API invocation, in MiB.
    """
