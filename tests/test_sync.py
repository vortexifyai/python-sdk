import pandas as pd
import pytest

from vortexify import (
    Connector,
    CronSchedule,
    DiscoveredTable,
    Sync,
    SyncPreview,
    TransformCompute,
    TriggerSchedule,
)


class MockConnector(Connector):
    def client(self):
        return "client"

    def check(self) -> bool:
        return True

    def discover(self) -> list[DiscoveredTable]:
        return []


class MockSync(Sync):
    compute = TransformCompute(
        memory=4096,
        cores=2,
        disk=8192,
    )

    def extract(self, *, avg_row_size_bytes: float | None = None):
        yield pd.DataFrame(
            {
                "id": range(150),
            }
        )


class EmptySync(Sync):
    def extract(self, *, avg_row_size_bytes: float | None = None):
        yield pd.DataFrame()


def test_sync_initialization():
    connector = MockConnector(
        config={},
    )

    sync = MockSync(
        connector=connector,
        config={
            "table": "orders",
        },
        state={
            "cursor": 100,
        },
    )

    assert sync.connector is connector
    assert sync.client == "client"

    assert sync.config == {
        "table": "orders",
    }

    assert sync.state == {
        "cursor": 100,
    }


def test_sync_defaults():
    connector = MockConnector(
        config={},
    )

    sync = MockSync(
        connector=connector,
    )

    assert sync.config == {}
    assert sync.state == {}


def test_sync_default_mode_is_full():
    sync = MockSync(connector=MockConnector(config={}))

    assert Sync.mode == "full"
    assert sync.mode == "full"


def test_sync_subclass_can_override_mode_to_incremental():
    class IncrementalSync(MockSync):
        mode = "incremental"

    sync = IncrementalSync(connector=MockConnector(config={}))

    assert IncrementalSync.mode == "incremental"
    assert sync.mode == "incremental"
    assert Sync.mode == "full"


def test_sync_defaults_to_no_schedule():
    sync = MockSync(connector=MockConnector(config={}))

    assert Sync.schedule is None
    assert sync.schedule is None


def test_sync_subclass_can_declare_cron_schedule():
    class ScheduledSync(MockSync):
        schedule = CronSchedule(expression="*/15 * * * *")

    sync = ScheduledSync(connector=MockConnector(config={}))

    assert sync.schedule.expression == "*/15 * * * *"
    assert sync.schedule.type == "cron"
    assert Sync.schedule is None
    assert MockSync.schedule is None


def test_sync_schedule_can_be_inherited_or_disabled():
    class ScheduledSync(MockSync):
        schedule = CronSchedule(expression="0 * * * *")

    class InheritedSync(ScheduledSync):
        pass

    class UnscheduledSync(ScheduledSync):
        schedule = None

    assert InheritedSync.schedule == ScheduledSync.schedule
    assert UnscheduledSync.schedule is None


@pytest.mark.parametrize("schedule", [TriggerSchedule(), "*/15 * * * *", {}])
def test_sync_rejects_non_cron_schedule(schedule):
    with pytest.raises(TypeError, match="CronSchedule or None"):
        type("InvalidScheduledSync", (MockSync,), {"schedule": schedule})


def test_sync_compute():
    assert MockSync.compute == TransformCompute(
        memory=4096,
        cores=2,
        disk=8192,
    )


def test_sync_has_no_implicit_test_method():
    assert not hasattr(Sync, "test")


def test_sync_has_no_extraction_measurement_wrapper():
    assert not hasattr(Sync, "iter_batches")


def test_preview_is_optional_and_never_falls_back_to_extract():
    class NoPreviewSync(MockSync):
        def extract(self, *, avg_row_size_bytes=None):
            raise AssertionError("preview called extract")

    sync = NoPreviewSync(connector=MockConnector(config={}), state={"cursor": 5})
    with pytest.raises(NotImplementedError, match="does not implement preview"):
        sync.preview()
    assert sync.state == {"cursor": 5}


