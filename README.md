# Macro Economics Data Platform

A production-oriented platform for exploring and comparing macroeconomic indicators across major economies.

The project collects data from the World Bank Indicators API, standardizes it into a consistent country-and-indicator model, stores it in PostgreSQL, exposes it through FastAPI, and presents it through an interactive Streamlit dashboard.

The goal is to make cross-country macroeconomic data easier to explore without requiring users to work directly with provider-specific indicator codes, manually align datasets, or repeatedly download and clean the same data.

## Dashboard

The dashboard is built around common macroeconomic questions: how countries compare today, how an individual economy has changed over time, how several economies have diverged, and whether two economic indicators appear to move together.

### Global snapshot

The Global Snapshot provides a quick cross-country view of a selected indicator. Economies are ranked using their latest available observation, with the corresponding reporting year shown explicitly.

![Global snapshot](docs/images/global-snapshot.png)

This is useful for questions such as:

* Which economies currently have the highest inflation?
* Where is GDP growth strongest?
* Which countries have the highest unemployment rates?
* How does GDP per capita differ across the selected economies?

### Country profile

The Country Profile focuses on a single economy and brings together its main macroeconomic indicators.

![Country profile](docs/images/country-profile.png)

It provides a compact view of indicators such as GDP growth, inflation, unemployment, and GDP per capita, together with historical series that make it easier to understand how the economy has evolved.

### Compare economies

The comparison view makes it possible to follow the same indicator across multiple countries over time.

![Compare economies](docs/images/compare-economies.png)

Users can compare reported values directly or apply simple analytical transformations such as annual differences and rolling z-scores. This makes the page useful both for level comparisons and for identifying periods in which countries moved unusually far from their own historical patterns.

### Indicator relationships

The Indicator Relationships page compares two macroeconomic indicators across countries for a selected year.

![Indicator relationships](docs/images/indicator-relationships.png)

For example, it can be used to explore relationships between:

* GDP per capita and inflation
* GDP growth and unemployment
* Trade openness and GDP per capita
* Investment and economic growth

The page also reports the cross-country correlation for the selected observations. This is presented as descriptive analysis rather than evidence of causality.

### Data catalog

The Data Catalog provides a searchable view of the series available in the platform, including countries, indicators, units, provider codes, and available periods.

It is intended as a reference for understanding the underlying dataset and can also be used to download catalog information.

## Data coverage

The current version covers 14 major economies:

`Australia`, `Brazil`, `Canada`, `China`, `France`, `Germany`, `India`, `Italy`, `Japan`, `Mexico`, `South Korea`, `Spain`, `United Kingdom`, and `United States`.

Countries are identified internally using ISO-3 codes:

`AUS`, `BRA`, `CAN`, `CHN`, `FRA`, `DEU`, `IND`, `ITA`, `JPN`, `MEX`, `KOR`, `ESP`, `GBR`, `USA`.

The platform currently tracks 11 macroeconomic indicators.

| Indicator                 | World Bank code     | Description                               |
| ------------------------- | ------------------- | ----------------------------------------- |
| `gdp_growth`              | `NY.GDP.MKTP.KD.ZG` | Real GDP growth                           |
| `gdp_current_usd`         | `NY.GDP.MKTP.CD`    | GDP in current US dollars                 |
| `gdp_per_capita`          | `NY.GDP.PCAP.CD`    | GDP per capita                            |
| `inflation`               | `FP.CPI.TOTL.ZG`    | Consumer price inflation                  |
| `unemployment_rate`       | `SL.UEM.TOTL.ZS`    | Unemployment rate                         |
| `current_account_balance` | `BN.CAB.XOKA.GD.ZS` | Current-account balance as a share of GDP |
| `trade_openness`          | `NE.TRD.GNFS.ZS`    | Exports and imports as a share of GDP     |
| `exports_share_gdp`       | `NE.EXP.GNFS.ZS`    | Exports as a share of GDP                 |
| `imports_share_gdp`       | `NE.IMP.GNFS.ZS`    | Imports as a share of GDP                 |
| `gross_capital_formation` | `NE.GDI.TOTL.ZS`    | Investment as a share of GDP              |
| `population`              | `SP.POP.TOTL`       | Total population                          |

The catalog is configuration-driven, so additional countries or World Bank indicators can be added without changing the ingestion pipeline itself.

## How the platform works

The project follows a simple end-to-end data flow:

