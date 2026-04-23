from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_backtest_run_returns_equity_and_drawdown_charts():
    response = client.post(
        "/api/v1/backtest/run",
        json={
            "source": "sample",
            "symbol": "DEMO",
            "timeframe": "1D",
            "strategy_name": "ema_crossover",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "stop_loss_pct": 2.0,
            "take_profit_pct": 4.0,
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
    assert isinstance(payload["trades"], list)
    assert isinstance(payload["equity_curve"], list)
    assert payload["commission_pct"] == 0.1
    assert payload["slippage_pct"] == 0.05
    assert payload["stop_loss_pct"] == 2.0
    assert payload["take_profit_pct"] == 4.0
    assert payload["position_sizing_mode"] == "fixed_capital"
    assert payload["capital_per_trade"] == 25000
    assert payload["fixed_quantity"] is None
    assert payload["equity_pct_per_trade"] is None
    assert "metrics" in payload
    assert "max_drawdown_pct" in payload["metrics"]
    assert isinstance(payload["metrics"]["max_drawdown_pct"], float)
    assert "total_brokerage" in payload["metrics"]
    assert "total_slippage" in payload["metrics"]
    assert "total_costs" in payload["metrics"]
    if payload["trades"]:
        latest_trade = payload["trades"][0]
        assert "exit_reason" in latest_trade
        assert latest_trade["position_sizing_mode"] == "fixed_capital"
        assert "capital_used" in latest_trade
    assert payload["chart_html"]
    assert payload["drawdown_chart_html"]
    assert "Plotly.newPlot" in payload["chart_html"]
    assert "Plotly.newPlot" in payload["drawdown_chart_html"]

    history_response = client.get("/api/v1/backtest/history?limit=10")

    assert history_response.status_code == 200

    history_payload = history_response.json()

    assert isinstance(history_payload, list)
    assert len(history_payload) <= 10
    assert history_payload

    latest_entry = history_payload[0]

    assert latest_entry["strategy_name"] == "ema_crossover"
    assert latest_entry["symbol"] == "DEMO"
    assert latest_entry["timeframe"] == "1D"
    assert latest_entry["initial_capital"] == 100000
    assert latest_entry["commission_pct"] == 0.1
    assert latest_entry["slippage_pct"] == 0.05
    assert "total_return_pct" in latest_entry
    assert "win_rate_pct" in latest_entry
    assert "max_drawdown_pct" in latest_entry
    assert "created_at" in latest_entry


def test_backtest_run_rejects_invalid_symbol_input():
    response = client.post(
        "/api/v1/backtest/run",
        json={
            "source": "sample",
            "symbol": "BAD SYMBOL!",
            "timeframe": "1D",
            "strategy_name": "ema_crossover",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "parameters": {
                "fast_period": 20,
                "slow_period": 50,
            },
        },
    )

    assert response.status_code == 422
