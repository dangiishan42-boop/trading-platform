import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_save_strategy_configuration_and_list_recent_configurations():
    response = client.post(
        "/api/v1/strategies/configurations",
        json={
            "strategy_name": "ema_crossover",
            "display_name": "EMA Daily Pullback",
            "parameters": {
                "fast_period": 15,
                "slow_period": 40,
            },
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["strategy_name"] == "ema_crossover"
    assert payload["display_name"] == "EMA Daily Pullback"
    assert json.loads(payload["parameters_json"]) == {
        "fast_period": 15,
        "slow_period": 40,
    }
    assert payload["created_at"]

    saved_response = client.get("/api/v1/strategies/configurations?limit=10")

    assert saved_response.status_code == 200

    saved_payload = saved_response.json()

    assert isinstance(saved_payload, list)
    assert saved_payload
    assert len(saved_payload) <= 10

    matching_entry = next((entry for entry in saved_payload if entry["id"] == payload["id"]), None)

    assert matching_entry is not None
    assert matching_entry["strategy_name"] == "ema_crossover"
    assert matching_entry["display_name"] == "EMA Daily Pullback"
    assert json.loads(matching_entry["parameters_json"]) == {
        "fast_period": 15,
        "slow_period": 40,
    }
