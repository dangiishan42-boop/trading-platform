from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_portfolio_backtest_combines_symbol_results():
    response = client.post(
        "/api/v1/portfolio/backtest",
        json={
            "datasets": [
                {
                    "source": "sample",
                    "symbol": "RELIANCE",
                    "timeframe": "1D",
                    "allocation_pct": 50,
                },
                {
                    "source": "sample",
                    "symbol": "TCS",
                    "timeframe": "1D",
                    "allocation_pct": 50,
                },
            ],
            "strategy_name": "ema_crossover",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "position_sizing_mode": "fixed_capital",
            "capital_per_trade": 25000,
            "parameters": {
                "fast_period": 20,
                "slow_period": 50,
            },
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["strategy_name"] == "ema_crossover"
    assert payload["rebalancing_mode"] == "none"
    assert payload["initial_capital"] == 100000
    assert "metrics" in payload
    assert "total_return_pct" in payload["metrics"]
    assert "net_profit" in payload["metrics"]
    assert "max_drawdown_pct" in payload["metrics"]
    assert "total_trades" in payload["metrics"]
    assert isinstance(payload["equity_curve"], list)
    assert len(payload["symbol_results"]) == 2

    total_symbol_trades = sum(
        symbol_result["metrics"]["total_trades"]
        for symbol_result in payload["symbol_results"]
    )
    assert payload["metrics"]["total_trades"] == total_symbol_trades
    assert payload["symbol_results"][0]["allocated_capital"] == 50000
    assert payload["symbol_results"][1]["allocated_capital"] == 50000


def test_portfolio_backtest_accepts_monthly_rebalancing_mode():
    response = client.post(
        "/api/v1/portfolio/backtest",
        json={
            "datasets": [
                {
                    "source": "sample",
                    "symbol": "RELIANCE",
                    "timeframe": "1D",
                    "allocation_pct": 50,
                },
                {
                    "source": "sample",
                    "symbol": "TCS",
                    "timeframe": "1D",
                    "allocation_pct": 50,
                },
            ],
            "strategy_name": "ema_crossover",
            "rebalancing_mode": "monthly",
            "position_sizing_mode": "fixed_capital",
            "capital_per_trade": 25000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rebalancing_mode"] == "monthly"
    assert isinstance(payload["equity_curve"], list)


def test_portfolio_backtest_rejects_allocations_that_do_not_total_100():
    response = client.post(
        "/api/v1/portfolio/backtest",
        json={
            "datasets": [
                {
                    "source": "sample",
                    "symbol": "RELIANCE",
                    "timeframe": "1D",
                    "allocation_pct": 40,
                },
                {
                    "source": "sample",
                    "symbol": "TCS",
                    "timeframe": "1D",
                    "allocation_pct": 40,
                },
            ],
            "strategy_name": "ema_crossover",
        },
    )

    assert response.status_code == 422
