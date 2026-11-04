# Vortexify Python SDK

Define data transforms, APIs, connectors, syncs, and agents for Vortexify. The SDK also provides resource inputs, compute settings, schedules, validation, and mock-based tests.

## Installation

Requires Python 3.10 or newer.

```sh
python -m pip install vortexify
```

## Work with a Vortexify project

Write SDK declarations in your project's resource files. Vortexify supplies resource inputs and runs the saved code; installing or importing the SDK does not deploy your project.

Use the Vortexify CLI to create resource starters, commit changes, and run them:

```sh
vortexify create transform order_totals
# Edit the generated transform, then save and run it:
vortexify commit --type transform --resource order_totals
vortexify run transform order_totals --wait
```

Run these commands from an initialized Vortexify project after signing in with `vortexify login`. Resource names and table references in the examples below should match resources in your project.

## Transforms

Transforms run as background compute jobs and produce tabular output.

Inputs are declared using Vortexify resources. At runtime, Vortexify resolves those declarations into normal Python values based on the selected execution engine.

### Pandas

```python
import pandas as pd

from vortexify import Table, vxfy_transform


@vxfy_transform(
    engine="pandas",
    inputs={"orders": Table("shopify.orders")},
)
def order_totals(orders: pd.DataFrame) -> pd.DataFrame:
    return orders.groupby("customer_id", as_index=False)["amount"].sum()
```

With the Pandas engine:

```text
Table            -> pandas.DataFrame
TransformOutput  -> pandas.DataFrame
DatabaseTable    -> pandas.DataFrame
```

### DuckDB

```python
import duckdb

from vortexify import (
    Table,
    vxfy_transform,
)


@vxfy_transform(
    engine="duckdb",
    inputs={
        "orders": Table("shopify.orders"),
    },
)
def summarize_orders(
    conn: duckdb.DuckDBPyConnection,
):
    return conn.execute(
        """
        SELECT
            customer_id,
            SUM(amount) AS revenue
        FROM orders
        GROUP BY customer_id
        """
    ).df()
```

With the DuckDB engine, declared tabular inputs are registered as relations in the injected DuckDB connection.

The function can use normal DuckDB APIs such as:

```python
conn.execute(...)
conn.sql(...)
```

The function decides how query results are returned, such as Pandas, Arrow, or another supported DuckDB representation.

### PySpark

```python
from pyspark.sql import DataFrame

from vortexify import (
    Table,
    vxfy_transform,
)


@vxfy_transform(
    engine="pyspark",
    inputs={
        "orders": Table("shopify.orders"),
    },
)
def summarize_orders(
    orders: DataFrame,
) -> DataFrame:
    return orders.groupBy(
        "customer_id"
    ).sum(
        "amount"
    )
```

With the PySpark engine:

```text
Table            -> pyspark.sql.DataFrame
TransformOutput  -> pyspark.sql.DataFrame
DatabaseTable    -> pyspark.sql.DataFrame
```

## APIs

APIs provide synchronous request-response execution and are exposed as POST endpoints by Vortexify.

Runtime values are declared using the same input system as transforms.

```python
import pandas as pd

from vortexify import (
    Input,
    Table,
    vxfy_api,
)


@vxfy_api(
    "/customers/update",
    inputs={
        "customers": Table("shopify.customers"),
        "customer_id": Input(str),
        "name": Input(str),
    },
)
def update_customer(
    customers: pd.DataFrame,
    customer_id: str,
    name: str,
):
    ...

    return {
        "customer_id": customer_id,
        "updated": True,
    }
```

APIs support the following engines:

```text
pandas
duckdb
```

API responses must be JSON-serializable.

## Inputs and Resources

Objects declared in `inputs={...}` describe where function arguments come from.
The mapping keys are function argument names; the reference strings identify resources in your project.

The function itself receives the resolved runtime value.

### Table

Reference a synced table using `connector.sync`, or an uploaded table using
`_upload.table_name`. `_upload` is reserved and cannot be a connector name:

```python
Table("shopify.orders")
Table("_upload.customers")  # Published with: vortexify upload table customers.csv --name customers
```

Runtime resolution depends on the selected engine:

```text
pandas   -> pandas.DataFrame
pyspark  -> pyspark.sql.DataFrame
duckdb   -> registered DuckDB relation
```

### TransformOutput

Reference the tabular output of another Transform:

