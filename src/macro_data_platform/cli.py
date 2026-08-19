import json
from pathlib import Path

import typer
from sqlalchemy import select

from macro_data_platform.clients.world_bank import WorldBankClient
from macro_data_platform.config import get_settings
from macro_data_platform.database import Base, SessionLocal, engine
from macro_data_platform.logging import configure_logging
from macro_data_platform.models import EconomicSeries
from macro_data_platform.services.ingestion import WorldBankIngestionService, load_world_bank_config

app = typer.Typer(no_args_is_help=True, help="Operate the Macro Economics Data Platform.")


@app.command("init-db")
def init_db() -> None:
    """Create database tables directly. Alembic is preferred outside local development."""
    Base.metadata.create_all(engine)
    typer.echo("Database tables created.")


@app.command("ingest")
def ingest(
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Override the World Bank country and indicator configuration.",
    ),
) -> None:
    """Refresh configured macroeconomic data and record revisions."""
    settings = get_settings()
    configure_logging(settings.log_level)
    config = load_world_bank_config(config_path or settings.world_bank_config_path)
    with WorldBankClient(
        base_url=settings.world_bank_base_url,
        timeout_seconds=settings.request_timeout_seconds,
    ) as client:
        service = WorldBankIngestionService(
            SessionLocal,
            client,
            lookback_years=settings.world_bank_lookback_years,
        )
        summary = service.run(config)
    typer.echo(json.dumps(summary.__dict__, indent=2))


@app.command("list-series")
def list_loaded_series() -> None:
    """List economic series currently registered in the database."""
    with SessionLocal() as session:
        items = session.scalars(
            select(EconomicSeries).order_by(
                EconomicSeries.country_code,
                EconomicSeries.indicator_code,
            )
        )
        for item in items:
            country = item.country_code or "---"
            indicator = item.indicator_code or item.series_id
            typer.echo(f"{country:3}  {indicator:28} {item.display_name}")


if __name__ == "__main__":
    app()
