from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config.settings import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Application starting",
        extra={
            "event_name": "application_starting",
            "event_fields": {
                "env": settings.app_env,
                "debug": settings.debug,
                "database_url": settings.database_url,
            },
        },
    )
    yield
    logger.info("Application shutting down", extra={"event_name": "application_shutting_down", "event_fields": {}})
