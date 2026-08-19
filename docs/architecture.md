# Architecture

The platform is deliberately small: one external data provider, one canonical relational model, one API, and one dashboard.

```text
World Bank Indicators API
          |
          v
  scheduled ingestion
          |
          v
validation + normalization
          |
          v
      PostgreSQL
       /      \
      v        v
  FastAPI   revision history
      |
      v
  Streamlit dashboard
```

The World Bank client is responsible only for HTTP communication and pagination. The ingestion service maps provider records into the platform's canonical country/indicator model, validates them, and performs idempotent upserts.

A configurable multi-year lookback is used on every refresh. This intentionally re-reads recent periods because published macroeconomic observations can be revised. When an existing value changes, the current observation is updated and the previous value is stored in `observation_revisions`.

The dashboard reads through FastAPI rather than querying PostgreSQL directly. That keeps the user interface independent from storage details and makes the same API usable by notebooks, scripts, or another frontend.

PostgreSQL is private to the Docker Compose network. Only the API and dashboard are exposed to the host.
