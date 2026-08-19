from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from macro_data_platform.api.routes import analytics, geography, health, series
from macro_data_platform.config import get_settings
from macro_data_platform.logging import configure_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        description=(
            "REST API for standardized cross-country macroeconomic indicators "
            "sourced from the World Bank Indicators API."
        ),
        lifespan=lifespan,
    )
    application.include_router(health.router)
    application.include_router(geography.router)
    application.include_router(series.router)
    application.include_router(analytics.router)
    return application


app = create_app()