```python
TransformOutput("forecast")
```

For a transform returning one DataFrame, use its name alone. For a transform
returning a dictionary of DataFrames, select an output using `transform.output`:

```python
TransformOutput("regional_forecast.weekly")
```

The output selector is required for dictionary outputs. Vortexify resolves the
appropriate upstream output for the current run.

For trigger-based workflows, this allows downstream transforms to receive the output associated with the specific upstream run that triggered them.

Runtime resolution follows the same engine behavior as `Table`.

### Secret

Reference a project secret created through Vortexify, for example with `vortexify secret set api_key`:

```python
Secret("api_key")
```

At runtime, the secret is resolved to its stored value.

```python
def call_service(
    api_key: str,
):
    ...
```

### Input

Declare a scalar value supplied at runtime:

```python
Input(str)
Input(int)
Input(float)
Input(bool)
```

Defaults may also be provided:

```python
Input(int, default=30)
```

Supported scalar types are:

```text
str
int
float
bool
```

The function receives the resolved scalar directly:

```python
def generate_forecast(
    lookback_days: int,
):
    ...
```

## Databases

Vortexify supports two different database access patterns.

### DatabaseTable

Use `DatabaseTable("database.table")` when a database table should be consumed
as tabular input. It accepts one reference string, replacing the previous
`DatabaseTable(database, table)` constructor.

```python
from vortexify import (
    DatabaseTable,
    vxfy_transform,
)


@vxfy_transform(
    engine="pandas",
    inputs={
        "orders": DatabaseTable("operations.orders"),
    },
)
def analyze_orders(
    orders: pd.DataFrame,
):
    ...
```

`DatabaseTable` is read-only and resolves according to the execution engine:

```text
pandas   -> pandas.DataFrame
pyspark  -> pyspark.sql.DataFrame
duckdb   -> registered DuckDB relation
```

### Database

Use `Database` when a function needs operational access to a managed database.

```python
from vortexify import (
    Database,
    vxfy_api,
)


@vxfy_api(
    "/orders/create",
    inputs={
        "db": Database(
            "operations",
            tables=[
                "orders",
                "customers",
            ],
            mode="read_write",
        ),
    },
)
def create_order(
    db,
):
    ...
```

At runtime, `Database` resolves to a permission-scoped Postgres connection.

Supported modes are:

```text
read
read_write
```

`read_write` connections are intended for operational SQL such as:

```text
SELECT
INSERT
UPDATE
DELETE
```

Manage database schema changes through your project's database resource.

The declared `tables` identify the database resources the function expects to access and can be used by Vortexify for dependency tracking and permission enforcement.

## Compute

All three compute types accept an optional `size` preset: `"xsmall"`, `"small"`, `"medium"`, `"large"`, or `"xlarge"`.

```python
from vortexify import ApiCompute, TransformCompute, TransformSparkCompute

transform_compute = TransformCompute(size="small")
spark_compute = TransformSparkCompute(size="large")
api_compute = ApiCompute(size="xsmall")

# Override individual resources while keeping the preset's other defaults.
custom_compute = TransformCompute(size="medium", memory=8192)
```

Pass these objects through the decorator's `compute=` argument, or declare `compute` on a Sync subclass. Selecting `size` fills unspecified (or `None`) resource fields with the SDK defaults below. Explicit resource values override the preset. The resolved values are included when the compute object is serialized, along with its `size`.

When `size` is omitted, unspecified fields remain `None` for Vortexify to resolve. Available allocations depend on your project and organization limits.

All memory, disk, and storage values below are **MiB**. Spark executor resources are **per executor**; `executor_instances` is the worker count.

**TransformCompute presets**

| Size | `memory` | `cores` | `disk` |
| --- | --- | --- | --- |
| `xsmall` | 1024 | 1 | 2048 |
| `small` | 2048 | 1 | 4096 |
| `medium` | 4096 | 2 | 8192 |
| `large` | 8192 | 4 | 16384 |
| `xlarge` | 16384 | 8 | 32768 |

**TransformSparkCompute presets**

