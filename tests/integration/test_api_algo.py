from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_algo_capabilities_returns_rule_options():
    response = client.get("/api/v1/algo/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert "Price" in payload["condition_sources"]
    assert "ATR" in payload["condition_sources"]
    assert "crosses above" in payload["operators"]
    assert "Weekly" in payload["timeframes"]
    assert "Short" in payload["entry_actions"]
    assert "F&O Stocks" in payload["data_universes"]
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


def test_algo_simulate_supports_advanced_strategy_payload():
    response = client.post(
        "/api/v1/algo/simulate",
        json={
            "source": "sample",
            "symbol": "DEMO",
            "exchange": "NSE",
            "timeframe": "1D",
            "initial_capital": 100000,
            "require_all_conditions": True,
            "legs": [
                {
                    "name": "Trend Confirmation",
                    "connector": "AND",
                    "conditions": [
                        {"source": "RSI", "timeframe": "Weekly", "operator": ">", "value": 30, "period": 14},
                        {
                            "source": "Price",
                            "timeframe": "Daily",
                            "operator": "crosses above",
                            "value": 0,
                            "compare_source": "EMA",
                            "compare_period": 20,
                            "connector": "AND",
                        },
                    ],
                }
            ],
            "position": {
                "action": "Buy",
                "sizing_mode": "capital_pct",
                "capital_allocation_pct": 25,
            },
            "exits": {
                "stop_type": "fixed_pct",
                "stop_loss_pct": 2,
                "target_type": "multi_target",
                "targets": [{"target_pct": 4, "exit_pct": 50}, {"target_pct": 8, "exit_pct": 50}],
                "exit_conditions": [
                    {"signal_type": "exit", "source": "RSI", "operator": "<", "value": 45, "period": 14}
                ],
            },
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "gross_profit" in payload
    assert "gross_loss" in payload
    assert "expectancy" in payload
    assert isinstance(payload["equity_curve"], list)


def test_algo_simulate_accepts_fetched_dataset_source_alias():
    upload_response = client.post(
        "/api/v1/data/upload",
        files={
            "file": (
                "algo_fetched_alias.csv",
                b"Date,Open,High,Low,Close,Volume\n"
                b"2025-01-01,100,105,99,104,1000\n"
                b"2025-01-02,104,108,103,107,1200\n"
                b"2025-01-03,107,109,101,102,1100\n",
                "text/csv",
            )
        },
    )
    assert upload_response.status_code == 200
    stored_file_name = upload_response.json()["file_name"]

    response = client.post(
        "/api/v1/algo/simulate",
        json={
            "source": "fetched",
            "file_name": stored_file_name,
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "timeframe": "1D",
            "conditions": [
                {"signal_type": "buy", "source": "Price", "operator": ">", "value": 100, "connector": "AND"}
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "RELIANCE"
    assert "metrics" in payload


def test_algo_validate_returns_strategy_warnings():
    response = client.post(
        "/api/v1/algo/validate",
        json={
            "config": {
                "source": "sample",
                "symbol": "DEMO",
                "exchange": "NSE",
                "timeframe": "1D",
                "legs": [
                    {
                        "name": "Conflicting Leg",
                        "conditions": [
                            {"source": "RSI", "operator": ">", "value": 70},
                            {"source": "RSI", "operator": "<", "value": 30},
                        ],
                    }
                ],
                "exits": {"stop_type": "none", "target_type": "none", "exit_conditions": []},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["warnings"]


def test_algo_strategy_save_and_list_round_trip():
    payload = {
        "name": "Test RSI Algo",
        "config": {
            "source": "sample",
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "timeframe": "1D",
            "from_date": "2025-01-01",
            "to_date": "2025-12-31",
            "require_all_conditions": True,
            "initial_capital": 100000,
            "stop_loss_pct": 2,
            "target_pct": 4,
            "position_size": 25000,
            "max_trades_per_day": 5,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "conditions": [
                {"signal_type": "buy", "source": "Price", "operator": ">", "value": 100, "connector": "AND"}
            ],
        },
    }

    save_response = client.post("/api/v1/algo/strategies", json=payload)

    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["name"] == "Test RSI Algo"
    assert saved["symbol"] == "RELIANCE"
    assert saved["config"]["conditions"][0]["source"] == "Price"

    list_response = client.get("/api/v1/algo/strategies")

    assert list_response.status_code == 200
    strategies = list_response.json()
    assert any(item["id"] == saved["id"] for item in strategies)


def test_algo_simulate_accepts_fno_data_universe():
    response = client.post(
        "/api/v1/algo/simulate",
        json={
            "source": "sample",
            "symbol": "RELIANCE",
            "data_universe": "F&O Stocks",
            "exchange": "NSE",
            "timeframe": "1D",
            "conditions": [
                {"signal_type": "buy", "source": "Price", "operator": ">", "value": 100, "connector": "AND"}
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["symbol"] == "RELIANCE"
