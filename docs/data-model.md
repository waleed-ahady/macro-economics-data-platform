# Data model

The database keeps provider identifiers for traceability while exposing clearer canonical indicator names to users.

## `economic_series`

One row represents one indicator for one country. For example, German consumer price inflation is stored with:

- internal series ID: `WB:DEU:FP.CPI.TOTL.ZG`
- country code: `DEU`
- canonical indicator: `inflation`
- provider indicator: `FP.CPI.TOTL.ZG`
- source: `WORLD_BANK`

The deterministic series ID makes ingestion repeatable and avoids provider-specific IDs leaking into most user-facing workflows.

## `observations`

Stores the latest known value for each `(series_id, observation_date)` pair. A unique constraint makes repeated ingestion idempotent.

## `observation_revisions`

Records the previous and replacement value when the provider revises an observation. The application therefore keeps a simple audit trail instead of silently overwriting history.

## `ingestion_runs`

Stores one audit record for each refresh, including timestamps, status, requested series, completed series, inserted observations, updated observations, and any error message.