| Size | `driver_memory` | `driver_cores` | `driver_disk` | `executor_memory` | `executor_cores` | `executor_disk` | `executor_instances` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `xsmall` | 1024 | 1 | 4096 | 2048 | 1 | 4096 | 1 |
| `small` | 2048 | 1 | 8192 | 4096 | 2 | 8192 | 2 |
| `medium` | 4096 | 2 | 16384 | 8192 | 2 | 16384 | 2 |
| `large` | 8192 | 4 | 32768 | 16384 | 4 | 32768 | 4 |
| `xlarge` | 16384 | 4 | 65536 | 32768 | 8 | 65536 | 8 |

**ApiCompute presets**

| Size | `memory` | `storage` |
| --- | --- | --- |
| `xsmall` | 256 | 512 |
| `small` | 512 | 512 |
| `medium` | 1024 | 1024 |
| `large` | 2048 | 2048 |
| `xlarge` | 4096 | 4096 |

For example:

```python
compute = TransformCompute(size="medium", memory=8192)
assert compute.memory == 8192  # Explicit override.
assert compute.cores == 2      # Medium preset.
assert compute.disk == 8192    # Medium preset.

# Inspect defaults without constructing a runtime configuration.
print(dict(TransformCompute.PRESETS["medium"]))
```

Each compute class exposes a read-only `PRESETS` mapping. Overrides apply only to the instance you create.


Transforms and Syncs can define compute requirements using `TransformCompute`.

```python
from vortexify import TransformCompute


compute = TransformCompute(
    memory=4096,
    cores=2,
    disk=8192,
)
```

PySpark transforms use `TransformSparkCompute`:

```python
from vortexify import TransformSparkCompute


compute = TransformSparkCompute(
    driver_memory=4096,
    driver_cores=2,
    driver_disk=8192,
    executor_memory=8192,
    executor_cores=4,
    executor_disk=16384,
    executor_instances=3,
)
```

APIs use `ApiCompute`:

```python
from vortexify import ApiCompute


compute = ApiCompute(
    memory=2048,
    storage=4096,
)
```

Memory and storage values are expressed in MiB.

## Scheduling

Transforms can run on cron schedules or when upstream resources update.

### Cron

```python
from vortexify import CronSchedule


CronSchedule(
    expression="0 2 * * *",
)
```

### Triggers

```python
from vortexify import (
    Table,
    TransformOutput,
    TriggerSchedule,
)


TriggerSchedule(
    mode="all",
    triggers=[
        Table("shopify.orders"),
        TransformOutput("forecast"),
    ],
)
```

Trigger modes are:

```text
any
all
```

`any` is the default and runs when any configured dependency updates.

`all` runs after all configured dependencies have updated.

Example:

```python
@vxfy_transform(
    inputs={
        "orders": Table("shopify.orders"),
        "forecast": TransformOutput("forecast"),
    },
    schedule=TriggerSchedule(
        mode="all",
        triggers=[
            Table("shopify.orders"),
            TransformOutput("forecast"),
        ],
    ),
)
def build_plan(
    orders,
    forecast,
):
    ...
```

## Validation

A resource directory may define one validation function using `vxfy_validate`.

Production transforms run validation against real output and return a structured `ValidationResult`. Findings and validator exceptions are reported without failing a successful transform or blocking table publication. Deployed API requests skip automatic validation; required request and business checks belong in the API implementation.

Runtime results include a separate `validation` report with `status` (`passed`, `issues_found`, `error`, or `skipped`), `valid`, `issues`, and `error`. Skipped reports include a reason (`not_defined` or `deployed_api`). Reports are also emitted as JSON logs and saved with the job. SDK mock tests do not automatically invoke these validators.

```python
import pandas as pd

from vortexify import (
    ValidationIssue,
    ValidationResult,
    vxfy_validate,
)


@vxfy_validate(
    engine="pandas",
)
def validate_output(
    output: pd.DataFrame,
) -> ValidationResult:
    issues = []

    if output.empty:
        issues.append(
            ValidationIssue(
                code="empty_output",
                message="Output cannot be empty.",
            )
        )

    return ValidationResult(
        issues=issues
    )
```

Validation issues may contain:

```text
message
level
code
field
```

Severity levels are:

```text
error
warning
```

An error makes the validation result invalid. Warnings are recorded without causing validation to fail.

DuckDB can be used for validation of large tabular outputs:

```python
@vxfy_validate(
    engine="duckdb",
)
def validate_output(
    conn,
) -> ValidationResult:
    issues = []

    invalid_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM output
        WHERE quantity < 0
        """
    ).fetchone()[0]

    if invalid_count:
        issues.append(
            ValidationIssue(
                code="negative_quantity",
                field="quantity",
                message="Quantity cannot be negative.",
            )
        )

    return ValidationResult(
        issues=issues
    )
```

