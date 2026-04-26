from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.database.session import engine
from app.main import app
from app.models.instrument_master_model import FnoUnderlying, InstrumentMaster


client = TestClient(app)


def test_instrument_search_endpoint():
    with Session(engine) as session:
        session.exec(delete(FnoUnderlying))
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
                is_equity=True,
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
        session.exec(delete(FnoUnderlying))
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
                is_equity=True,
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


def test_fno_underlyings_and_contract_endpoints_return_unique_contracts():
    with Session(engine) as session:
        session.exec(delete(FnoUnderlying))
        session.exec(delete(InstrumentMaster))
        session.add(
            FnoUnderlying(
                symbol="RELIANCE",
                name="Reliance Industries",
                exchange="NSE",
                equity_token="2885",
                nearest_future_token="111",
                active_expiries="2025-04-24",
                has_futures=True,
                has_options=True,
                lot_size=250,
            )
        )
        session.add_all(
            [
                InstrumentMaster(
                    exchange="NFO",
                    symbol="RELIANCE",
                    name="RELIANCE",
                    trading_symbol="RELIANCE25APRFUT",
                    token="111",
                    instrument_type="FUTSTK",
                    expiry="2025-04-24",
                    lot_size=250,
                    underlying="RELIANCE",
                    is_fno=True,
                    is_future=True,
                ),
                InstrumentMaster(
                    exchange="NFO",
                    symbol="RELIANCE",
                    name="RELIANCE",
                    trading_symbol="RELIANCE25APR2500CE",
                    token="112",
                    instrument_type="OPTSTK",
                    expiry="2025-04-24",
                    strike=2500,
                    option_type="CE",
                    lot_size=250,
                    underlying="RELIANCE",
                    is_fno=True,
                    is_option=True,
                ),
            ]
        )
        session.commit()

    underlyings_response = client.get("/api/v1/instruments/fno-underlyings?q=rel")
    assert underlyings_response.status_code == 200
    underlyings = underlyings_response.json()
    assert [row["symbol"] for row in underlyings] == ["RELIANCE"]

    contracts_response = client.get("/api/v1/instruments/fno-contracts?symbol=RELIANCE")
    assert contracts_response.status_code == 200
    contracts = contracts_response.json()
    assert contracts["futures"][0]["token"] == "111"
    assert contracts["options"][0]["option_type"] == "CE"

    expiries_response = client.get("/api/v1/instruments/fno-expiries?symbol=RELIANCE")
    assert expiries_response.status_code == 200
    assert expiries_response.json()["expiries"] == ["2025-04-24"]
