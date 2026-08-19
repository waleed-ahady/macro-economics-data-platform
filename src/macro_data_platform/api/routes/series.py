import csv
import io
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from macro_data_platform.api.dependencies import SessionDependency
from macro_data_platform.schemas import (
    LatestObservationOut,
    ObservationListOut,
    ObservationOut,
    SeriesListOut,
    SeriesOut,
)
from macro_data_platform.services import catalog

router = APIRouter(prefix="/v1/series", tags=["series"])


@router.get("", response_model=SeriesListOut)
def list_series(
    session: SessionDependency,
    q: str | None = None,
    category: str | None = None,
    source: str | None = None,
    country: str | None = None,
    indicator: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SeriesListOut:
    total, items = catalog.list_series(
        session,
        query=q,
        category=category,
        source=source,
        country_code=country,
        indicator_code=indicator,
        limit=limit,
        offset=offset,
    )
    return SeriesListOut(total=total, items=[SeriesOut.model_validate(item) for item in items])


@router.get("/{series_id}", response_model=SeriesOut)
def series_metadata(series_id: str, session: SessionDependency) -> SeriesOut:
    item = catalog.get_series(session, series_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Series not found")
    return SeriesOut.model_validate(item)


@router.get("/{series_id}/latest", response_model=LatestObservationOut)
def latest_observation(series_id: str, session: SessionDependency) -> LatestObservationOut:
    series = catalog.get_series(session, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    observation = catalog.get_latest_observation(session, series_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="No observations found")
    return LatestObservationOut(
        series_id=series.series_id,
        observation_date=observation.observation_date,
        value=observation.value,
        units=series.units,
        retrieved_at=observation.retrieved_at,
    )


@router.get("/{series_id}/observations", response_model=ObservationListOut)
def observations(
    series_id: str,
    session: SessionDependency,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(default=5000, ge=1, le=50000),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> ObservationListOut:
    series = catalog.get_series(session, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    items = catalog.get_observations(
        session,
        series_id,
        start=start,
        end=end,
        limit=limit,
        ascending=order == "asc",
    )
    return ObservationListOut(
        series_id=series.series_id,
        units=series.units,
        frequency=series.frequency,
        count=len(items),
        observations=[ObservationOut.model_validate(item) for item in items],
    )


@router.get("/{series_id}/observations.csv", response_class=Response)
def observations_csv(
    series_id: str,
    session: SessionDependency,
    start: date | None = None,
    end: date | None = None,
) -> StreamingResponse:
    series = catalog.get_series(session, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    items = catalog.get_observations(session, series_id, start=start, end=end, limit=50000)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "series_id",
            "country_code",
            "indicator_code",
            "source",
            "date",
            "value",
            "units",
        ]
    )
    for item in items:
        writer.writerow(
            [
                series.series_id,
                series.country_code,
                series.indicator_code,
                series.source,
                item.observation_date,
                item.value,
                series.units,
            ]
        )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{series.series_id}.csv"'},
    )
