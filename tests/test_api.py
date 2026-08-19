from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from macro_data_platform.models import EconomicSeries, Observation


def seed(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add_all(
            [
                EconomicSeries(
                    series_id="WB:USA:TEST",
                    provider_series_id="TEST",
                    indicator_code="inflation",
                    country_code="USA",
                    country_name="United States",
                    display_name="Inflation",
                    title="Inflation — United States",
                    category="prices",
                    source="WORLD_BANK",
                    units="Percent",
                    frequency="Annual",
                ),
                EconomicSeries(
                    series_id="WB:DEU:TEST",
                    provider_series_id="TEST",
                    indicator_code="inflation",
                    country_code="DEU",
                    country_name="Germany",
                    display_name="Inflation",
                    title="Inflation — Germany",
                    category="prices",
                    source="WORLD_BANK",
                    units="Percent",
                    frequency="Annual",
                ),
            ]
        )
        session.add_all(
            [
                Observation(series_id="WB:USA:TEST", observation_date=date(2023, 1, 1), value=4.0),
                Observation(series_id="WB:USA:TEST", observation_date=date(2024, 1, 1), value=3.0),
                Observation(series_id="WB:DEU:TEST", observation_date=date(2023, 1, 1), value=5.0),
                Observation(series_id="WB:DEU:TEST", observation_date=date(2024, 1, 1), value=2.5),
            ]
        )
        session.commit()


def test_catalog_country_and_comparison_endpoints(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    seed(session_factory)

    catalog_response = api_client.get("/v1/series", params={"country": "DEU"})
    assert catalog_response.status_code == 200
    assert catalog_response.json()["total"] == 1

    countries_response = api_client.get("/v1/countries")
    assert countries_response.status_code == 200
    assert len(countries_response.json()["items"]) == 2

    indicators_response = api_client.get("/v1/indicators")
    assert indicators_response.status_code == 200
    assert indicators_response.json()["items"][0]["country_count"] == 2

    country_indicator = api_client.get("/v1/countries/DEU/indicators/inflation")
    assert country_indicator.status_code == 200
    assert country_indicator.json()["series"]["country_name"] == "Germany"

    comparison = api_client.get(
        "/v1/analytics/compare-countries",
        params=[
            ("indicator", "inflation"),
            ("countries", "USA"),
            ("countries", "DEU"),
        ],
    )
    assert comparison.status_code == 200
    assert len(comparison.json()["series"]) == 2


def test_unknown_series_returns_404(api_client: TestClient) -> None:
    response = api_client.get("/v1/series/UNKNOWN")
    assert response.status_code == 404


def test_compare_countries_accepts_full_dashboard_selection(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """The dashboard may compare all configured economies in one request."""
    seed(session_factory)
    response = api_client.get(
        "/v1/analytics/compare-countries",
        params=[
            ("indicator", "inflation"),
            *[("countries", "USA") for _ in range(14)],
        ],
    )
    assert response.status_code == 200
    assert len(response.json()["series"]) == 14
