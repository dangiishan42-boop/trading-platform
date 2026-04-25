from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.database.session import engine
from app.main import app
from app.models.instrument_master_model import InstrumentMaster


client = TestClient(app)


def test_instrument_search_endpoint():
    with Session(engine) as session:
        session.exec(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                exchange="NSE",
                symbol="RELIANCE",
                name="Reliance Industries",
                token="2885",
                instrument_type="EQ",
                lot_size=1,
                tick_size=0.05,
            )
        )
        session.commit()

    response = client.get("/api/v1/instruments/search?q=reliance&exchange=NSE")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["symbol"] == "RELIANCE"
    assert payload["items"][0]["name"] == "Reliance Industries"
    assert payload["items"][0]["token"] == "2885"


def test_selected_instrument_candle_fetch_uses_master_token(monkeypatch):
    with Session(engine) as session:
        session.exec(delete(InstrumentMaster))
        session.add(
            InstrumentMaster(
                exchange="NSE",
                symbol="RELIANCE",
                name="Reliance Industries",
                token="2885",
                instrument_type="EQ",
                lot_size=1,
                tick_size=0.05,
            )
        )
        session.commit()

    def fake_fetch_frame(self, request):
        assert request.exchange == "NSE"
        assert request.symbol_token == "2885"
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "Date": "2026-04-24 09:15",
                    "Open": 100,
                    "High": 101,
                    "Low": 99,
                    "Close": 100.5,
                    "Volume": 1000,
                }
            ]
        )

    monkeypatch.setattr("app.services.data.angel_smartapi_service.AngelSmartApiService.fetch_frame", fake_fetch_frame)

    response = client.post(
        "/api/v1/market-watch/candles",
        json={"query": "RELIANCE", "exchange": "NSE", "interval": "5m"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "RELIANCE"
    assert payload["symbol_token"] == "2885"
    assert payload["rows"][0]["close"] == 100.5
