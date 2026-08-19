import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from macro_data_platform.clients.world_bank import WorldBankClient, parse_world_bank_value
from macro_data_platform.models import (
    EconomicSeries,
    IngestionRun,
    Observation,
    ObservationRevision,
    RunStatus,
)
from macro_data_platform.services.validation import parse_observation_date, validate_observations

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorldBankCountryConfig:
    code: str
    name: str


@dataclass(frozen=True)
class WorldBankIndicatorConfig:
    code: str
    provider_id: str
    display_name: str
    category: str
    units: str
    start_year: int
    description: str | None = None


@dataclass(frozen=True)
class WorldBankConfig:
    countries: list[WorldBankCountryConfig]
    indicators: list[WorldBankIndicatorConfig]


@dataclass
class SeriesIngestionStats:
    inserted: int = 0
    updated: int = 0


@dataclass
class IngestionSummary:
    run_id: int
    provider: str
    status: str
    series_requested: int
    series_succeeded: int
    observations_inserted: int
    observations_updated: int


def load_world_bank_config(path: Path) -> WorldBankConfig:
    with path.open(encoding="utf-8") as config_file:
        payload = yaml.safe_load(config_file) or {}

    raw_countries = payload.get("countries", [])
    raw_indicators = payload.get("indicators", [])
    if not raw_countries or not raw_indicators:
        raise ValueError(f"World Bank configuration requires countries and indicators: {path}")

    countries = [
        WorldBankCountryConfig(code=str(item["code"]).upper(), name=str(item["name"]))
        for item in raw_countries
    ]
    indicators = [
        WorldBankIndicatorConfig(
            code=str(item["code"]),
            provider_id=str(item["provider_id"]),
            display_name=str(item["display_name"]),
            category=str(item.get("category") or "uncategorized"),
            units=str(item.get("units") or "Not specified"),
            start_year=int(item.get("start_year") or 1990),
            description=item.get("description"),
        )
        for item in raw_indicators
    ]

    country_codes = [item.code for item in countries]
    indicator_codes = [item.code for item in indicators]
    provider_ids = [item.provider_id for item in indicators]
    if len(country_codes) != len(set(country_codes)):
        raise ValueError("Duplicate country code in World Bank configuration")
    if len(indicator_codes) != len(set(indicator_codes)):
        raise ValueError("Duplicate indicator code in World Bank configuration")
    if len(provider_ids) != len(set(provider_ids)):
        raise ValueError("Duplicate provider indicator in World Bank configuration")
    return WorldBankConfig(countries=countries, indicators=indicators)


def values_differ(left: float | None, right: float | None, tolerance: float = 1e-12) -> bool:
    if left is None or right is None:
        return left is not right
    return abs(left - right) > tolerance


def upsert_observations(
    session: Session,
    series_id: str,
    normalized_observations: list[dict[str, Any]],
) -> SeriesIngestionStats:
    stats = SeriesIngestionStats()
    if not normalized_observations:
        return stats

    dates = [item["observation_date"] for item in normalized_observations]
    existing = {
        item.observation_date: item
        for item in session.scalars(
            select(Observation).where(
                Observation.series_id == series_id,
                Observation.observation_date.in_(dates),
            )
        )
    }

    for item in normalized_observations:
        observation_date = item["observation_date"]
        value = item.get("value")
        current = existing.get(observation_date)
        if current is None:
            session.add(
                Observation(
                    series_id=series_id,
                    observation_date=observation_date,
                    value=value,
                )
            )
            stats.inserted += 1
            continue

        if values_differ(current.value, value):
            session.add(
                ObservationRevision(
                    series_id=series_id,
                    observation_date=observation_date,
                    old_value=current.value,
                    new_value=value,
                )
            )
            current.value = value
            current.retrieved_at = datetime.now(UTC)
            stats.updated += 1
    return stats


class IngestionRunManager:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def start(self, provider: str, series_requested: int) -> int:
        with self.session_factory() as session:
            run = IngestionRun(provider=provider, series_requested=series_requested)
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.id

    def finish(
        self,
        run_id: int,
        *,
        status: str,
        succeeded: int,
        inserted: int,
        updated: int,
        error_message: str | None = None,
    ) -> None:
        with self.session_factory() as session:
            run = session.get(IngestionRun, run_id)
            if run is None:
                raise RuntimeError(f"Ingestion run {run_id} disappeared")
            run.status = status
            run.completed_at = datetime.now(UTC)
            run.series_succeeded = succeeded
            run.observations_inserted = inserted
            run.observations_updated = updated
            run.error_message = error_message
            session.commit()


