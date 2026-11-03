from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any

from .types.discovery import DiscoveredTable


class Connector(ABC):
    """
    Base class for Vortexify connectors.

    A Connector defines how Vortexify connects to an external system,
    verifies access, and discovers resources that can be synced.
    """

    # Optional vendor domain (e.g. "stripe.com") for display and branding.
    # It does not classify the connector or control its behavior.
    vendor_domain: str | None = None

    def __init__(
        self,
        config: dict,
    ):
        """
        Initialize the Connector with connection-level configuration.

        Args:
            config: Configuration required to connect to the source,
                such as credentials, host information, or account settings.
        """
        self.config = config
        self._client = None

    def close(self) -> None:
        """
        Release source resources. The default implementation does nothing.

        Override when the connector owns a client or connection that needs
        cleanup. Make repeated calls safe and never initialize a client just
        to close it. Cleanup must not commit data or advance sync checkpoints.
        The caller owns this lifecycle, including after discovery or preview.
        """

    def __enter__(self) -> "Connector":
        """Return the connector without eagerly creating its source client."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Always run cleanup and propagate errors from the with block."""
        self.close()
        return False

    @abstractmethod
    def client(self) -> Any:
        """
        Return the client or connection used to access the source.

        Implementations should create the client once, store it on
        ``self._client``, and reuse it on subsequent calls.

        Returns:
            The source-specific client or connection object.
        """
        raise NotImplementedError

    @abstractmethod
    def check(self) -> bool:
        """
        Verify that Vortexify can successfully connect to the source.

        Implementations should perform a lightweight request or operation
        that confirms the configuration and credentials are valid.

        Returns:
            True when the connection is valid.

        Raises:
            Exception: If the source cannot be reached or authentication fails.
        """
        raise NotImplementedError

    @abstractmethod
    def discover(self) -> list[DiscoveredTable]:
        """
        Discover resources available from the source.

        Return stable names and column schemas. Preview rows are optional,
        limited to 100 per table, and must be fetched deliberately using
        source-specific sampling or an author-defined Sync.preview() with a fresh
        connector, never the state of an active sync. Metadata-only discovery
        need not read source rows.
        The SDK never fetches previews automatically.

        Returns:
            A list of DiscoveredTable objects.
        """
        raise NotImplementedError
