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
    assert "Key Price Stats" in response.text
    assert "Technical Snapshot" in response.text
    assert "Peer Quick Compare" in response.text
    assert "Latest News / Corporate Actions" in response.text
    assert "Company Snapshot / Fundamentals" not in response.text
    assert '<div class="panel-title">Option Chain</div>' not in response.text
    assert '<section class="panel" id="technical-signals">' not in response.text
    assert '<section class="panel" id="peers">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_overview_page_loads_professional_summary():
    response = client.get("/market-watch/stock/RELIANCE/overview")

    assert response.status_code == 200
    assert "Key Price Stats" in response.text
    assert "Performance" in response.text
    assert "Technical Snapshot" in response.text
    assert "Company Snapshot" in response.text
    assert "Trading Actions" in response.text
    assert "Peer Quick Compare" in response.text
    assert "News data source not connected yet" in response.text


def test_market_watch_stock_fundamentals_page_loads_only_fundamentals():
    response = client.get("/market-watch/stock/RELIANCE/fundamentals")

    assert response.status_code == 200
    assert "Company Snapshot / Fundamentals" in response.text
    assert "Fundamental data source not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert '<div class="panel-title">Option Chain</div>' not in response.text
    assert '<section class="panel" id="technical-signals">' not in response.text
    assert '<section class="panel" id="peers">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_option_chain_page_loads_only_option_chain():
    response = client.get("/market-watch/stock/RELIANCE/option-chain")

    assert response.status_code == 200
    assert '<div class="panel-title">Option Chain</div>' in response.text
    assert "Option chain data source not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Company Snapshot / Fundamentals" not in response.text
    assert '<section class="panel" id="technical-signals">' not in response.text
    assert '<section class="panel" id="peers">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_technical_page_loads_only_technical():
    response = client.get("/market-watch/stock/RELIANCE/technical")

    assert response.status_code == 200
    assert '<div class="panel-title">Technical Signals</div>' in response.text
    assert "Derived Metrics" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Company Snapshot / Fundamentals" not in response.text
    assert '<div class="panel-title">Option Chain</div>' not in response.text
    assert '<section class="panel" id="peers">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_peers_page_loads_only_peers():
    response = client.get("/market-watch/stock/RELIANCE/peers")

    assert response.status_code == 200
    assert "Related Stocks / Peers" in response.text
    assert "Loading peers..." in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Company Snapshot / Fundamentals" not in response.text
    assert '<div class="panel-title">Option Chain</div>' not in response.text
    assert '<section class="panel" id="technical-signals">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_actions_page_loads_only_actions():
    response = client.get("/market-watch/stock/RELIANCE/actions")

    assert response.status_code == 200
    assert '<div class="panel-title">Action Hub</div>' in response.text
    assert "Alerts engine not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Company Snapshot / Fundamentals" not in response.text
    assert '<div class="panel-title">Option Chain</div>' not in response.text
    assert '<section class="panel" id="technical-signals">' not in response.text
    assert '<section class="panel" id="peers">' not in response.text


def test_market_watch_index_detail_page_loads():
    response = client.get("/market-watch/index/NIFTY50")

    assert response.status_code == 200
    assert "NIFTY50" in response.text
    assert "Advanced Candlestick Chart" in response.text
    assert "Key Price Stats" in response.text
    assert "Company Snapshot / Fundamentals" not in response.text


def test_market_watch_index_overview_page_loads_professional_summary():
    response = client.get("/market-watch/index/NIFTY50/overview")

    assert response.status_code == 200
    assert "NIFTY50" in response.text
    assert "Key Price Stats" in response.text
    assert "Technical Snapshot" in response.text
    assert "Company Snapshot" in response.text
    assert "Latest News / Corporate Actions" in response.text


def test_market_watch_index_detail_sub_pages_load():
    for section, expected in [
        ("overview", "Advanced Candlestick Chart"),
        ("fundamentals", "Company Snapshot / Fundamentals"),
        ("option-chain", '<div class="panel-title">Option Chain</div>'),
        ("technical", '<div class="panel-title">Technical Signals</div>'),
        ("peers", "Related Stocks / Peers"),
        ("actions", '<div class="panel-title">Action Hub</div>'),
    ]:
        response = client.get(f"/market-watch/index/NIFTY50/{section}")

        assert response.status_code == 200
        assert expected in response.text


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
