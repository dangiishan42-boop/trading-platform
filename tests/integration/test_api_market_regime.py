from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_market_regime_run_returns_regime_breakdown():
    response = client.post(
        "/api/v1/market-regime/run",
        json={
            "initial_capital": 100000,
            "slope_threshold_pct": 0.1,
            "market_data": [
                {"timestamp": "2025-01-01", "close": 100},
                {"timestamp": "2025-01-02", "close": 101},
                {"timestamp": "2025-01-03", "close": 102},
                {"timestamp": "2025-01-04", "close": 101},
                {"timestamp": "2025-01-05", "close": 99},
                {"timestamp": "2025-01-06", "close": 98},
                {"timestamp": "2025-01-07", "close": 98.2},
                {"timestamp": "2025-01-08", "close": 98.1},
            ],
            "trades": [
                {"exit_time": "2025-01-03", "pnl": 1000},
                {"exit_time": "2025-01-06", "pnl": -600},
                {"exit_time": "2025-01-08", "pnl": 200},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert "moving average slope" in payload["method"]
    assert payload["best_regime"] in {"Bull trend", "Bear trend", "Sideways"}
    assert payload["worst_regime"] in {"Bull trend", "Bear trend", "Sideways"}
    assert set(payload["regime_counts"]) == {"Bull trend", "Bear trend", "Sideways"}
    assert len(payload["breakdown"]) == 3
    assert sum(item["trades_count"] for item in payload["breakdown"]) == 3
    assert "robustness_score" in payload["robustness_summary"]


def test_market_regime_requires_market_data():
    response = client.post(
        "/api/v1/market-regime/run",
        json={
            "initial_capital": 100000,
            "market_data": [],
            "trades": [{"exit_time": "2025-01-01", "pnl": 100}],
        },
    )

    assert response.status_code == 400
