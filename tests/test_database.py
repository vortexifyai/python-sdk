import pytest

from vortexify import (
    Database,
    DatabaseTable,
)


def test_database_table():
    table = DatabaseTable("operations.orders")

    assert table.reference == "operations.orders"


def test_database_defaults_to_read_write():
    database = Database(
        "operations",
        tables=[
            "orders",
            "customers",
        ],
    )

    assert database.name == "operations"
    assert database.tables == [
        "orders",
        "customers",
    ]
    assert database.mode == "read_write"


def test_database_read_mode():
    database = Database(
        "operations",
        tables=[
            "orders",
        ],
        mode="read",
    )

    assert database.mode == "read"


def test_database_rejects_invalid_mode():
    with pytest.raises(
        ValueError,
        match="Database mode must be",
    ):
        Database(
            "operations",
            tables=[
                "orders",
            ],
            mode="invalid",
        )


def test_database_requires_tables():
    database = Database(
        "operations",
        tables=[],
    )

    assert database.tables == []
