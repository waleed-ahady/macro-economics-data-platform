# Operations

Database migrations run before the API starts. Docker Compose waits until PostgreSQL passes its health check before starting the application service.

Refresh the configured dataset with:

```bash
macro-data ingest
```

The ingestion job is incremental. It revisits a configurable number of recent years to detect revisions while avoiding a full historical download on every run.

The `/health` endpoint reports database connectivity, catalog size, observation count, and the latest ingestion result.

The GitHub Actions workflow in `.github/workflows/ingest.yml` can run the same migration and ingestion commands against a hosted PostgreSQL database. The only required production secret for that workflow is `DATABASE_URL`; the World Bank Indicators API does not require an API key.
