from pathlib import Path

from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app
from app.services.data.angel_smartapi_service import AngelSmartApiService


client = TestClient(app)


def test_upload_saves_dataset_metadata_and_lists_recent_uploads():
    sample_path = Path("data/samples/sample_ohlcv.csv")
    response = client.post(
        "/api/v1/data/upload",
        files={
            "file": (
                sample_path.name,
                sample_path.read_bytes(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["original_file_name"] == sample_path.name
    assert payload["file_name"]
    assert payload["preview"]["total_rows"] > 0
    assert payload["preview"]["min_date"]
    assert payload["preview"]["max_date"]

    datasets_response = client.get("/api/v1/data/uploads?limit=10")

    assert datasets_response.status_code == 200

    datasets_payload = datasets_response.json()

    assert isinstance(datasets_payload, list)
    assert datasets_payload
    assert len(datasets_payload) <= 10

    matching_entry = next(
        (entry for entry in datasets_payload if entry["stored_file_name"] == payload["file_name"]),
        None,
    )

    assert matching_entry is not None
    assert matching_entry["original_file_name"] == sample_path.name
    assert matching_entry["stored_file_name"] == payload["file_name"]
    assert matching_entry["row_count"] == payload["preview"]["total_rows"]
    assert matching_entry["min_date"]
    assert matching_entry["max_date"]
    assert matching_entry["uploaded_at"]


def test_upload_rejects_binary_or_non_csv_content():
    response = client.post(
        "/api/v1/data/upload",
        files={
            "file": (
                "suspicious.csv",
                b"\x00\x01\x02not-a-valid-csv",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert "Unsupported upload content type" in response.json()["detail"]


def test_fetch_angel_saves_dataset_metadata_and_lists_recent_uploads(monkeypatch):
    class FakeSmartClient:
        def __init__(self) -> None:
            self.terminated = False

        def generateSession(self, client_id, mpin, totp):
            assert client_id == "TESTCLIENT"
            assert mpin == "1234"
            assert totp == "654321"
            return {"status": True, "data": {"clientcode": client_id}}

        def getCandleData(self, params):
            assert params["exchange"] == "NSE"
            assert params["symboltoken"] == "3045"
            assert params["interval"] == "ONE_MINUTE"
            return {
                "status": True,
                "data": [
                    ["2026-04-01 09:15", "100", "105", "99", "104", "1000"],
                    ["2026-04-01 09:16", "104", "106", "103", "105", "1100"],
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
        "/api/v1/data/fetch-angel",
        json={
            "exchange": "nse",
            "symbol_token": "3045",
            "interval": "one_minute",
            "fromdate": "2026-04-01T09:15:00",
            "todate": "2026-04-01T09:17:00",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["message"] == "Angel One data fetched successfully"
    assert payload["stored_file_name"].endswith(".csv")
    assert payload["row_count"] == 2
    assert payload["min_date"].startswith("2026-04-01T09:15:00")
    assert payload["max_date"].startswith("2026-04-01T09:16:00")
    assert Path(payload["path"]).exists()
    assert fake_client.terminated is True

    datasets_response = client.get("/api/v1/data/uploads?limit=10")

    assert datasets_response.status_code == 200

    datasets_payload = datasets_response.json()
    matching_entry = next(
        (entry for entry in datasets_payload if entry["stored_file_name"] == payload["stored_file_name"]),
        None,
    )

    assert matching_entry is not None
    assert matching_entry["original_file_name"] == payload["original_file_name"]
    assert matching_entry["row_count"] == 2

    saved_file = Path(payload["path"])
    saved_header = saved_file.read_text(encoding="utf-8").splitlines()[0]
    assert saved_header == "Date,Open,High,Low,Close,Volume"

    get_settings.cache_clear()


def test_fetch_angel_requires_configured_credentials(monkeypatch):
    monkeypatch.delenv("ANGEL_API_KEY", raising=False)
    monkeypatch.delenv("ANGEL_CLIENT_ID", raising=False)
    monkeypatch.delenv("ANGEL_MPIN", raising=False)
    monkeypatch.delenv("ANGEL_TOTP_SECRET", raising=False)
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/data/fetch-angel",
        json={
            "exchange": "NSE",
            "symbol_token": "3045",
            "interval": "ONE_MINUTE",
            "fromdate": "2026-04-01T09:15:00",
            "todate": "2026-04-01T09:17:00",
        },
    )

    assert response.status_code == 400
    assert "Angel One credentials are not configured" in response.json()["detail"]

    get_settings.cache_clear()