For non-tabular results such as API responses, the validation engine can be omitted.

## Testing

Use `@vxfy_mocks` to declare mock scenarios and `@vxfy_test(mocks=...)` to
write assertions against a transform or API. Mock factories are ordinary Python
functions: they can construct inline data or generate larger datasets.

```python
import pandas as pd

from vortexify import Input, Table, vxfy_transform
from vortexify.testing import vxfy_mocks, vxfy_test


@vxfy_transform(inputs={
    "orders": Table("shopify.orders"),
    "multiplier": Input(int, default=1),
})
def transform(orders, multiplier):
    return {"quantity": int(orders["quantity"].sum()) * multiplier}


@vxfy_mocks
def small_orders():
    return {
        "orders": pd.DataFrame({"quantity": [100, 200, 150]}),
    }


@vxfy_test(mocks=small_orders)
def test_total(run):
    assert run()["quantity"] == 450
    assert run()["quantity"] == 450
```

The factory's function name identifies the scenario. Multiple tests can reference
the same factory. Each `run()` calls it again, validates its dictionary, and
executes the resource directly in the test's Python process. Return fresh mutable
objects from factories so repeated runs remain independent. `run()` accepts no
arguments; different inputs belong in separate mock scenarios.

Mock keys must match the resource's declared input names. Missing scalar `Input`
values use their declared defaults; optional scalars without defaults receive
`None`. Other inputs must be supplied explicitly. Scalar values must match their
declared type, without coercion. The runner never resolves live tables, secrets,
or database connections:

| Declaration | Mock value |
| --- | --- |
| `Table`, `TransformOutput`, `DatabaseTable` | Pandas DataFrame; existing Spark DataFrames are also accepted for PySpark |
| `Input` | Declared scalar type, or `None` when optional |
| `Database` | Connection test double supporting `cursor()` or `execute()` |
| `Secret` | Explicit non-`None` mock value |

Pandas resources receive DataFrames directly. DuckDB resources receive a fresh
in-memory `conn`, with tables registered under the **input names**. Other inputs
are passed as normal keyword arguments. Returned DuckDB connections or relations
are materialized as Pandas DataFrames before the connection closes; Arrow readers
are materialized as Arrow tables. Avoid nesting lazy DuckDB results inside other
objects. The name `conn` is reserved for the DuckDB connection.

PySpark resources receive Spark DataFrames. Use the Spark session provided by the test environment, or supply Spark DataFrames from your mock factory. Clean up any connections or sessions your factory creates.

### Monkey-patching

Tests can use standard Python patches around `run()`:

```python
from unittest.mock import patch


@vxfy_test(mocks=small_orders)
def test_supplier_outage(run):
    with patch("inventory_optimizer.main.get_supplier_status", return_value=False):
        result = run()
        assert result["supplier_unavailable"] is True
```

Patch the name used by the resource module. Import resource modules under stable,
unique names so patches address the actual imported objects. The runner executes
tests serially. Patches affect the Python process running the test, so keep them scoped to the test body.

### Run your resource tests

Save the resource and run its mock tests through the CLI:

```sh
vortexify commit --type transform --resource order_totals
vortexify test transform order_totals --wait
```

Use `vortexify test api NAME --wait` for an API. Each resource folder should define one transform or API and can include multiple mock scenarios and tests. Decorated tests receive their `run` callable from Vortexify; they are not ordinary pytest tests. Production output validation is separate from mock tests.

## Connectors

Custom connectors define how Vortexify connects to external systems.

### Configuration schemas (`config.json`)

Define the configuration dictionary for each connector or sync in a **JSON Schema file named `config.json`**, alongside its Python implementation:

```text
connectors/postgres/
├── connector.py
└── config.json

syncs/orders/
├── sync.py
└── config.json
```

The file describes configuration fields, not actual configuration values. Connector schemas describe connection settings such as host and credentials; sync schemas describe extraction settings such as table selection and source-specific options. Sync checkpoint state is separate and does not belong in this schema.

For example, a PostgreSQL connector's `config.json`:

