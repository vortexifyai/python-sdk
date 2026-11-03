import pytest

from vortexify import (
    Input,
    Secret,
    Table,
    TransformOutput,
)


def test_table():
    table = Table("shopify.orders")

    assert table.alias == "shopify.orders"


@pytest.mark.parametrize("reference", ["forecast", "forecast.weekly"])
def test_transform_output(reference):
    output = TransformOutput(reference)

    assert output.transform == reference


def test_secret():
    secret = Secret("api_key")

    assert secret.alias == "api_key"


@pytest.mark.parametrize(
    "type_,default",
    [
        (str, "hello"),
        (int, 30),
        (float, 1.5),
        (bool, True),
    ],
)
def test_input_supported_types(
    type_,
    default,
):
    input_ = Input(
        type_,
        default=default,
    )

    assert input_.type is type_
    assert input_.default == default


def test_input_without_default():
    input_ = Input(int)

    assert input_.type is int
    assert input_.required is True
    assert input_.default is None


def test_invalid_input_type():
    with pytest.raises(
        ValueError,
        match="Input type must be",
    ):
        Input(list)


def test_invalid_input_default_type():
    with pytest.raises(
        ValueError,
        match="Input default must be",
    ):
        Input(
            int,
            default="30",
        )


def test_file_declaration_is_removed():
    import vortexify
    from vortexify.types import inputs

    assert not hasattr(vortexify, "File")
    assert "File" not in vortexify.__all__
    assert not hasattr(inputs, "File")
