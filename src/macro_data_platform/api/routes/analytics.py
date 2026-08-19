from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from macro_data_platform.api.dependencies import SessionDependency
from macro_data_platform.schemas import AnalyticsOut, AnalyticsPoint, CompareOut, CompareSeries
from macro_data_platform.services import catalog
from macro_data_platform.services.analytics import SUPPORTED_TRANSFORMS, transform_observations

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/series/{series_id}", response_model=AnalyticsOut)
def analyze_series(
    series_id: str,
    session: SessionDependency,
    transform: str = Query(default="raw"),
    start: date | None = None,
    end: date | None = None,
    periods: int | None = Query(default=None, ge=1, le=3650),
    zscore_window: int = Query(default=36, ge=3, le=1000),
) -> AnalyticsOut:
    if transform not in SUPPORTED_TRANSFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"transform must be one of {sorted(SUPPORTED_TRANSFORMS)}",
        )
    series = catalog.get_series(session, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    items = catalog.get_observations(session, series_id, start=start, end=end, limit=50000)
    points = transform_observations(
        items,
        transform,
        frequency=series.frequency,
        periods=periods,
        zscore_window=zscore_window,
    )
    return AnalyticsOut(
        series_id=series.series_id,
        transform=transform,
        source_frequency=series.frequency,
        periods=periods,
        points=[AnalyticsPoint.model_validate(point) for point in points],
    )


@router.get("/compare", response_model=CompareOut)
def compare_series(
    session: SessionDependency,
    series_ids: Annotated[list[str], Query(min_length=1, max_length=8)],
    transform: str = Query(default="zscore"),
    start: date | None = None,
    end: date | None = None,
    periods: int | None = Query(default=None, ge=1, le=3650),
) -> CompareOut:
    if transform not in SUPPORTED_TRANSFORMS:
        raise HTTPException(status_code=422, detail="Unsupported transform")
    output: list[CompareSeries] = []
    for series_id in series_ids:
        series = catalog.get_series(session, series_id)
        if series is None:
            raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")
        items = catalog.get_observations(session, series_id, start=start, end=end, limit=50000)
        points = transform_observations(
            items,
            transform,
            frequency=series.frequency,
            periods=periods,
        )
        output.append(
            CompareSeries(
                series_id=series.series_id,
                display_name=series.display_name,
                country_code=series.country_code,
                country_name=series.country_name,
                units=series.units,
                points=[AnalyticsPoint.model_validate(point) for point in points],
            )
        )
    return CompareOut(transform=transform, series=output)


@router.get("/compare-countries", response_model=CompareOut)
def compare_countries(
    session: SessionDependency,
    indicator: str,
    countries: Annotated[list[str], Query(min_length=1, max_length=50)],
    transform: str = Query(default="raw"),
    start: date | None = None,
    end: date | None = None,
) -> CompareOut:
    if transform not in SUPPORTED_TRANSFORMS:
        raise HTTPException(status_code=422, detail="Unsupported transform")

    output: list[CompareSeries] = []
    for country_code in countries:
        series = catalog.find_country_indicator_series(session, country_code, indicator)
        if series is None:
            raise HTTPException(
                status_code=404,
                detail=f"Indicator {indicator!r} is not available for {country_code.upper()}",
            )
        items = catalog.get_observations(
            session,
            series.series_id,
            start=start,
            end=end,
            limit=50000,
        )
        points = transform_observations(items, transform, frequency=series.frequency)
        output.append(
            CompareSeries(
                series_id=series.series_id,
                display_name=series.display_name,
                country_code=series.country_code,
                country_name=series.country_name,
                units=series.units,
                points=[AnalyticsPoint.model_validate(point) for point in points],
            )
        )
    return CompareOut(transform=transform, series=output)