class WorldBankIngestionService:
    """Ingest configured annual macroeconomic indicators from the World Bank."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        client: WorldBankClient,
        lookback_years: int = 5,
    ) -> None:
        self.session_factory = session_factory
        self.client = client
        self.lookback_years = lookback_years
        self.runs = IngestionRunManager(session_factory)

    def run(self, config: WorldBankConfig) -> IngestionSummary:
        series_requested = len(config.countries) * len(config.indicators)
        run_id = self.runs.start("WORLD_BANK", series_requested)
        total_inserted = 0
        total_updated = 0
        succeeded = 0

        try:
            for indicator in config.indicators:
                start_year = self._request_start_year(config.countries, indicator)
                records = self.client.get_indicator_observations(
                    indicator.provider_id,
                    [country.code for country in config.countries],
                    start_year=start_year,
                    end_year=date.today().year,
                )
                grouped: dict[str, list[dict[str, Any]]] = {
                    country.code: [] for country in config.countries
                }
                for record in records:
                    country_code = str(record.get("countryiso3code") or "").upper()
                    if country_code in grouped:
                        grouped[country_code].append(record)

                for country in config.countries:
                    with self.session_factory() as session:
                        stats = self.ingest_country_indicator(
                            session,
                            country,
                            indicator,
                            grouped[country.code],
                        )
                        session.commit()
                    succeeded += 1
                    total_inserted += stats.inserted
                    total_updated += stats.updated

            status = RunStatus.SUCCEEDED.value
            self.runs.finish(
                run_id,
                status=status,
                succeeded=succeeded,
                inserted=total_inserted,
                updated=total_updated,
            )
        except Exception as exc:
            logger.exception("World Bank ingestion run failed")
            status = RunStatus.FAILED.value
            self.runs.finish(
                run_id,
                status=status,
                succeeded=succeeded,
                inserted=total_inserted,
                updated=total_updated,
                error_message=str(exc),
            )
            raise

        return IngestionSummary(
            run_id=run_id,
            provider="WORLD_BANK",
            status=status,
            series_requested=series_requested,
            series_succeeded=succeeded,
            observations_inserted=total_inserted,
            observations_updated=total_updated,
        )

    def _request_start_year(
        self,
        countries: list[WorldBankCountryConfig],
        indicator: WorldBankIndicatorConfig,
    ) -> int:
        latest_years: list[int] = []
        with self.session_factory() as session:
            for country in countries:
                series_id = self.series_id(country.code, indicator.provider_id)
                latest = session.scalar(
                    select(func.max(Observation.observation_date)).where(
                        Observation.series_id == series_id
                    )
                )
                if latest is None:
                    return indicator.start_year
                latest_years.append(latest.year)
        earliest_latest = min(latest_years)
        return max(indicator.start_year, earliest_latest - self.lookback_years + 1)

    def ingest_country_indicator(
        self,
        session: Session,
        country: WorldBankCountryConfig,
        indicator: WorldBankIndicatorConfig,
        records: list[dict[str, Any]],
    ) -> SeriesIngestionStats:
        series_id = self.series_id(country.code, indicator.provider_id)
        series = session.get(EconomicSeries, series_id)
        if series is None:
            series = EconomicSeries(
                series_id=series_id,
                display_name=indicator.display_name,
                title=indicator.display_name,
                category=indicator.category,
                source="WORLD_BANK",
            )
            session.add(series)

        normalized_source = self._normalize_source_records(series_id, records)
        self._apply_metadata(series, country, indicator, normalized_source)
        session.flush()
        normalized = [
            {
                "observation_date": parse_observation_date(item["date"]),
                "value": parse_world_bank_value(item.get("value")),
            }
            for item in normalized_source
        ]
        return upsert_observations(session, series_id, normalized)

    @staticmethod
    def series_id(country_code: str, provider_id: str) -> str:
        return f"WB:{country_code.upper()}:{provider_id}"

    @staticmethod
    def _normalize_source_records(
        series_id: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for record in records:
            raw_year = record.get("date")
            if raw_year is None:
                continue
            year = int(raw_year)
            normalized.append({"date": f"{year:04d}-01-01", "value": record.get("value")})
        normalized.sort(key=lambda item: item["date"])
        validate_observations(series_id, normalized)
        return normalized

    @staticmethod
    def _apply_metadata(
        series: EconomicSeries,
        country: WorldBankCountryConfig,
        indicator: WorldBankIndicatorConfig,
        observations: list[dict[str, Any]],
    ) -> None:
        series.provider_series_id = indicator.provider_id
        series.indicator_code = indicator.code
        series.country_code = country.code
        series.country_name = country.name
        series.display_name = indicator.display_name
        series.title = f"{indicator.display_name} — {country.name}"
        series.category = indicator.category
        series.source = "WORLD_BANK"
        series.units = indicator.units
        series.frequency = "Annual"
        series.observation_start = date(indicator.start_year, 1, 1)
        if observations:
            series.observation_end = parse_observation_date(observations[-1]["date"])
        series.notes = f"World Bank indicator {indicator.provider_id}"
        series.description = indicator.description
        series.enabled = True
