import pytest
from pydantic import ValidationError

from vortexify import (
    ApiCompute,
    TransformCompute,
    TransformSparkCompute,
    vxfy_api,
    vxfy_transform,
)


def test_transform_compute():
    compute = TransformCompute(
        memory=4096,
        cores=2,
        disk=8192,
    )

    assert compute.memory == 4096
    assert compute.cores == 2
    assert compute.disk == 8192


def test_transform_compute_defaults():
    compute = TransformCompute()

    assert compute.memory is None
    assert compute.cores is None
    assert compute.disk is None


def test_transform_spark_compute():
    compute = TransformSparkCompute(
        driver_memory=4096,
        driver_cores=2,
        driver_disk=8192,
        executor_memory=8192,
        executor_cores=4,
        executor_disk=16384,
        executor_instances=3,
    )

    assert compute.driver_memory == 4096
    assert compute.driver_cores == 2
    assert compute.driver_disk == 8192

    assert compute.executor_memory == 8192
    assert compute.executor_cores == 4
    assert compute.executor_disk == 16384
    assert compute.executor_instances == 3


def test_api_compute():
    compute = ApiCompute(
        memory=2048,
        storage=4096,
    )

    assert compute.memory == 2048
    assert compute.storage == 4096


def test_api_compute_defaults():
    compute = ApiCompute()

    assert compute.memory is None
    assert compute.storage is None


@pytest.mark.parametrize("compute_type", [TransformCompute, TransformSparkCompute, ApiCompute])
@pytest.mark.parametrize("size", ["xsmall", "small", "medium", "large", "xlarge"])
def test_compute_sizes_round_trip(compute_type, size):
    compute = compute_type(size=size)

    assert compute.model_dump(exclude_none=True) == {"size": size, **compute_type.PRESETS[size]}
    assert compute_type.model_validate_json(compute.model_dump_json()).size == size


@pytest.mark.parametrize("compute_type", [TransformCompute, TransformSparkCompute, ApiCompute])
def test_compute_size_is_optional(compute_type):
    assert compute_type().size is None


@pytest.mark.parametrize("compute_type", [TransformCompute, TransformSparkCompute, ApiCompute])
def test_compute_rejects_unknown_size(compute_type):
    with pytest.raises(ValidationError, match="size"):
        compute_type(size="huge")


@pytest.mark.parametrize("compute_type,overrides", [
    (TransformCompute, {"memory": 8192}),
    (TransformSparkCompute, {"executor_instances": 4}),
    (ApiCompute, {"storage": 2048}),
])
def test_compute_size_preserves_explicit_overrides(compute_type, overrides):
    compute = compute_type(size="medium", **overrides)

    assert compute.model_dump(exclude_none=True) == {"size": "medium", **compute_type.PRESETS["medium"], **overrides}


@pytest.mark.parametrize("compute,decorator", [
    (TransformCompute(size="small"), vxfy_transform(engine="pandas", compute=TransformCompute(size="small"))),
    (TransformSparkCompute(size="large"), vxfy_transform(engine="pyspark", compute=TransformSparkCompute(size="large"))),
    (ApiCompute(size="xsmall"), vxfy_api("/example", compute=ApiCompute(size="xsmall"))),
])
def test_decorators_preserve_compute_presets(compute, decorator):
    @decorator
    def resource():
        pass

    assert resource.__vxfy_definition__.compute == compute


@pytest.mark.parametrize("compute_type,fields,expected", [
    (TransformCompute, ["memory", "cores", "disk"], [
        (1024, 1, 2048), (2048, 1, 4096), (4096, 2, 8192),
        (8192, 4, 16384), (16384, 8, 32768),
    ]),
    (ApiCompute, ["memory", "storage"], [
        (256, 512), (512, 512), (1024, 1024), (2048, 2048), (4096, 4096),
    ]),
    (TransformSparkCompute, [
        "driver_memory", "driver_cores", "driver_disk", "executor_memory",
        "executor_cores", "executor_disk", "executor_instances",
    ], [
        (1024, 1, 4096, 2048, 1, 4096, 1),
        (2048, 1, 8192, 4096, 2, 8192, 2),
        (4096, 2, 16384, 8192, 2, 16384, 2),
        (8192, 4, 32768, 16384, 4, 32768, 4),
        (16384, 4, 65536, 32768, 8, 65536, 8),
    ]),
])
def test_documented_preset_allocations(compute_type, fields, expected):
    for size, values in zip(["xsmall", "small", "medium", "large", "xlarge"], expected):
        compute = compute_type(size=size)
        assert tuple(getattr(compute, field) for field in fields) == values


def test_preset_resolution_does_not_mutate_input_or_shared_defaults():
    data = {"size": "medium", "memory": None, "cores": 4}
    compute = TransformCompute.model_validate(data)

    assert data == {"size": "medium", "memory": None, "cores": 4}
    assert compute.memory == 4096
    assert compute.cores == 4
    assert TransformCompute(size="medium").cores == 2
    with pytest.raises(TypeError):
        TransformCompute.PRESETS["medium"]["memory"] = 123


def test_spark_definition_serialization_preserves_resolved_compute():
    from vortexify.types.definitions import TransformDefinition

    definition = TransformDefinition(
        engine="pyspark",
        compute=TransformSparkCompute(size="small", executor_instances=3),
    )
    restored = TransformDefinition.model_validate_json(definition.model_dump_json())

    assert isinstance(restored.compute, TransformSparkCompute)
    assert restored.compute.executor_instances == 3
    assert restored.compute.executor_memory == 4096
