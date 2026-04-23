from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.config.settings import get_settings
from app.services.strategies.strategy_registry import StrategyRegistry

settings = get_settings()
templates = Jinja2Templates(directory=str(settings.templates_dir))
router = APIRouter()

@router.get("/")
def home(request: Request):
    strategies = StrategyRegistry().available()
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={"request": request, "strategies": strategies, "title": settings.app_name},
    )
