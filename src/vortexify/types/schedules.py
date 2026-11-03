from typing import Literal

from pydantic import BaseModel, Field

from .inputs import (
    Table,
    TransformOutput,
)


class CronSchedule(BaseModel):
    """
    Runs a resource on a cron schedule.
    """

    type: Literal["cron"] = "cron"
    """
    Schedule type identifier.
    """

    expression: str
    """
    Standard cron expression defining when the resource should run.
    """


class TriggerSchedule(BaseModel):
    """
    Runs a resource when one or more upstream data dependencies update.
    """

    type: Literal["trigger"] = "trigger"
    """
    Schedule type identifier.
    """

    mode: Literal[
        "any",
        "all",
    ] = "any"
    """
    Controls how multiple triggers are evaluated.

    `any` runs when any trigger updates.
    `all` runs after all configured triggers have updated.
    """

    triggers: list[
        Table | TransformOutput
    ] = Field(
        default_factory=list
    )
    """
    Tables or Transform outputs whose updates can trigger the resource.
    """

    model_config = {
        "arbitrary_types_allowed": True,
    }


Schedule = CronSchedule | TriggerSchedule
