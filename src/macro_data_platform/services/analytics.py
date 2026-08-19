from collections.abc import Sequence

import pandas as pd

from macro_data_platform.models import Observation

SUPPORTED_TRANSFORMS = {"raw", "yoy", "pct_change", "difference", "zscore"}


def default_year_periods(frequency: str | None) -> int:
    normalized = (frequency or "").lower()
    if "quarter" in normalized:
        return 4
    if "week" in normalized:
        return 52
    if "day" in normalized:
        return 365
    if "annual" in normalized or "year" in normalized:
        return 1
    return 12


def transform_observations(
    observations: Sequence[Observation],
    transform: str,
    *,
    frequency: str | None = None,
    periods: int | None = None,
    zscore_window: int = 36,
) -> list[dict[str, object]]:
    if transform not in SUPPORTED_TRANSFORMS:
        raise ValueError(f"Unsupported transform: {transform}")
    frame = pd.DataFrame(
        {
            "date": [item.observation_date for item in observations],
            "value": [item.value for item in observations],
        }
    )
    if frame.empty:
        return []
    frame = frame.sort_values("date").drop_duplicates("date", keep="last")
    values = pd.to_numeric(frame["value"], errors="coerce")

    if transform == "raw":
        transformed = values
    elif transform == "yoy":
        effective_periods = periods or default_year_periods(frequency)
        transformed = values.pct_change(periods=effective_periods, fill_method=None) * 100
    elif transform == "pct_change":
        transformed = values.pct_change(periods=periods or 1, fill_method=None) * 100
    elif transform == "difference":
        transformed = values.diff(periods=periods or 1)
    else:
        minimum_periods = max(3, min(zscore_window, 12))
        rolling_mean = values.rolling(zscore_window, min_periods=minimum_periods).mean()
        rolling_std = values.rolling(zscore_window, min_periods=minimum_periods).std(ddof=0)
        transformed = (values - rolling_mean) / rolling_std.replace(0, pd.NA)

    output: list[dict[str, object]] = []
    for item_date, value in zip(frame["date"], transformed, strict=True):
        clean_value = None if pd.isna(value) else round(float(value), 12)
        output.append({"date": item_date, "value": clean_value})
    return output
