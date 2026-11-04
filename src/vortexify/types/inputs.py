from typing import Generic, TypeVar


T = TypeVar(
    "T",
    str,
    int,
    float,
    bool,
)


class Table:
    """
    Reference to a synced table or a published uploaded table.

    At runtime, the table is resolved according to the resource engine:
    pandas -> pandas.DataFrame
    pyspark -> pyspark.sql.DataFrame
    duckdb -> registered relation in the injected DuckDB connection.
    """

    def __init__(
        self,
        alias: str,
    ):
        """
        Args:
            alias: Qualified connector.sync reference, such as "shopify.orders",
                or "_upload.customers" for an uploaded table.
                Stored unchanged; the platform interprets and validates it.
        """
        self.alias = alias


class TransformOutput:
    """
    Reference to the tabular output of another Transform.

    Vortexify resolves the appropriate upstream output for the current run.
    The runtime representation depends on the resource engine.
    """

    def __init__(
        self,
        transform: str,
    ):
        """
        Args:
            transform: Transform name for a single output, or transform.output
                for a named output, such as "forecast.weekly". Stored unchanged;
                the platform interprets and validates the reference.
        """
        self.transform = transform


class Secret:
    """
    Reference to a Vortexify-managed secret.

    At runtime, the secret is resolved to its stored value.
    """

    def __init__(
        self,
        alias: str,
    ):
        """
        Args:
            alias: Name of the registered secret.
        """
        self.alias = alias


class Input(Generic[T]):
    """
    Runtime-supplied scalar input.

    Supported scalar types are str, int, float, and bool. The resolved
    value is passed directly to the function.
    """

    def __init__(
        self,
        type_: type[T],
        required: bool = True,
        default: T | None = None,
    ):
        """
        Args:
            type_: Expected scalar type.
            required: Whether a value must be supplied at runtime.
            default: Default value used when no runtime value is supplied.
        """
        if type_ not in (
            str,
            int,
            float,
            bool,
        ):
            raise ValueError(
                "Input type must be str, int, float, or bool."
            )

        if (
            default is not None
            and type(default) is not type_
        ):
            raise ValueError(
                f"Input default must be of type {type_.__name__}."
            )

        self.type = type_
        self.required = required
        self.default = default
