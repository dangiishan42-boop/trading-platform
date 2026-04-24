from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_monte_carlo_run_returns_robustness_summary():
    response = client.post(
        "/api/v1/monte-carlo/run",
        json={
            "source": "backtest",
            "initial_capital": 100000,
            "simulation_count": 100,
            "drawdown_threshold_pct": 5,
            "noise_pct": 3,
            "trades": [
                {"pnl": 1200},
                {"pnl": -500},
                {"pnl": 800},
                {"pnl": -300},
                {"pnl": 450},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["simulation_count"] == 100
    assert payload["trade_count"] == 5
    assert "median_return" in payload
    assert "worst_case_return" in payload
    assert "best_case_return" in payload
    assert 0 <= payload["probability_of_loss"] <= 100
    assert 0 <= payload["probability_of_drawdown_beyond_threshold"] <= 100
    assert 0 <= payload["robustness_score"] <= 100
    assert payload["distribution"]
    assert len(payload["sample_simulations"]) <= 50


def test_monte_carlo_requires_supported_simulation_count():
    response = client.post(
        "/api/v1/monte-carlo/run",
        json={
            "initial_capital": 100000,
            "simulation_count": 250,
            "drawdown_threshold_pct": 10,
            "trades": [{"pnl": 100}],
        },
    )

    assert response.status_code == 422
