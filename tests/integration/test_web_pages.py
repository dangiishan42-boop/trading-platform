from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_market_watch_page_loads():
    response = client.get("/market-watch")

    assert response.status_code == 200
    assert "Live Market Watch" in response.text
    assert "Advanced Chart" in response.text


def test_screener_page_loads():
    response = client.get("/screener")

    assert response.status_code == 200
    assert "Enterprise grade stock screener" in response.text
    assert "Filter Builder" in response.text
    assert "Scan Summary" in response.text
    assert "Market Cap Breakdown" in response.text


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
    assert "Valuation Snapshot" in response.text
    assert "Profitability Ratios" in response.text
    assert "Growth Metrics" in response.text
    assert "Balance Sheet Strength" in response.text
    assert "Quarterly Results" in response.text
    assert "Annual P&amp;L" in response.text
    assert "Cash Flow" in response.text
    assert "Shareholding Pattern" in response.text
    assert "Peer Valuation Compare" in response.text
    assert "Research Notes / Warnings" in response.text
    assert "Fundamental data source not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert '<div class="panel-title">Option Chain</div>' not in response.text
    assert '<section class="panel" id="technical-signals">' not in response.text
    assert '<section class="panel" id="peers">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_option_chain_page_loads_only_option_chain():
    response = client.get("/market-watch/stock/RELIANCE/option-chain")

    assert response.status_code == 200
    assert "Option Chain Table" in response.text
    assert "Summary Cards" in response.text
    assert "OI Heatmap" in response.text
    assert "Buildup Analysis" in response.text
    assert "Option Strategy Quick Builder" in response.text
    assert "Historical Option Chain" in response.text
    assert "Option chain data source not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Valuation Snapshot" not in response.text
    assert '<section class="panel" id="technical-signals">' not in response.text
    assert '<section class="panel" id="peers">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_technical_page_loads_only_technical():
    response = client.get("/market-watch/stock/RELIANCE/technical")

    assert response.status_code == 200
    assert "Overall Signal Score" in response.text
    assert "Trend Signals" in response.text
    assert "Momentum Signals" in response.text
    assert "Volume Signals" in response.text
    assert "Volatility / Risk Signals" in response.text
    assert "Support &amp; Resistance" in response.text
    assert "Multi-Timeframe Signal Summary" in response.text
    assert "Signal History" in response.text
    assert "Technical Summary / Interpretation" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Valuation Snapshot" not in response.text
    assert "Option Chain Table" not in response.text
    assert '<section class="panel" id="peers">' not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_stock_peers_page_loads_only_peers():
    response = client.get("/market-watch/stock/RELIANCE/peers")

    assert response.status_code == 200
    assert "Peer Quote Table" in response.text
    assert "Peer Group Summary" in response.text
    assert "Peer Performance Cards" in response.text
    assert "Relative Performance Chart" in response.text
    assert "Peer Valuation Compare" in response.text
    assert "Sector Strength / Rotation" in response.text
    assert "Loading peers..." in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Valuation Snapshot" not in response.text
    assert "Option Chain Table" not in response.text
    assert "Overall Signal Score" not in response.text
    assert '<section class="panel" id="action-hub">' not in response.text


def test_market_watch_hdfcbank_peers_page_loads():
    response = client.get("/market-watch/stock/HDFCBANK/peers")

    assert response.status_code == 200
    assert "Peer Quote Table" in response.text
    assert "Peer Group Summary" in response.text
    assert "Sector Strength / Rotation" in response.text


def test_market_watch_stock_actions_page_loads_only_actions():
    response = client.get("/market-watch/stock/RELIANCE/actions")

    assert response.status_code == 200
    assert "Quick Action Cards" in response.text
    assert "Backtest Workflow" in response.text
    assert "Research Workflow" in response.text
    assert "Algo Workflow" in response.text
    assert "Portfolio Workflow" in response.text
    assert "Alert Workflow" in response.text
    assert "Export Snapshot" in response.text
    assert "Alerts engine not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Valuation Snapshot" not in response.text
    assert "Option Chain Table" not in response.text
    assert "Overall Signal Score" not in response.text
    assert "Peer Quote Table" not in response.text


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


def test_market_watch_index_fundamentals_page_loads_professional_placeholders():
    response = client.get("/market-watch/index/NIFTY50/fundamentals")

    assert response.status_code == 200
    assert "Valuation Snapshot" in response.text
    assert "Profitability Ratios" in response.text
    assert "Quarterly Results" in response.text
    assert "Peer Valuation Compare" in response.text
    assert "Research Notes / Warnings" in response.text
    assert "Fundamental data source not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert '<div class="panel-title">Option Chain</div>' not in response.text


def test_market_watch_index_option_chain_page_loads_professional_terminal():
    response = client.get("/market-watch/index/NIFTY50/option-chain")

    assert response.status_code == 200
    assert "Option Chain Table" in response.text
    assert "Summary Cards" in response.text
    assert "OI Heatmap" in response.text
    assert "Buildup Analysis" in response.text
    assert "Historical option-chain data source not connected yet" in response.text
    assert "Option chain data source not connected yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Valuation Snapshot" not in response.text


def test_market_watch_index_technical_page_loads_professional_dashboard():
    response = client.get("/market-watch/index/NIFTY50/technical")

    assert response.status_code == 200
    assert "Overall Signal Score" in response.text
    assert "Trend Signals" in response.text
    assert "Momentum Signals" in response.text
    assert "Support &amp; Resistance" in response.text
    assert "Multi-Timeframe Signal Summary" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Option Chain Table" not in response.text
    assert "Valuation Snapshot" not in response.text


def test_market_watch_index_peers_page_loads_professional_comparison():
    response = client.get("/market-watch/index/NIFTY50/peers")

    assert response.status_code == 200
    assert "Peer Quote Table" in response.text
    assert "Peer Group Summary" in response.text
    assert "Peer Valuation Compare" in response.text
    assert "Peer mapping not available yet" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Option Chain Table" not in response.text
    assert "Overall Signal Score" not in response.text


def test_market_watch_index_actions_page_loads_workflow_hub():
    response = client.get("/market-watch/index/NIFTY50/actions")

    assert response.status_code == 200
    assert "Quick Action Cards" in response.text
    assert "Backtest Workflow" in response.text
    assert "Research Workflow" in response.text
    assert "Algo Workflow" in response.text
    assert "Portfolio Workflow" in response.text
    assert "Alert Workflow" in response.text
    assert '<section class="panel" id="chart">' not in response.text
    assert "Valuation Snapshot" not in response.text
    assert "Option Chain Table" not in response.text
    assert "Overall Signal Score" not in response.text
    assert "Peer Quote Table" not in response.text


def test_market_watch_index_detail_sub_pages_load():
    for section, expected in [
        ("overview", "Advanced Candlestick Chart"),
        ("fundamentals", "Valuation Snapshot"),
        ("option-chain", "Option Chain Table"),
        ("technical", "Overall Signal Score"),
        ("peers", "Peer Quote Table"),
        ("actions", "Quick Action Cards"),
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
