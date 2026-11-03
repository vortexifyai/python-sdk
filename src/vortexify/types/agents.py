from typing import Literal

from pydantic import BaseModel, Field

from .inputs import (
    Table,
    TransformOutput,
)

from .runners import ApiRunner


class AgentCapabilities(BaseModel):
    """
    Optional capabilities available to a Vortexify Agent.
    """

    model_config = {"extra": "forbid"}

    sql_analysis: bool = False
    """
    Allow context-scoped inspection and SQL analysis through platform jobs.
    """

    chart_generation: bool = False
    """
    Allow chart configuration referencing completed analysis jobs.
    Applications retrieve the stored rows and render the charts.
    """


class Agent(BaseModel):
    """
    Defines a Vortexify Agent with context, tools, and capabilities.
    """

    name: str
    """
    Name of the Agent.
    """

    provider: Literal["openai", "anthropic"] | None = None
    """
    Model provider. When omitted, the platform selects its default provider.
    """

    model: str | None = None
    """
    Provider model ID or snapshot ID. When omitted, the platform selects
    the default model for the selected provider.
    """

    prompt: str = ""
    """
    Primary instructions that define the Agent's role and behavior.
    """

    context: list[
        Table
        | TransformOutput
    ] = Field(
        default_factory=list
    )
    """
    Tabular data the Agent can use as context.
    """

    tools: list[
        ApiRunner
    ] = Field(
        default_factory=list
    )
    """
    APIs the Agent is allowed to invoke as tools.
    """

    capabilities: AgentCapabilities = Field(
        default_factory=AgentCapabilities
    )
    """
    Optional built-in capabilities available to the Agent.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }
