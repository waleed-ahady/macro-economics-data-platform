import math
from datetime import date
from typing import Any


class DataValidationError(ValueError):
    """Raised when source observations do not satisfy ingestion invariants."""


def parse_observation_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def parse_numeric_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def validate_observations(series_id: str, observations: list[dict[str, Any]]) -> None:
    """Validate dates, duplicate keys, sort order, and finite values before persistence."""
    seen_dates: set[date] = set()
    previous_date: date | None = None

    for index, item in enumerate(observations):
        try:
            observation_date = parse_observation_date(item.get("date"))
        except (TypeError, ValueError) as exc:
            raise DataValidationError(f"{series_id}: invalid date at source row {index}") from exc

        if observation_date is None:
            raise DataValidationError(f"{series_id}: missing date at source row {index}")
        if observation_date in seen_dates:
            raise DataValidationError(f"{series_id}: duplicate source date {observation_date}")
        if previous_date is not None and observation_date < previous_date:
            raise DataValidationError(f"{series_id}: source observations are not ascending")

        try:
            value = parse_numeric_value(item.get("value"))
        except (TypeError, ValueError) as exc:
            raise DataValidationError(f"{series_id}: invalid value at {observation_date}") from exc
        if value is not None and not math.isfinite(value):
            raise DataValidationError(f"{series_id}: non-finite value at {observation_date}")

        seen_dates.add(observation_date)
        previous_date = observation_date
