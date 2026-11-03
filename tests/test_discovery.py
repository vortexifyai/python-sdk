import pytest
from pydantic import ValidationError

from vortexify import Column, DiscoveredTable


def test_discovered_table_schema_preview_and_serialization():
    table = DiscoveredTable(
        name="orders",
        schema=[
            Column(name="id", type="string", nullable=False),
            Column(name="amount", type="decimal"),
        ],
        preview=[{"id": "order-123", "amount": "49.99"}],
    )

    assert table.schema[0].name == "id"
    assert table.schema[0].nullable is False
    assert table.schema[1].nullable is True
    wire = table.model_dump(by_alias=True)
    assert "schema" in wire
    assert "schema_" not in wire
    assert wire["preview"] == [{"id": "order-123", "amount": "49.99"}]
    assert DiscoveredTable.model_validate_json(table.model_dump_json(by_alias=True)) == table
    assert "schema" in DiscoveredTable.model_json_schema()["properties"]


def test_metadata_only_discovery_needs_no_preview():
    table = DiscoveredTable(name="orders", schema=[])
    assert table.preview is None
    assert table.schema == []
    assert "preview" not in table.model_dump(by_alias=True, exclude_none=True)


def test_preview_limit_and_empty_preview():
    assert DiscoveredTable(name="orders", schema=[], preview=[]).preview == []
    table = DiscoveredTable(name="orders", schema=[], preview=[{"id": i} for i in range(100)])
    assert len(table.preview) == 100
    with pytest.raises(ValidationError, match="preview"):
        DiscoveredTable(name="orders", schema=[], preview=[{}] * 101)


def test_preview_must_be_json_compatible():
    with pytest.raises(ValidationError, match="preview"):
        DiscoveredTable(name="orders", schema=[], preview=[{"value": object()}])


def test_discovery_rejects_duplicate_columns_and_empty_names():
    with pytest.raises(ValidationError, match="unique column names"):
        DiscoveredTable(name="orders", schema=[Column(name="id", type="string")] * 2)
    with pytest.raises(ValidationError):
        DiscoveredTable(name="", schema=[])
    with pytest.raises(ValidationError):
        Column(name="id", type="")
