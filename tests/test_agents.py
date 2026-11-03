import pytest
from pydantic import ValidationError

from vortexify import (
    Agent,
    AgentCapabilities,
    ApiRunner,
    Table,
    TransformOutput,
)


def test_agent_defaults():
    agent = Agent(
        name="planner",
    )

    assert agent.name == "planner"
    assert agent.provider is None
    assert agent.model is None
    assert agent.prompt == ""
    assert agent.context == []
    assert agent.tools == []
    assert "tasks" not in agent.model_dump()
    assert agent.capabilities == AgentCapabilities()


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_agent_model_provider_round_trip(provider):
    agent = Agent(
        name="planner",
        provider=provider,
        model="provider-model-snapshot",
    )

    restored = Agent.model_validate_json(agent.model_dump_json())

    assert restored.provider == provider
    assert restored.model == "provider-model-snapshot"


def test_agent_rejects_unsupported_provider():
    with pytest.raises(ValidationError, match="provider"):
        Agent(name="planner", provider="unsupported")


def test_agent_provider_can_use_platform_default_model():
    agent = Agent(name="planner", provider="anthropic")

    assert agent.provider == "anthropic"
    assert agent.model is None


def test_agent_capabilities():
    capabilities = AgentCapabilities(
        sql_analysis=True,
        chart_generation=True,
    )

    assert capabilities.sql_analysis is True
    assert capabilities.chart_generation is True


def test_agent_context():
    context = [
        Table("shopify.orders"),
        TransformOutput("forecast"),
    ]

    agent = Agent(
        name="planner",
        context=context,
    )

    assert agent.context == context


def test_agent_tools():
    runner = ApiRunner(
        "save_schedule",
    )

    agent = Agent(
        name="planner",
        tools=[
            runner,
        ],
    )

    assert agent.tools == [
        runner,
    ]


@pytest.mark.parametrize("tasks", [[], [{"name": "review", "prompt": "Review risks."}]])
def test_agent_rejects_tasks(tasks):
    with pytest.raises(ValidationError, match="tasks"):
        Agent(name="planner", tasks=tasks)


def test_agent_rejects_tasks_in_serialized_definition():
    with pytest.raises(ValidationError, match="tasks"):
        Agent.model_validate_json('{"name":"planner","tasks":[]}')


def test_task_is_not_exported():
    import vortexify

    assert not hasattr(vortexify, "Task")
    assert "Task" not in vortexify.__all__


def test_agent_rejects_file_context():
    with pytest.raises(ValidationError):
        Agent(name="planner", context=[{"type": "file", "alias": "manual"}])


def test_agent_capabilities_reject_arbitrary_code_execution():
    with pytest.raises(ValidationError, match="code_execution"):
        AgentCapabilities(code_execution=True)
