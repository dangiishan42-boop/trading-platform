from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_market_watch_page_loads():
    response = client.get("/market-watch")

    assert response.status_code == 200
    assert "Live Market Watch" in response.text
    assert "Advanced Chart" in response.text


def test_market_watch_stock_detail_page_loads():
    response = client.get("/market-watch/stock/RELIANCE")

    assert response.status_code == 200
    assert "RELIANCE" in response.text
    assert "Advanced Candlestick Chart" in response.text
    assert "Financial data source not connected yet" in response.text


def test_market_watch_index_detail_page_loads():
    response = client.get("/market-watch/index/NIFTY50")

    assert response.status_code == 200
    assert "NIFTY50" in response.text
    assert "Advanced Candlestick Chart" in response.text
    assert "Financial data source not connected yet" in response.text


def test_backtest_dashboard_page_loads_focused_layout():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Backtest Dashboard" in response.text
    assert "Upload & Datasets" in response.text
    assert "Backtest Configuration" in response.text
    assert "Latest Backtest Results" in response.text
    assert "Recent Backtest History" in response.text


def test_research_page_loads_focused_layout():
    response = client.get("/research")

    assert response.status_code == 200
    assert "Research &amp; Optimization" in response.text
    assert "Optimization Results" in response.text
    assert "Monte Carlo" in response.text
    assert "Market Regime Analysis" in response.text
    assert "Strategy Recommendation" in response.text
    assert "Strategy Scorecard / Tear Sheet" in response.text


def test_portfolio_page_loads_focused_layout():
    response = client.get("/portfolio")

    assert response.status_code == 200
    assert "Portfolio Dashboard" in response.text
    assert "Portfolio Backtest" in response.text
    assert "Run Portfolio Backtest" in response.text
    assert "Per-Symbol Breakdown" in response.text


def test_algo_trading_page_loads():
    response = client.get("/algo-trading")

    assert response.status_code == 200
    assert "Algo Trading" in response.text
    assert "Market Data / Dataset" in response.text
    assert "Fetch Angel Data" in response.text
    assert "Fetched Dataset" in response.text
    assert "Algo Rule Builder" in response.text
    assert "Risk Controls" in response.text
    assert "Simulation Settings" in response.text
