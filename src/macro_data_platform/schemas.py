from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SeriesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    series_id: str
    provider_series_id: str | None
    indicator_code: str | None
    country_code: str | None
    country_name: str | None
    display_name: str
    title: str
    category: str
    source: str
    units: str | None
    frequency: str | None
    observation_start: date | None
    observation_end: date | None
    description: str | None
    enabled: bool


class SeriesListOut(BaseModel):
    total: int
    items: list[SeriesOut]


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    observation_date: date
    value: float | None
    retrieved_at: datetime


class ObservationListOut(BaseModel):
    series_id: str
    units: str | None
    frequency: str | None
    count: int
    observations: list[ObservationOut]


class LatestObservationOut(BaseModel):
    series_id: str
    observation_date: date
    value: float | None
    units: str | None
    retrieved_at: datetime


class AnalyticsPoint(BaseModel):
    date: date
    value: float | None


class AnalyticsOut(BaseModel):
    series_id: str
    transform: str
    source_frequency: str | None
    periods: int | None
    points: list[AnalyticsPoint]


class CompareSeries(BaseModel):
    series_id: str
    display_name: str
    country_code: str | None = None
    country_name: str | None = None
    units: str | None = None
    points: list[AnalyticsPoint]


class CompareOut(BaseModel):
    transform: str
    series: list[CompareSeries]


class CountryOut(BaseModel):
    country_code: str
    country_name: str
    series_count: int
    indicator_count: int


class CountryListOut(BaseModel):
    items: list[CountryOut]


class IndicatorOut(BaseModel):
    indicator_code: str
    display_name: str
    category: str
    units: str | None
    country_count: int
    sources: list[str]


class IndicatorListOut(BaseModel):
    items: list[IndicatorOut]


class CountryIndicatorOut(BaseModel):
    series: SeriesOut
    transform: str
    points: list[AnalyticsPoint]


class IngestionStatsOut(BaseModel):
    run_id: int
    provider: str
    status: str
    series_requested: int
    series_succeeded: int
    observations_inserted: int
    observations_updated: int


class HealthOut(BaseModel):
    status: str
    database: str
    countries: int = 0
    series: int = 0
    observations: int = 0
    latest_ingestion_status: str | None = None
    latest_ingestion_provider: str | None = None
    latest_ingestion_completed_at: datetime | None = None


class ErrorOut(BaseModel):
    detail: str = Field(examples=["Series not found"])
