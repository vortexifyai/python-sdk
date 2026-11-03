from vortexify import (
    CronSchedule,
    Table,
    TransformOutput,
    TriggerSchedule,
)


def test_cron_schedule():
    schedule = CronSchedule(
        expression="0 8 * * *",
    )

    assert schedule.type == "cron"
    assert schedule.expression == "0 8 * * *"


def test_trigger_schedule_defaults_to_any():
    schedule = TriggerSchedule(
        triggers=[
            Table("shopify.orders"),
        ],
    )

    assert schedule.type == "trigger"
    assert schedule.mode == "any"
    assert len(schedule.triggers) == 1


def test_trigger_schedule_all():
    schedule = TriggerSchedule(
        mode="all",
        triggers=[
            Table("shopify.orders"),
            TransformOutput("forecast"),
        ],
    )

    assert schedule.mode == "all"
    assert len(schedule.triggers) == 2


def test_trigger_schedule_accepts_table():
    table = Table("shopify.orders")

    schedule = TriggerSchedule(
        triggers=[
            table,
        ],
    )

    assert schedule.triggers[0] is table


def test_trigger_schedule_accepts_transform_output():
    output = TransformOutput("forecast")

    schedule = TriggerSchedule(
        triggers=[
            output,
        ],
    )

    assert schedule.triggers[0] is output