```json
{
  "type": "object",
  "properties": {
    "host": {
      "title": "Host",
      "description": "Hostname or IP address of the PostgreSQL server.",
      "examples": [
        "database.example.com"
      ],
      "order": 0,
      "type": "string"
    },
    "port": {
      "title": "Port",
      "description": "Port used by the PostgreSQL server.",
      "default": 5432,
      "examples": [
        5432
      ],
      "order": 1,
      "type": "integer",
      "minimum": 1,
      "maximum": 65535
    },
    "database": {
      "title": "Database",
      "description": "Name of the PostgreSQL database to connect to.",
      "examples": [
        "production"
      ],
      "order": 2,
      "type": "string"
    },
    "username": {
      "title": "Username",
      "description": "Username used to authenticate with PostgreSQL.",
      "examples": [
        "postgres"
      ],
      "order": 3,
      "type": "string"
    },
    "password": {
      "title": "Password",
      "description": "Password used to authenticate with PostgreSQL.",
      "order": 4,
      "type": "string",
      "x-vortexify-secret": true
    },
    "sslmode": {
      "title": "SSL Mode",
      "description": "PostgreSQL TLS policy. Use verify-full with a trusted server certificate for verified TLS.",
      "type": "string",
      "enum": [
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full"
      ],
      "default": "prefer",
      "order": 5
    }
  },
  "required": [
    "host",
    "database",
    "username",
    "password"
  ]
}
```

The schema uses:

| Keyword | Purpose |
| --- | --- |
| `type`, `properties`, `required` | Define the configuration object, field types, and required fields. |
| `minimum`, `maximum`, `enum` | Constrain accepted values. |
| `title`, `description`, `examples` | Provide labels, help text, and examples for configuration forms. |
| `default` | Declare a default value; the platform must explicitly apply defaults when preparing configuration. Schema validation alone does not populate them. |
| `order` | Custom form metadata specifying display order; it is not a standard JSON Schema validation keyword. |
| `x-vortexify-secret` | Marks a sensitive configuration field. Supply its value through Vortexify configuration rather than storing credentials in the schema. |

A sync can define its own `config.json`, independently of its connector:

```json
{
  "type": "object",
  "properties": {
    "table": {
      "title": "Table",
      "type": "string",
      "order": 0
    },
    "page_size": {
      "title": "Page Size",
      "type": "integer",
      "minimum": 1,
      "default": 1000,
      "order": 1
    }
  },
  "required": [
    "table"
  ]
}
```

Vortexify uses the schema for configuration forms and supplies configured values through `self.config`, for example `self.config["host"]` in a connector or `self.config["table"]` in a sync.

Keep actual credentials and extraction checkpoints out of `config.json`. When constructing a connector or sync directly in Python, pass its configuration dictionary explicitly.

`vendor_domain` is optional display/branding metadata, for example `"stripe.com"`.
Custom connectors can leave it as `None`.

```python
from vortexify import Column, Connector, DiscoveredTable


class ExampleConnector(Connector):
    vendor_domain = None

    def client(self):
        if self._client is None:
            self._client = SomeClient(
                api_key=self.config["api_key"],
            )

        return self._client

    def check(self) -> bool:
        self.client().ping()
        return True

    def discover(self) -> list[DiscoveredTable]:
        return [
            DiscoveredTable(
                name="orders",
                schema=[
                    Column(name="id", type="string", nullable=False),
                    Column(name="amount", type="decimal"),
                    Column(name="updated_at", type="timestamp"),
                ],
                # Omit preview for metadata-only discovery.
            ),
        ]

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None
```

A Connector is responsible for:

```text
creating and reusing a source client
verifying connectivity and credentials
discovering available source resources
```

`Connector.close()` is an optional cleanup hook with a **no-op default**, so existing connectors need not implement it. Override it to release owned client connections, sessions, or other source resources. Cleanup should be safe to repeat, use an already initialized `_client` rather than call `client()`, and must not commit data or advance checkpoints. The example above clears the cached client even if closing fails.

Connectors support context managers:

```python
with ExampleConnector(config=connector_config) as connector:
    tables = connector.discover()
```

Entering the block returns the connector without initializing its client. Exiting always calls `close()`, including when the body raises; exceptions are not suppressed, and cleanup failures propagate. When using a connector directly, use a `with` block or call `close()` in `finally`. Implement `close()` for any source client that needs cleanup.

