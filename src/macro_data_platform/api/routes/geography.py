from datetime import date

from fastapi import APIRouter, HTTPException, Query

from macro_data_platform.api.dependencies import SessionDependency
from macro_data_platform.schemas import (
    AnalyticsPoint,
    CountryIndicatorOut,
    CountryListOut,
    CountryOut,
    IndicatorListOut,
    IndicatorOut,
    SeriesOut,
)
from macro_data_platform.services import catalog
from macro_data_platform.services.analytics import SUPPORTED_TRANSFORMS, transform_observations

router = APIRouter(prefix="/v1", tags=["countries and indicators"])


@router.get("/countries", response_model=CountryListOut)
def countries(session: SessionDependency) -> CountryListOut:
    return CountryListOut(
        items=[CountryOut.model_validate(item) for item in catalog.country_catalog(session)]
    )


@router.get("/indicators", response_model=IndicatorListOut)
def indicators(session: SessionDependency) -> IndicatorListOut:
    return IndicatorListOut(
        items=[IndicatorOut.model_validate(item) for item in catalog.indicator_catalog(session)]
    )


@router.get(
    "/countries/{country_code}/indicators/{indicator_code}",
    response_model=CountryIndicatorOut,
)
def country_indicator(
    country_code: str,
    indicator_code: str,
    session: SessionDependency,
    transform: str = Query(default="raw"),
    start: date | None = None,
    end: date | None = None,
) -> CountryIndicatorOut:
    if transform not in SUPPORTED_TRANSFORMS:
        raise HTTPException(status_code=422, detail="Unsupported transform")
    series = catalog.find_country_indicator_series(session, country_code, indicator_code)
    if series is None:
        raise HTTPException(status_code=404, detail="Country indicator not found")
    observations = catalog.get_observations(
        session,
        series.series_id,
        start=start,
        end=end,
        limit=50000,
    )
    points = transform_observations(
        observations,
        transform,
        frequency=series.frequency,
    )
    return CountryIndicatorOut(
        series=SeriesOut.model_validate(series),
        transform=transform,
        points=[AnalyticsPoint.model_validate(point) for point in points],
    )
