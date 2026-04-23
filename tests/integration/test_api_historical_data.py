from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app
from app.services.data.angel_smartapi_service import AngelSmartApiService


client = TestClient(app)


def test_historical_data_page_loads():
    response = client.get("/historical-data")

    assert response.status_code == 200
    assert "Historical Data" in response.text


def test_historical_data_endpoint_supports_symbol_mapping_and_derived_interval(monkeypatch):
    class FakeSmartClient:
        def __init__(self) -> None:
            self.terminated = False

        def generateSession(self, client_id, mpin, totp):
            assert client_id == "TESTCLIENT"
            assert mpin == "1234"
            assert totp == "654321"
            return {"status": True}

        def getCandleData(self, params):
            assert params["exchange"] == "NSE"
            assert params["symboltoken"] == "2885"
            assert params["interval"] == "ONE_HOUR"
            return {
                "status": True,
                "data": [
                    ["2026-04-01 09:00", "100", "101", "99", "100", "1000"],
                    ["2026-04-01 10:00", "100", "103", "99", "102", "1100"],
                    ["2026-04-01 11:00", "102", "104", "101", "103", "1200"],
                    ["2026-04-01 12:00", "103", "105", "102", "104", "1300"],
                    ["2026-04-01 13:00", "104", "106", "103", "105", "1400"],
                    ["2026-04-01 14:00", "105", "107", "104", "106", "1500"],
                ],
            }

        def terminateSession(self, client_id):
            self.terminated = True
            return {"status": True}

    monkeypatch.setenv("ANGEL_API_KEY", "api-key")
    monkeypatch.setenv("ANGEL_CLIENT_ID", "TESTCLIENT")
    monkeypatch.setenv("ANGEL_MPIN", "1234")
    monkeypatch.setenv("ANGEL_TOTP_SECRET", "totp-secret")
    get_settings.cache_clear()

    fake_client = FakeSmartClient()
    monkeypatch.setattr(AngelSmartApiService, "_build_client", lambda self, api_key: fake_client)
    monkeypatch.setattr(AngelSmartApiService, "_generate_totp", lambda self, secret: "654321")

    response = client.post(
        "/api/v1/data/historical",
        json={
            "exchange": "nse",
            "symbol": "reliance",
            "interval": "3h",
            "fromdate": "2026-04-01T09:00:00",
            "todate": "2026-04-01T15:00:00",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["exchange"] == "NSE"
    assert payload["symbol"] == "RELIANCE"
    assert payload["symbol_token"] == "2885"
    assert payload["interval"] == "3H"
    assert payload["row_count"] == 2
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["open"] == 100.0
    assert payload["rows"][0]["high"] == 104.0
    assert payload["rows"][0]["low"] == 99.0
    assert payload["rows"][0]["close"] == 103.0
    assert payload["rows"][0]["volume"] == 3300.0
    assert payload["rows"][0]["change"] is None
    assert payload["rows"][1]["open"] == 103.0
    assert payload["rows"][1]["high"] == 107.0
    assert payload["rows"][1]["low"] == 102.0
    assert payload["rows"][1]["close"] == 106.0
    assert payload["rows"][1]["volume"] == 4200.0
    assert payload["rows"][1]["change"] == 3.0
    assert payload["rows"][1]["change_pct"] == 2.9126
    assert fake_client.terminated is True

    get_settings.cache_clear()
