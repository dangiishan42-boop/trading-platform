from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_algo_capabilities_returns_rule_options():
    response = client.get("/api/v1/algo/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert "Price" in payload["condition_sources"]
    assert "crosses above" in payload["operators"]
    assert payload["live_execution_enabled"] is False


def test_algo_simulate_returns_signal_and_trade_summary():
    response = client.post(
        "/api/v1/algo/simulate",
        json={
            "source": "sample",
            "symbol": "DEMO",
            "exchange": "NSE",
            "timeframe": "1D",
            "initial_capital": 100000,
            "position_size": 25000,
            "stop_loss_pct": 2,
            "target_pct": 4,
            "max_trades_per_day": 5,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "conditions": [
                {"signal_type": "buy", "source": "Price", "operator": ">", "value": 100, "connector": "AND"},
                {"signal_type": "sell", "source": "RSI", "operator": ">", "value": 70, "connector": "OR"},
                {"signal_type": "exit", "source": "RSI", "operator": "<", "value": 45, "connector": "OR"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["signal_count"] >= payload["buy_signal_count"]
    assert "estimated_net_profit" in payload
    assert "win_rate" in payload
    assert "max_drawdown" in payload
    assert "metrics" in payload
    assert isinstance(payload["trades"], list)
