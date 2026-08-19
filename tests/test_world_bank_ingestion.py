from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from macro_data_platform.models import EconomicSeries, Observation, ObservationRevision
from macro_data_platform.services.ingestion import (
    WorldBankConfig,
    WorldBankCountryConfig,
    WorldBankIndicatorConfig,
    WorldBankIngestionService,
)


class FakeWorldBankClient:
    value = 2.5

    def get_indicator_observations(
        self,
        indicator_id: str,
        country_codes: list[str],
        *,
        start_year: int,
        end_year: int,
    ) -> list[dict[str, Any]]:
        return [
            {
                "countryiso3code": country_code,
                "date": "2024",
                "value": self.value,
            }
            for country_code in country_codes
        ]


def test_world_bank_ingestion_creates_country_series_and_tracks_revisions(
    session_factory: sessionmaker[Session],
) -> None:
    config = WorldBankConfig(
        countries=[
            WorldBankCountryConfig("USA", "United States"),
            WorldBankCountryConfig("DEU", "Germany"),
        ],
        indicators=[
            WorldBankIndicatorConfig(
                code="inflation",
                provider_id="FP.CPI.TOTL.ZG",
                display_name="Consumer Price Inflation",
                category="prices",
                units="Percent",
                start_year=2020,
            )
        ],
    )
    client = FakeWorldBankClient()
    service = WorldBankIngestionService(session_factory, client)  # type: ignore[arg-type]

    first = service.run(config)
    second = service.run(config)
    assert first.observations_inserted == 2
    assert second.observations_inserted == 0

    client.value = 2.7
    third = service.run(config)
    assert third.observations_updated == 2

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(EconomicSeries)) == 2
        assert session.scalar(select(func.count()).select_from(Observation)) == 2
        assert session.scalar(select(func.count()).select_from(ObservationRevision)) == 2
        germany = session.get(EconomicSeries, "WB:DEU:FP.CPI.TOTL.ZG")
        assert germany is not None
        assert germany.country_name == "Germany"
        assert germany.indicator_code == "inflation"
