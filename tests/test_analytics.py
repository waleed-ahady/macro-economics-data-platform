from datetime import date

import pytest

from macro_data_platform.models import Observation
from macro_data_platform.services.analytics import default_year_periods, transform_observations


def observations(values: list[float]) -> list[Observation]:
    return [
        Observation(series_id="TEST", observation_date=date(2020 + index, 1, 1), value=value)
        for index, value in enumerate(values)
    ]


def test_year_over_year_transformation() -> None:
    points = transform_observations(
        observations([100.0, 110.0, 121.0]),
        "yoy",
        frequency="Annual",
    )
    assert points[0]["value"] is None
    assert points[1]["value"] == pytest.approx(10.0)
    assert points[2]["value"] == pytest.approx(10.0)


def test_default_periods_by_frequency() -> None:
    assert default_year_periods("Monthly") == 12
    assert default_year_periods("Quarterly") == 4
    assert default_year_periods("Weekly") == 52
