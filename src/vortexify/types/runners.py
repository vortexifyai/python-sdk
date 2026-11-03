class ApiRunner:
    """
    Reference to a Vortexify API that can be invoked from a supported runtime.

    ApiRunner is typically used to expose an API as a tool to an Agent.
    """

    def __init__(
        self,
        api: str,
        *,
        api_id: str | None = None,
        client=None,
    ):
        """
        Args:
            api: Name of the API resource.
        """
        self.api = api
        self._api_id = api_id
        self._client = client

    def run(
        self,
        inputs: dict | None = None,
    ):
        """
        Invoke the API with runtime inputs.

        Args:
            inputs: Values supplied to the API's declared Input fields.

        Returns:
            The response returned by the API.
        """
        self._require_bound()

        return self._client.run_api(
            api_id=self._api_id,
            inputs=inputs or {},
        )

    def _require_bound(self):
        if self._client is None or self._api_id is None:
            raise RuntimeError(
                f"API '{self.api}' is not bound to a runtime resource."
            )
