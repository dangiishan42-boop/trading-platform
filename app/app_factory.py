from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config.settings import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import register_middlewares
from app.database.init_db import initialize_database
from app.lifespan import lifespan
from app.web.routes import router as web_router


def create_app() -> FastAPI:
    settings = get_settings()
    settings.static_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    register_middlewares(app)
    register_exception_handlers(app)
    app.include_router(web_router)
    app.include_router(api_router, prefix="/api")
    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
    initialize_database()
    return app
