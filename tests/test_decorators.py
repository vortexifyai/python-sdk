from vortexify import (
    Input,
    Table,
    vxfy_api,
    vxfy_test,
    vxfy_mocks,
    vxfy_transform,
    vxfy_validate,
)


def test_transform_decorator_attaches_definition():
    @vxfy_transform(
        engine="pandas",
        inputs={
            "orders": Table("shopify.orders"),
            "horizon": Input(int, default=30),
        },
    )
    def transform(
        orders,
        horizon,
    ):
        return orders

    assert transform.__vxfy_type__ == "transform"
    assert transform.__vxfy_definition__.engine == "pandas"
    assert "orders" in transform.__vxfy_definition__.inputs
    assert "horizon" in transform.__vxfy_definition__.inputs


def test_transform_decorator_wraps_single_schedule():
    from vortexify import CronSchedule

    schedule = CronSchedule(
        expression="0 8 * * *",
    )

    @vxfy_transform(
        schedule=schedule,
    )
    def transform():
        pass

    assert transform.__vxfy_definition__.schedule == [
        schedule
    ]


def test_api_decorator_attaches_definition():
    @vxfy_api(
        "/orders",
        inputs={
            "order_id": Input(str),
        },
    )
    def api(order_id):
        return {
            "order_id": order_id,
        }

    assert api.__vxfy_type__ == "api"
    assert api.__vxfy_definition__.path == "/orders"
    assert api.__vxfy_definition__.engine == "pandas"
    assert "order_id" in api.__vxfy_definition__.inputs


def test_validation_decorator_attaches_definition():
    @vxfy_validate(
        engine="duckdb",
    )
    def validate(conn):
        pass

    assert validate.__vxfy_type__ == "validation"
    assert validate.__vxfy_definition__.engine == "duckdb"


def test_validation_engine_defaults_to_none():
    @vxfy_validate()
    def validate(output):
        pass

    assert validate.__vxfy_definition__.engine is None


def test_test_decorator_attaches_mock_reference():
    @vxfy_mocks
    def shortage():
        return {}

    @vxfy_test(mocks=shortage)
    def test_case(run):
        pass

    assert test_case.__vxfy_type__ == "test"
    assert test_case.__vxfy_definition__.mocks is shortage
    assert shortage.__vxfy_type__ == "mocks"
    assert test_case.__test__ is False
