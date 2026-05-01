from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI
from app.config.settings import get_settings
from app.core.logger import get_logger
from app.database.session import engine
from app.services.market_data.fno_live_data_service import get_fno_live_data_service
from sqlmodel import Session

logger = get_logger(__name__)

_stop_fno_refresh = threading.Event()


def _fno_refresh_loop(interval_seconds: int) -> None:
    service = get_fno_live_data_service()
    while not _stop_fno_refresh.wait(interval_seconds):
        try:
            with Session(engine) as session:
                service.refresh(session)
        except Exception as exc:
            logger.error(
                "F&O live quote background refresh failed",
                extra={"event_name": "fno_live_refresh_failed", "event_fields": {"error": str(exc)}},
            )

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
    if settings.enable_fno_live_refresh:
        _stop_fno_refresh.clear()
        thread = threading.Thread(
            target=_fno_refresh_loop,
            args=(settings.fno_live_refresh_interval_seconds,),
            name="fno-live-refresh",
            daemon=True,
        )
        thread.start()
        logger.info(
            "F&O live quote background refresh enabled",
            extra={"event_name": "fno_live_refresh_enabled", "event_fields": {"interval_seconds": settings.fno_live_refresh_interval_seconds}},
        )
    yield
    _stop_fno_refresh.set()
    logger.info("Application shutting down", extra={"event_name": "application_shutting_down", "event_fields": {}})
