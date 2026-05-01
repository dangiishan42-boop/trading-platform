from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.database.session import engine
from app.main import app
from app.models.instrument_master_model import FnoUnderlying, InstrumentMaster
from app.models.market_data_model import FnoQuoteCache
from app.services.data.angel_smartapi_service import AngelSmartApiService
from app.services.market_data.fno_live_data_service import FnoLiveDataService


client = TestClient(app)


def _clear_fno_data():
    with Session(engine) as session:
        session.exec(delete(FnoQuoteCache))
        session.exec(delete(FnoUnderlying))
        session.exec(delete(InstrumentMaster))
        session.commit()


def _add_fno_underlyings(symbols: list[str]):
    with Session(engine) as session:
        for index, symbol in enumerate(symbols, start=1):
            token = str(1000 + index)
            session.add(
                FnoUnderlying(
                    symbol=symbol,
                    name=f"{symbol} Ltd",
                    exchange="NSE",
                    equity_token=token,
                    nearest_future_token=str(9000 + index),
                    active_expiries="2026-05-28",
                    has_futures=True,
                    has_options=True,
                    lot_size=100,
                )
            )
            session.add(
                InstrumentMaster(
                    exchange="NSE",
                    symbol=symbol,
                    name=f"{symbol} Ltd",
                    token=token,
                    trading_symbol=f"{symbol}-EQ",
                    instrument_type="EQ",
                    is_equity=True,
                )
            )
        session.commit()


def test_fno_live_refresh_handles_empty_universe():
    _clear_fno_data()

    response = client.post("/api/v1/market-data/fno-live-refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_status"] == "F&O instrument master not synced. Run instrument sync first."
    assert payload["refreshed_count"] == 0


def test_fno_live_refresh_batches_symbols(monkeypatch):
    _clear_fno_data()
    _add_fno_underlyings(["AAA", "BBB", "CCC"])
    calls = []

    monkeypatch.setattr(AngelSmartApiService, "has_credentials", lambda self: True)

    def fake_fetch_ltp_batch(self, instruments, mode="FULL"):
        calls.append([item["symbol"] for item in instruments])
        fetched = [
            {
                "symbolToken": item["token"],
                "ltp": 100,
                "open": 98,
                "high": 101,
                "low": 97,
                "close": 96,
                "tradeVolume": 1000,
            }
            for item in instruments
        ]
        return {"status": True, "data": {"fetched": fetched}}

    monkeypatch.setattr(AngelSmartApiService, "fetch_ltp_batch", fake_fetch_ltp_batch)

    with Session(engine) as session:
        status = FnoLiveDataService().refresh(session, batch_size=2, batch_delay_seconds=0)

    assert calls == [["AAA", "BBB"], ["CCC"]]
    assert status["refreshed_count"] == 3
    assert status["failed_count"] == 0


def test_failed_symbols_do_not_delete_old_cache(monkeypatch):
    _clear_fno_data()
    _add_fno_underlyings(["AAA", "BBB"])
    with Session(engine) as session:
        session.add(FnoQuoteCache(symbol="BBB", name="BBB Ltd", exchange="NSE", token="1002", ltp=55, percent_change=1.2, source="Cached"))
        session.commit()

    monkeypatch.setattr(AngelSmartApiService, "has_credentials", lambda self: True)

    def fake_fetch_ltp_batch(self, instruments, mode="FULL"):
        return {
            "status": True,
            "data": {
                "fetched": [
                    {
                        "symbolToken": "1001",
                        "ltp": 110,
                        "open": 105,
                        "high": 111,
                        "low": 104,
                        "close": 100,
                        "tradeVolume": 2000,
                    }
                ]
            },
        }

    monkeypatch.setattr(AngelSmartApiService, "fetch_ltp_batch", fake_fetch_ltp_batch)

    with Session(engine) as session:
        status = FnoLiveDataService().refresh(session, batch_size=2, batch_delay_seconds=0)
        old = session.exec(select(FnoQuoteCache).where(FnoQuoteCache.symbol == "BBB")).first()

    assert status["refreshed_count"] == 1
    assert old is not None
    assert old.ltp == 55
    assert old.source == "Cached"
    assert old.failure_message == "Angel One returned no quote for symbol"


def test_fno_quotes_endpoint_paginates():
    _clear_fno_data()
    with Session(engine) as session:
        session.add_all(
            [
                FnoQuoteCache(symbol="AAA", name="AAA Ltd", exchange="NSE", token="1", ltp=10, percent_change=1, source="Live: Angel One"),
                FnoQuoteCache(symbol="BBB", name="BBB Ltd", exchange="NSE", token="2", ltp=20, percent_change=2, source="Live: Angel One"),
                FnoQuoteCache(symbol="CCC", name="CCC Ltd", exchange="NSE", token="3", ltp=30, percent_change=3, source="Live: Angel One"),
            ]
        )
        session.commit()

    response = client.get("/api/v1/market-data/fno-quotes?limit=2&offset=1&sort_by=symbol")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert [row["symbol"] for row in payload["items"]] == ["BBB", "CCC"]


def test_screener_fno_universe_reads_cached_snapshot():
    _clear_fno_data()
    _add_fno_underlyings(["AAA"])
    with Session(engine) as session:
        session.add(FnoQuoteCache(symbol="AAA", name="AAA Ltd", exchange="NSE", token="1001", ltp=123, percent_change=4.5, volume=10000, source="Live: Angel One"))
        session.commit()

    response = client.post("/api/v1/screener/run", json={"universe": "F&O Stocks", "exchange": "NSE", "filters": []})

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["symbol"] == "AAA"
    assert row["ltp"] == 123
    assert row["data_source_badge"] == "Live: Angel One"


def test_heatmap_fno_universe_reads_cached_snapshot():
    _clear_fno_data()
    _add_fno_underlyings(["AAA"])
    with Session(engine) as session:
        session.add(FnoQuoteCache(symbol="AAA", name="AAA Ltd", exchange="NSE", token="1001", ltp=123, percent_change=-2.5, volume=10000, source="Live: Angel One"))
        session.commit()

    response = client.post("/api/v1/heatmap/run", json={"universe": "F&O Stocks", "size_by": "Volume", "color_by": "% Change", "timeframe": "1D"})

    assert response.status_code == 200
    row = response.json()["stocks"][0]
    assert row["symbol"] == "AAA"
    assert row["price"] == 123
    assert row["change_pct"] == -2.5
