import pytest

from vortexify import ApiRunner


class MockClient:
    def __init__(self):
        self.calls = []

    def run_api(
        self,
        api_id,
        inputs,
    ):
        self.calls.append(
            {
                "api_id": api_id,
                "inputs": inputs,
            }
        )

        return {
            "status": "success",
        }


def test_api_runner_initialization():
    runner = ApiRunner(
        "save_schedule",
    )

    assert runner.api == "save_schedule"


def test_api_runner_requires_runtime_binding():
    runner = ApiRunner(
        "save_schedule",
    )

    with pytest.raises(
        RuntimeError,
        match="is not bound to a runtime resource",
    ):
        runner.run()


def test_api_runner_run():
    client = MockClient()

    runner = ApiRunner(
        "save_schedule",
        api_id="api-123",
        client=client,
    )

    result = runner.run(
        inputs={
            "schedule_id": "schedule-1",
        }
    )

    assert result == {
        "status": "success",
    }

    assert client.calls == [
        {
            "api_id": "api-123",
            "inputs": {
                "schedule_id": "schedule-1",
            },
        }
    ]


def test_api_runner_defaults_inputs_to_empty_dict():
    client = MockClient()

    runner = ApiRunner(
        "save_schedule",
        api_id="api-123",
        client=client,
    )

    runner.run()

    assert client.calls == [
        {
            "api_id": "api-123",
            "inputs": {},
        }
    ]