`discover()` returns typed `DiscoveredTable` objects with a stable source `name`, a `schema` of `Column(name, type, nullable)` entries, and optional `preview` rows. Column `type` is a source-defined, nonempty string; `nullable` defaults to `True`. Column names must be unique within a table. Discovery can use known schema definitions, source catalog metadata, or source-specific metadata requests.

`preview=None` means rows were not sampled or a preview is unavailable; `preview=[]` means sampling returned no rows. Preview rows must be JSON-compatible dictionaries and are limited to **100 rows per table** (larger lists raise a validation error). Use strings for decimal values and ISO-formatted timestamps when needed. Previews are optional and are never fetched automatically by the SDK:

```python
table = DiscoveredTable(
    name="orders",
    schema=[Column(name="id", type="string", nullable=False)],
    preview=[{"id": "order-123"}],
)

# For API responses, serialize the field alias as "schema".
payload = table.model_dump(by_alias=True, exclude_none=True)
columns = table.schema
```

Discovery previews are optional JSON sample rows. Use a dedicated sampling read; discovery should not start extraction or change extraction checkpoints. For a configured sync, implement `preview()` as described below.

## Syncs

Syncs extract tabular data from a Connector. Their `config` dictionary is described by the resource's `config.json` JSON Schema; see [Configuration schemas](#configuration-schemas-configjson).

Syncs support two modes:

```text
full
incremental
```

`full` is the default, so full syncs do not need to declare a mode.
Incremental syncs should declare `mode = "incremental"` on their class:

```python
class OrdersSync(Sync):
    mode = "incremental"

    def extract(self, *, avg_row_size_bytes: float | None = None):
        ...
```

`state` is intended for incremental sync state such as cursors, timestamps,
or other checkpoints. Incremental sync implementations can read and update
`self.state` to track their extraction progress.

Syncs can declare an optional **cron-only** schedule on their class:

```python
from vortexify import CronSchedule, Sync


class OrdersSync(Sync):
    mode = "incremental"
    schedule = CronSchedule(expression="*/15 * * * *")

    def extract(self, *, avg_row_size_bytes: float | None = None):
        ...
```

This example requests a run every 15 minutes. `schedule` defaults to `None`, meaning no scheduled runs; full syncs can also declare a cron schedule. Subclasses inherit a schedule unless they override it, and can set `schedule = None` to disable it. `TriggerSchedule`, raw cron strings, and other schedule values are rejected when the subclass is defined.

Vortexify runs scheduled syncs after deployment. Defining a schedule in Python does not start a local scheduler.

```python
import pandas as pd

from vortexify import (
    Sync,
    TransformCompute,
)


class OrdersSync(Sync):
    compute = TransformCompute(
        memory=4096,
        cores=2,
        disk=8192,
    )

    def extract(self, *, avg_row_size_bytes: float | None = None):
        yield pd.DataFrame(
            ...
        )
```

`extract()` yields Pandas DataFrames containing rows retrieved from the source.

Yield batches from `extract()` and use `self.state` to track incremental progress. Vortexify persists extraction checkpoints as the output is saved.

### Preview, row-size estimates, and extraction

Sync authors define two separate methods:

```python
from collections.abc import Iterator

import pandas as pd
from vortexify import Sync, TransformCompute


class OrdersSync(Sync):
    compute = TransformCompute(size="small")

    def preview(self) -> pd.DataFrame:
        # A dedicated source sampling read; no production checkpoints.
        return pd.DataFrame(self.client.sample_orders(limit=100))

    def extract(
        self,
        *,
        avg_row_size_bytes: float | None = None,
    ) -> Iterator[pd.DataFrame]:
        # Runtime-provided estimate, available before the first batch.
        # It is None when no saved preview estimate exists.
        row_bytes = avg_row_size_bytes

        # Declared resources, with preset defaults already resolved.
        memory_mib = self.compute.memory if self.compute else None
        cores = self.compute.cores if self.compute else None
        disk_mib = self.compute.disk if self.compute else None

        # Use these optional hints to choose a source-specific batching
        # strategy, then fetch/yield DataFrames and update self.state.
        ...
```

`preview()` is an **instance method returning a DataFrame**, implemented by the author. Its default raises `NotImplementedError`; it never falls back to `extract()`. A source that cannot safely sample can leave preview unsupported. Real runs still work with `avg_row_size_bytes=None`.

