from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_strategy_scorecard_returns_tearsheet_metrics():
    response = client.post(
        "/api/v1/strategy-scorecard/run",
        json={
            "initial_capital": 100000,
            "equity_curve": [
                {"timestamp": "2025-01-01", "equity": 100000},
                {"timestamp": "2025-01-02", "equity": 101000},
                {"timestamp": "2025-01-03", "equity": 100500},
                {"timestamp": "2025-01-04", "equity": 102000},
                {"timestamp": "2025-01-05", "equity": 101500},
            ],
            "trades": [
                {"entry_time": "2025-01-01", "exit_time": "2025-01-02", "pnl": 1000},
                {"entry_time": "2025-01-02", "exit_time": "2025-01-03", "pnl": -500},
                {"entry_time": "2025-01-03", "exit_time": "2025-01-04", "pnl": 1500},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    metrics = payload["metrics"]

    for key in [
        "cagr",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "profit_factor",
        "expectancy",
        "avg_win",
        "avg_loss",
        "exposure_pct",
        "recovery_factor",
    ]:
        assert key in metrics

    assert metrics["profit_factor"] == 5.0
    assert metrics["expectancy"] > 0
    assert payload["highlights"]
    assert payload["warnings"]
    assert "252-period annualization" in payload["method"]


def test_strategy_scorecard_requires_equity_curve():
    response = client.post(
        "/api/v1/strategy-scorecard/run",
        json={
            "initial_capital": 100000,
            "equity_curve": [{"timestamp": "2025-01-01", "equity": 100000}],
            "trades": [],
        },
    )

    assert response.status_code == 400
