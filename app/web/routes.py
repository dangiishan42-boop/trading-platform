from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.config.constants import ANGEL_SYMBOL_TO_TOKEN
from app.config.settings import get_settings
from app.services.strategies.strategy_registry import StrategyRegistry

settings = get_settings()
templates = Jinja2Templates(directory=str(settings.templates_dir))
router = APIRouter()

@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="market_watch/index.html",
        context={
            "request": request,
            "title": f"{settings.app_name} - Live Market Watch",
            "angel_symbol_map": ANGEL_SYMBOL_TO_TOKEN,
        },
    )


@router.get("/market-watch")
def market_watch_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="market_watch/index.html",
        context={
            "request": request,
            "title": f"{settings.app_name} - Live Market Watch",
            "angel_symbol_map": ANGEL_SYMBOL_TO_TOKEN,
        },
    )


@router.get("/dashboard")
def dashboard_page(request: Request):
    strategies = StrategyRegistry().available()
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={"request": request, "strategies": strategies, "title": settings.app_name},
    )


@router.get("/historical-data")
def historical_data_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="historical_data/index.html",
        context={
            "request": request,
            "title": f"{settings.app_name} - Historical Data",
            "angel_symbol_map": ANGEL_SYMBOL_TO_TOKEN,
        },
    )