```text
World Bank Indicators API
          |
          v
  Scheduled ingestion
          |
          v
Validation and normalization
          |
          v
      PostgreSQL
          |
          v
       FastAPI
          |
          v
      Streamlit
```

The ingestion service retrieves data from the World Bank API and maps provider-specific series into a canonical internal model.

For example, users can work with:

```text
inflation
gdp_growth
unemployment_rate
gdp_per_capita
```

without needing to know the corresponding World Bank indicator codes.

The dashboard does not connect directly to PostgreSQL. All data is retrieved through the FastAPI service, which keeps the analytical frontend independent from the storage layer and makes the REST API useful as a standalone interface.

## Data ingestion

The ingestion pipeline is designed to be repeatable and safe to run periodically.

It performs incremental updates, validates incoming observations, avoids duplicate records, and revisits recent years to detect revisions published by the World Bank.

Missing observations remain missing rather than being automatically interpolated or filled. This keeps the stored dataset faithful to the source.

Economic data can also change after its first publication. The platform therefore re-fetches a configurable recent period during each refresh. When an existing observation changes, the latest value becomes the current observation and the previous value is written to a revision history table together with the time the change was detected.

This provides a lightweight audit trail without introducing the complexity of a full vintage-data system.

## API

FastAPI exposes the standardized macroeconomic data through a REST interface.

Interactive API documentation is available through Swagger UI at:

```text
http://localhost:8000/docs
```

Examples include:

```bash
# Available economies
curl http://localhost:8000/v1/countries
```

```bash
# Available canonical indicators
curl http://localhost:8000/v1/indicators
```

```bash
# German inflation history
curl "http://localhost:8000/v1/countries/DEU/indicators/inflation"
```

```bash
# Compare inflation across several economies
curl --get "http://localhost:8000/v1/analytics/compare-countries" \
  --data-urlencode "indicator=inflation" \
  --data-urlencode "countries=USA" \
  --data-urlencode "countries=DEU" \
  --data-urlencode "countries=JPN" \
  --data-urlencode "countries=BRA"
```

Individual series can also be downloaded as CSV:

```bash
curl -OJ "http://localhost:8000/v1/series/WB:DEU:FP.CPI.TOTL.ZG/observations.csv"
```

## Technology

The project is built with:

* **Python** for application and data-processing logic
* **World Bank Indicators API** as the macroeconomic data source
* **PostgreSQL** for production data storage
* **SQLAlchemy** for database access
* **Alembic** for schema migrations
* **FastAPI** for the REST API
* **Streamlit** for the analytical dashboard
* **Plotly** for interactive visualizations
* **Docker Compose** for local orchestration
* **pytest** for automated testing
* **Ruff** for linting and code-quality checks
* **GitHub Actions** for continuous integration and scheduled ingestion

## Repository structure

```text
macro-economics-data-platform/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── ingest.yml
├── alembic/
│   └── versions/
├── configs/
│   └── world_bank.yml
├── docs/
│   ├── images/
│   ├── architecture.md
│   ├── data-model.md
│   └── operations.md
├── src/
│   └── macro_data_platform/
│       ├── api/
│       ├── clients/
│       ├── dashboard/
│       ├── services/
│       ├── cli.py
│       ├── config.py
│       ├── database.py
│       ├── logging.py
│       ├── models.py
│       └── schemas.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.dashboard
├── Makefile
└── pyproject.toml
```

## Running the project

No external API key is required.

With Docker:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api macro-data ingest
```

Once the data has been ingested:

* Dashboard: `http://localhost:8501`
* API documentation: `http://localhost:8000/docs`
* Health endpoint: `http://localhost:8000/health`

PostgreSQL runs inside the Docker network and is not exposed on host port `5432`.

The stack can be stopped with:

```bash
docker compose down
```

The database volume can also be removed when a completely clean environment is needed:

```bash
docker compose down -v
```

## Local development

The application can also run without Docker using Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,dashboard]"
alembic upgrade head
macro-data ingest
```

The API and dashboard can then be started separately:

```bash
uvicorn macro_data_platform.api.main:app --reload
```

```bash
streamlit run src/macro_data_platform/dashboard/app.py
```

SQLite is used as the default lightweight database for local development, while the Docker environment uses PostgreSQL.

## Testing and code quality

The project includes automated tests for the main data and application workflows.

Coverage includes:

* World Bank API responses
* ingestion idempotency
* revision detection
* input validation
* analytical transformations
* country and indicator catalogs
* cross-country API queries
* API behavior

Tests and linting can be run with:

```bash
pytest
ruff check src tests
```



