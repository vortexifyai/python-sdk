import pytest

from vortexify import Column, Connector, DiscoveredTable


class CompleteConnector(Connector):
    def client(self):
        return "client"

    def check(self) -> bool:
        return True

    def discover(self) -> list[DiscoveredTable]:
        return [
            DiscoveredTable(
                name="orders",
                schema=[Column(name="id", type="string", nullable=False)],
            )
        ]


class IncompleteConnector(Connector):
    def client(self):
        return "client"


def test_connector_initialization():
    connector = CompleteConnector(
        config={
            "host": "localhost",
        }
    )

    assert connector.config == {
        "host": "localhost",
    }


def test_vendor_domain_metadata_and_context_annotations():
    class StripeConnector(CompleteConnector):
        vendor_domain = "stripe.com"

    assert CompleteConnector(config={}).vendor_domain is None
    assert StripeConnector(config={}).vendor_domain == "stripe.com"
    assert Connector.__exit__.__annotations__["exc_type"] == type[BaseException] | None


def test_connector_client():
    connector = CompleteConnector(
        config={},
    )

    assert connector.client() == "client"


def test_connector_check():
    connector = CompleteConnector(
        config={},
    )

    assert connector.check() is True


def test_connector_discover():
    connector = CompleteConnector(
        config={},
    )

    tables = connector.discover()
    assert tables == [DiscoveredTable(
        name="orders",
        schema=[Column(name="id", type="string", nullable=False)],
    )]
    assert tables[0].preview is None



def test_incomplete_connector_cannot_be_instantiated():
    with pytest.raises(TypeError):
        IncompleteConnector(
            config={},
        )

def test_default_close_is_optional_noop_and_context_entry_is_lazy():
    connector = CompleteConnector(config={})
    assert connector.close() is None
    with connector as entered:
        assert entered is connector
        assert connector._client is None
    assert connector._client is None
    assert connector.close() is None


class ManagedConnector(CompleteConnector):
    def client(self):
        if self._client is None:
            from unittest.mock import Mock
            self._client = Mock()
        return self._client

    def close(self):
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None


def test_context_manager_closes_initialized_client_and_allows_repeated_cleanup():
    connector = ManagedConnector(config={})
    with connector:
        client = connector.client()
        assert connector.client() is client
        client.close.assert_not_called()
    client.close.assert_called_once()
    assert connector._client is None
    connector.close()
    client.close.assert_called_once()


def test_context_manager_cleans_up_without_suppressing_body_errors():
    connector = ManagedConnector(config={})
    error = RuntimeError("source failed")
    with pytest.raises(RuntimeError) as caught:
        with connector:
            client = connector.client()
            raise error
    assert caught.value is error
    client.close.assert_called_once()
    assert connector._client is None


def test_context_manager_does_not_initialize_an_unused_client():
    connector = ManagedConnector(config={})
    with connector:
        pass
    assert connector._client is None


def test_cleanup_errors_are_propagated_and_client_reference_is_cleared():
    connector = ManagedConnector(config={})
    with pytest.raises(RuntimeError, match="close failed"):
        with connector:
            client = connector.client()
            client.close.side_effect = RuntimeError("close failed")
    assert connector._client is None


def test_preview_caller_owns_connector_cleanup_on_success_and_failure():
    import pandas as pd
    from vortexify import Sync

    class PreviewSync(Sync):
        def preview(self):
            if self.config.get("fail"):
                raise RuntimeError("preview failed")
            return pd.DataFrame({"id": [1]})

        def extract(self, *, avg_row_size_bytes=None):
            raise AssertionError("preview called extract")

    connector = ManagedConnector(config={})
    with connector:
        result = PreviewSync(connector=connector).preview()
        client = connector.client()
        client.close.assert_not_called()
        assert len(result) == 1
    client.close.assert_called_once()

    failed_connector = ManagedConnector(config={})
    with pytest.raises(RuntimeError, match="preview failed"):
        with failed_connector:
            failed_client = failed_connector.client()
            PreviewSync(connector=failed_connector, config={"fail": True}).preview()
    failed_client.close.assert_called_once()