`extract()` receives the optional preview-derived average explicitly as a keyword-only argument. It is not a constructor setting, an automatically calculated property, or a checkpoint value. `self.compute` remains available for declared memory/disk (MiB) and CPU cores. Compute or individual fields can be `None`; these are requested allocations, not measurements of free resources. The SDK does not choose a page size or batching strategy automatically.

Keep preview sampling separate from extraction. Preview should not consume records, acknowledge source messages, or advance checkpoints.

`SyncPreview.from_dataframe(data, limit=100)` validates that `data` is a DataFrame, copies up to `limit` rows and calculates their average UTF-8 newline-delimited JSON size (ISO dates, including newline bytes). It makes no source requests. `limit` must be an integer between 1 and 100 and bounds the measured sample, not the amount an author's preview already fetched. Returned fields are:

- `data`: the copied sample, with a fresh sequential index.
- `avg_row_size_bytes`: serialized sample bytes divided by row count; `None` for empty output.

This is a sampling estimate, not an exact size for every output format. Preview authors must use appropriate source reads: temporary Vortexify state cannot undo consuming or acknowledging records externally. `DiscoveredTable.preview` remains optional JSON metadata for discovery; discovery never invokes sync preview automatically.

## Agents

Agents can be given data context, API tools, and built-in capabilities. Agent declarations do not support tasks or task schedules; passing `tasks=` raises a validation error.

Set `provider` to `"openai"` or `"anthropic"` and `model` to that provider's model ID or dated snapshot ID:

```python
agent = Agent(
    provider="openai",
    model="your-openai-model-id",
    prompt="Help manage operations.",
)
```

For Anthropic, use `provider="anthropic"` with a supported Anthropic model ID. Both fields are optional: omit them to use the defaults available in your Vortexify environment. A configured model must be available for the selected provider.

```python
from vortexify import (
    Agent,
    AgentCapabilities,
    ApiRunner,
    Table,
    TransformOutput,
)


agent = Agent(
    prompt="Help manage operations.",
    context=[
        Table("shopify.orders"),
        TransformOutput("forecast"),
    ],
    tools=[
        ApiRunner("save_schedule"),
    ],
    capabilities=AgentCapabilities(
        sql_analysis=True,
        chart_generation=True,
    ),

)
```

Agent context can include:

```text
Table
TransformOutput
```

Uploaded files and documentation are managed as agent context by the platform;
they are not declared through the Python SDK.

`Agent.tools` exposes project APIs through `ApiRunner`. Optional capabilities add built-in analysis and chart tools:

- `sql_analysis=True` lets the agent inspect and query the tables in its context.
- `chart_generation=True` lets the agent create chart configurations from completed analyses. Enable SQL analysis too when the agent needs to query its own chart data.

Chart configuration contains `chartType`, `xKey`, and `yKeys`. Supported types are Bar, StackedBar, GroupedBar, Line, MultiLine, Scatter, and Pie. Chart results contain `{ success: true, chart: { query_id, name, config, row_count } }` and require a complete analysis with at most 1000 rows. React apps fetch the saved rows with `client.getAnalysisData(chart.query_id)` and render with their chart library; your app controls how charts are rendered.

Both capabilities default to false. Unknown capability fields are rejected. Uploaded documentation is searched through a separate platform-managed tool when attached.

## Find resource examples

Use the Vortexify CLI to search for project blueprints and add examples to your project:

```sh
vortexify blueprints search "data pipeline"
vortexify blueprints attach BLUEPRINT_NAME
vortexify blueprints read BLUEPRINT_NAME
```

## License

The Vortexify SDK is source-available for noncommercial use.

Commercial use of the SDK requires permission from Vortexify.

Code, applications, workflows, configurations, and other materials created by users using the Vortexify SDK remain the property of those users and are not subject to the SDK license solely because they use or interact with the SDK.


Python SDK 0.1.1 removes `Agent.name`. Declare `Agent(prompt=..., context=..., tools=...)`;
use the registered resource name or ID in CLI/React calls. When upgrading existing
source, remove the `name=` argument and update `requirements.in` to `vortexify==0.1.1`.

<!-- sdk-release-history -->
## Changelog

### v0.1.1

- Remove Agent.name; agents use their registered resource identity. Remove name= from existing declarations when upgrading.

### v0.1.0

- Initial release.
<!-- /sdk-release-history -->
