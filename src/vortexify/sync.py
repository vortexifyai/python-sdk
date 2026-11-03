from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .connector import Connector
from .types.compute import TransformCompute
from .types.schedules import CronSchedule


@dataclass(frozen=True)
class SyncPreview:
    """Sample rows and their estimated UTF-8 NDJSON size, including newlines."""

    data: pd.DataFrame
    avg_row_size_bytes: float | None

    @classmethod
    def from_dataframe(cls, data: pd.DataFrame, *, limit: int = 100) -> "SyncPreview":
        """
        Copy up to limit sample rows and calculate their average JSON size.

        This helper makes no source requests and never accesses a Sync's state.
        Empty samples have no estimate. The backend can store the estimate and
        supply it as extract(avg_row_size_bytes=...) on a later real run.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Preview data must be a pandas DataFrame.")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Preview limit must be an integer between 1 and 100.")
        sample = data.head(limit).copy().reset_index(drop=True)
        if sample.empty:
            return cls(data=sample, avg_row_size_bytes=None)
        encoded = sample.to_json(
            orient="records", lines=True, date_format="iso", force_ascii=False,
        ).encode("utf-8")
        return cls(data=sample, avg_row_size_bytes=len(encoded) / len(sample))


class Sync(ABC):
    """
    Defines a sync that extracts tabular data from a Connector.
    """

    mode: Literal["full", "incremental"] = "full"

    schedule: CronSchedule | None = None
    """
    Optional cron schedule used by the platform to launch this Sync.
    Trigger schedules are not supported for Syncs.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.schedule is not None and not isinstance(cls.schedule, CronSchedule):
            raise TypeError("Sync.schedule must be a CronSchedule or None.")

    compute: TransformCompute | None = None
    """
    Declared runtime resources, accessible inside extract() as self.compute.
    Presets resolve to memory/disk in MiB and CPU cores. This configuration
    describes requested allocations, not measured free resources. Compute or
    individual fields may be None and require an implementation fallback.
    """

    def __init__(
        self,
        connector: Connector,
        config: dict | None = None,
        state: dict | None = None,
    ):
        self.connector = connector
        self.client = connector.client()
        self.config = config if config is not None else {}
        self.state = state if state is not None else {}

    @abstractmethod
    def extract(
        self,
        *,
        avg_row_size_bytes: float | None = None,
    ) -> Iterator[pd.DataFrame]:
        """
        Yield DataFrames containing rows extracted from the source.

        Args:
            avg_row_size_bytes: Optional preview-derived average UTF-8 JSON
                bytes per row, supplied by the backend before extraction.
                None means no saved estimate is available. This is metadata,
                not checkpoint state; the SDK does not calculate it here.

        Authors can read self.compute.memory, self.compute.cores and
        self.compute.disk for declared resources, handling None as needed.
        self.state remains the real run's checkpoint dictionary.
        """
        ...

    def preview(self) -> pd.DataFrame:
        """
        Return representative sample rows using a source-specific read.

        Optional author-defined implementation; never falls back to extract().
        The backend must call this on a separate Sync with empty temporary
        state, copied configuration, and a fresh connector/client, and must
        never persist preview checkpoints. Return a small DataFrame; use
        SyncPreview.from_dataframe() to calculate the estimate separately.
        """
        raise NotImplementedError("This Sync does not implement preview().")
