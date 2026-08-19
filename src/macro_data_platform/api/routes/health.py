from fastapi import APIRouter
from sqlalchemy import func, select, text

from macro_data_platform.api.dependencies import SessionDependency
from macro_data_platform.models import EconomicSeries, IngestionRun, Observation
from macro_data_platform.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(session: SessionDependency) -> HealthOut:
    session.execute(text("SELECT 1"))
    latest = session.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))
    countries = (
        session.scalar(
            select(func.count(func.distinct(EconomicSeries.country_code))).where(
                EconomicSeries.country_code.is_not(None), EconomicSeries.enabled.is_(True)
            )
        )
        or 0
    )
    series = (
        session.scalar(
            select(func.count()).select_from(EconomicSeries).where(EconomicSeries.enabled.is_(True))
        )
        or 0
    )
    observations = session.scalar(select(func.count()).select_from(Observation)) or 0
    return HealthOut(
        status="ok",
        database="ok",
        countries=countries,
        series=series,
        observations=observations,
        latest_ingestion_status=latest.status if latest else None,
        latest_ingestion_provider=latest.provider if latest else None,
        latest_ingestion_completed_at=latest.completed_at if latest else None,
    )
