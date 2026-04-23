from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_optimization_run_returns_ranked_results():
    response = client.post(
        "/api/v1/optimization/run",
        json={
            "source": "sample",
            "symbol": "DEMO",
            "timeframe": "1D",
            "strategy_name": "breakout",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "position_sizing_mode": "fixed_capital",
            "capital_per_trade": 25000,
            "parameters": {
                "lookback": [10, 20, 30],
            },
            "max_results": 10,
        },
    )

    assert response.status_code == 200

    payload = response.json()
    results = payload["results"]

    assert payload["strategy_name"] == "breakout"
    assert payload["evaluated_count"] == 3
    assert payload["evaluated_count"] >= len(results) >= 1
    assert len(results) <= 10

    for index, result in enumerate(results, start=1):
        assert result["rank"] == index
        assert result["strategy_name"] == "breakout"
        assert "parameters" in result
        assert "lookback" in result["parameters"]
        assert "metrics" in result
        assert "total_return_pct" in result["metrics"]
        assert "win_rate_pct" in result["metrics"]
        assert "max_drawdown_pct" in result["metrics"]
        assert result["score"] == result["objective_score"]

    if len(results) > 1:
        assert results[0]["score"] >= results[-1]["score"]
