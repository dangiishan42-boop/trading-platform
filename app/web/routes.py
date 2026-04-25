from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from app.config.constants import ANGEL_SYMBOL_TO_TOKEN
from app.config.settings import get_settings
from app.services.strategies.strategy_registry import StrategyRegistry

settings = get_settings()
templates = Jinja2Templates(directory=str(settings.templates_dir))
router = APIRouter()

DETAIL_SECTIONS = {
    "overview",
    "fundamentals",
    "option-chain",
    "technical",
    "peers",
    "actions",
}


def render_market_watch_detail(request: Request, symbol: str, asset_type: str, section: str = "overview"):
    active_section = section.strip().lower()
    if active_section not in DETAIL_SECTIONS:
        raise HTTPException(status_code=404, detail="Detail section not found")

    normalized_symbol = symbol.strip().upper()
    exchange = "NSE"
    if asset_type == "index":
        exchange = "BSE" if normalized_symbol == "SENSEX" else "NSE"

    return templates.TemplateResponse(
        request=request,
        name="market_watch/detail.html",
        context={
            "request": request,
            "title": f"{settings.app_name} - {normalized_symbol} Detail",
            "angel_symbol_map": ANGEL_SYMBOL_TO_TOKEN,
            "symbol": normalized_symbol,
            "asset_type": asset_type,
            "exchange": exchange,
            "active_section": active_section,
        },
    )

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


@router.get("/market-watch/chart")
def market_watch_large_chart_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="market_watch/index.html",
        context={
            "request": request,
            "title": f"{settings.app_name} - Advanced Chart",
            "angel_symbol_map": ANGEL_SYMBOL_TO_TOKEN,
            "chart_only": True,
        },
    )


@router.get("/market-watch/stock/{symbol}")
def market_watch_stock_detail_page(request: Request, symbol: str):
    return render_market_watch_detail(request, symbol, "stock")


@router.get("/market-watch/stock/{symbol}/{section}")
def market_watch_stock_detail_section_page(request: Request, symbol: str, section: str):
    return render_market_watch_detail(request, symbol, "stock", section)


@router.get("/market-watch/index/{symbol}")
def market_watch_index_detail_page(request: Request, symbol: str):
    return render_market_watch_detail(request, symbol, "index")


@router.get("/market-watch/index/{symbol}/{section}")
def market_watch_index_detail_section_page(request: Request, symbol: str, section: str):
    return render_market_watch_detail(request, symbol, "index", section)


@router.get("/dashboard")
def dashboard_page(request: Request):
    strategies = StrategyRegistry().available()
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "request": request,
            "strategies": strategies,
            "title": f"{settings.app_name} - Backtest Dashboard",
            "page_mode": "dashboard",
            "page_heading": "Backtest Dashboard",
            "page_description": "Upload data, fetch Angel candles, configure and run backtests, then review charts, trades, history, and saved strategy configurations.",
        },
    )


@router.get("/research")
def research_page(request: Request):
    strategies = StrategyRegistry().available()
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "request": request,
            "strategies": strategies,
            "title": f"{settings.app_name} - Research & Optimization",
            "page_mode": "research",
            "page_heading": "Research & Optimization",
            "page_description": "Optimize strategy parameters, validate with walk-forward analysis, stress test with Monte Carlo, review regimes, and summarize strategy quality.",
        },
    )


@router.get("/portfolio")
def portfolio_page(request: Request):
    strategies = StrategyRegistry().available()
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "request": request,
            "strategies": strategies,
            "title": f"{settings.app_name} - Portfolio Dashboard",
            "page_mode": "portfolio",
            "page_heading": "Portfolio Dashboard",
            "page_description": "Run multi-symbol portfolio backtests, review portfolio metrics, allocation, equity curve, contribution, rebalancing, and per-symbol breakdowns.",
        },
    )


@router.get("/algo-trading")
def algo_trading_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="algo_trading/index.html",
        context={
            "request": request,
            "title": f"{settings.app_name} - Algo Trading",
            "angel_symbol_map": ANGEL_SYMBOL_TO_TOKEN,
        },
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
