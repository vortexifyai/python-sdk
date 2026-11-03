from typing import Literal


class DatabaseTable:
    """
    Reference to a table in a Vortexify-managed database.

    DatabaseTable is read-only and resolves according to the resource engine:
    pandas -> pandas.DataFrame
    pyspark -> pyspark.sql.DataFrame
    duckdb -> registered relation in the injected DuckDB connection.
    """

    def __init__(
        self,
        reference: str,
    ):
        """
        Args:
            reference: Qualified table reference, such as "operations.orders".
                Stored unchanged; the platform interprets and validates it.
        """
        self.reference = reference


class Database:
    """
    Reference to a Vortexify-managed database for operational access.

    At runtime, Database resolves to a permission-scoped Postgres connection
    that can access the declared tables.
    """

    def __init__(
        self,
        name: str,
        *,
        tables: list[str],
        mode: Literal[
            "read",
            "read_write",
        ] = "read_write",
    ):
        """
        Args:
            name: Name of the Vortexify database.
            tables: Tables this function expects to access.
            mode: Whether the connection is read-only or can also insert,
                update, and delete rows.
        """
        if mode not in (
            "read",
            "read_write",
        ):
            raise ValueError(
                "Database mode must be 'read' or 'read_write'."
            )

        self.name = name
        self.tables = tables
        self.mode = mode