def test_preview_helper_limits_rows_copies_data_and_calculates_size():
    data = pd.DataFrame({"id": range(150)}, index=range(10, 160))
    result = SyncPreview.from_dataframe(data)
    assert result.data["id"].tolist() == list(range(100))
    assert result.data.index.tolist() == list(range(100))
    expected_size = len(result.data.to_json(orient="records", lines=True).encode("utf-8")) / 100
    assert result.avg_row_size_bytes == expected_size
    result.data.loc[0, "id"] = -1
    assert data.iloc[0]["id"] == 0
    assert len(SyncPreview.from_dataframe(data, limit=3).data) == 3


@pytest.mark.parametrize("limit", [0, -1, 101, True, 1.5, "10", None])
def test_preview_helper_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="between 1 and 100"):
        SyncPreview.from_dataframe(pd.DataFrame(), limit=limit)


def test_preview_helper_rejects_non_dataframe():
    with pytest.raises(TypeError, match="pandas DataFrame"):
        SyncPreview.from_dataframe([{"id": 1}])


def test_empty_preview_preserves_columns_and_has_no_row_estimate():
    result = SyncPreview.from_dataframe(pd.DataFrame(columns=["id", "text"]))
    assert result.data.empty
    assert list(result.data.columns) == ["id", "text"]
    assert result.avg_row_size_bytes is None


def test_preview_estimate_uses_utf8_and_iso_dates():
    data = pd.DataFrame({"text": ["é"], "at": [pd.Timestamp("2026-10-17")]})
    result = SyncPreview.from_dataframe(data)
    assert result.avg_row_size_bytes == len('{"text":"é","at":"2026-10-17T00:00:00.000"}\n'.encode("utf-8"))


def test_author_preview_and_runtime_estimate_are_separate_from_run_state():
    from copy import deepcopy

    events = []
    config = {"nested": {"flag": False}}
    saved_state = {"cursor": 100}

    class AuthorSync(MockSync):
        def preview(self):
            events.append(("preview", dict(self.state)))
            self.config["nested"]["flag"] = True
            self.state["temporary"] = True
            return pd.DataFrame({"id": [1, 2]})

        def extract(self, *, avg_row_size_bytes: float | None = None):
            events.append(("extract", avg_row_size_bytes, dict(self.state)))
            self.state["cursor"] += 1
            yield pd.DataFrame({"id": [self.state["cursor"]]})

    preview_sync = AuthorSync(
        connector=MockConnector(config={}), config=deepcopy(config), state={},
    )
    result = SyncPreview.from_dataframe(preview_sync.preview())
    assert events == [("preview", {})]
    assert saved_state == {"cursor": 100}
    assert config == {"nested": {"flag": False}}

    run_sync = AuthorSync(connector=MockConnector(config={}), config=config, state=saved_state)
    batches = list(run_sync.extract(avg_row_size_bytes=result.avg_row_size_bytes))
    assert events[-1] == ("extract", result.avg_row_size_bytes, {"cursor": 100})
    assert batches[0]["id"].tolist() == [101]
    assert saved_state == {"cursor": 101}


@pytest.mark.parametrize("size,memory", [("small", 2048), ("medium", 4096)])
def test_extract_can_use_resolved_compute_and_optional_estimate(size, memory):
    observed = []

    class ConfiguredSync(MockSync):
        compute = TransformCompute(size=size)

        def extract(self, *, avg_row_size_bytes: float | None = None):
            observed.append((self.compute.memory, self.compute.cores, self.compute.disk, avg_row_size_bytes))
            yield pd.DataFrame()

    sync = ConfiguredSync(connector=MockConnector(config={}))
    list(sync.extract())
    list(sync.extract(avg_row_size_bytes=42.5))
    assert observed[0] == (memory, sync.compute.cores, sync.compute.disk, None)
    assert observed[1][-1] == 42.5


def test_extract_can_handle_no_declared_compute():
    class UnconfiguredSync(MockSync):
        compute = None

        def extract(self, *, avg_row_size_bytes=None):
            assert self.compute is None
            assert avg_row_size_bytes is None
            yield pd.DataFrame()

    list(UnconfiguredSync(connector=MockConnector(config={})).extract())
