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
            "from_date": "2025-01-01",
            "to_date": "2025-12-31",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "position_sizing_mode": "fixed_capital",
            "capital_per_trade": 25000,
            "ranking_metric": "net_profit",
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
    assert payload["ranking_metric"] == "net_profit"
    assert payload["evaluated_count"] == 3
    assert payload["evaluated_count"] >= len(results) >= 1
    assert len(results) <= 10

    for index, result in enumerate(results, start=1):
        assert result["rank"] == index
        assert result["strategy_name"] == "breakout"
        assert "parameters" in result
        assert "lookback" in result["parameters"]
        assert result["from_date"] == "2025-01-01"
        assert result["to_date"] == "2025-12-31"
        assert "net_profit" in result
        assert "total_return_pct" in result
        assert "win_rate_pct" in result
        assert "max_drawdown_pct" in result
        assert "total_trades" in result
        assert "ending_equity" in result
        assert "metrics" in result
        assert result["net_profit"] == result["metrics"]["net_profit"]
        assert "total_return_pct" in result["metrics"]
        assert "win_rate_pct" in result["metrics"]
        assert "max_drawdown_pct" in result["metrics"]
        assert result["score"] == result["objective_score"]

    if len(results) > 1:
        assert results[0]["score"] >= results[-1]["score"]


def test_optimization_supports_ema_defaults_and_lowest_drawdown_ranking():
    response = client.post(
        "/api/v1/optimization/run",
        json={
            "source": "sample",
            "symbol": "DEMO",
            "timeframe": "1D",
            "strategy_name": "ema_crossover",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "position_sizing_mode": "fixed_capital",
            "capital_per_trade": 25000,
            "ranking_metric": "max_drawdown_pct",
            "max_results": 20,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    results = payload["results"]

    assert payload["evaluated_count"] == 20
    assert 1 <= len(results) <= 20
    assert all(result["parameters"]["fast_period"] < result["parameters"]["slow_period"] for result in results)
    assert all(result["ranking_metric"] == "max_drawdown_pct" for result in results)
    if len(results) > 1:
        assert results[0]["max_drawdown_pct"] <= results[-1]["max_drawdown_pct"]


def test_walk_forward_optimization_returns_out_of_sample_ranked_results():
    response = client.post(
        "/api/v1/optimization/run",
        json={
            "source": "sample",
            "symbol": "DEMO",
            "timeframe": "1D",
            "strategy_name": "breakout",
            "from_date": "2025-01-01",
            "to_date": "2025-12-31",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "position_sizing_mode": "fixed_capital",
            "capital_per_trade": 25000,
            "optimization_mode": "walk_forward",
            "walk_forward_split": "60_40",
            "parameters": {
                "lookback": [10, 20, 30],
            },
            "max_results": 10,
        },
    )

    assert response.status_code == 200

    payload = response.json()
    results = payload["results"]

    assert payload["optimization_mode"] == "walk_forward"
    assert payload["walk_forward_split"] == "60_40"
    assert payload["ranking_metric"] == "out_sample_net_profit"
    assert payload["evaluated_count"] == 3
    assert payload["best_in_sample_parameters"]
    assert 1 <= len(results) <= 10

    for index, result in enumerate(results, start=1):
        assert result["rank"] == index
        assert result["optimization_mode"] == "walk_forward"
        assert result["walk_forward_split"] == "60_40"
        assert "parameters" in result
        assert "in_sample_net_profit" in result
        assert "out_sample_net_profit" in result
        assert "in_sample_return" in result
        assert "out_sample_return" in result
        assert "out_sample_drawdown" in result
        assert "robustness_score" in result
        assert "performance_degraded" in result
        assert result["net_profit"] == result["out_sample_net_profit"]
        assert result["total_return_pct"] == result["out_sample_return"]

    if len(results) > 1:
        assert results[0]["out_sample_net_profit"] >= results[-1]["out_sample_net_profit"]
