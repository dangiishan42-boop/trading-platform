from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.database.session import engine
from app.main import app
from app.models.instrument_master_model import FnoUnderlying, InstrumentMaster
from app.models.market_data_model import FnoQuoteCache


client = TestClient(app)


def _clear_stock_data():
    with Session(engine) as session:
        session.exec(delete(FnoQuoteCache))
        session.exec(delete(FnoUnderlying))
        session.exec(delete(InstrumentMaster))
        session.commit()


def _seed_stock_data():
    with Session(engine) as session:
        session.add_all(
            [
                InstrumentMaster(exchange="NSE", symbol="AAA", name="AAA Ltd", token="101", trading_symbol="AAA-EQ", instrument_type="EQ", is_equity=True),
                InstrumentMaster(exchange="NSE", symbol="BBB", name="BBB Bank", token="102", trading_symbol="BBB-EQ", instrument_type="EQ", is_equity=True),
                InstrumentMaster(exchange="BSE", symbol="CCC", name="CCC Metals", token="103", trading_symbol="CCC", instrument_type="EQ", is_equity=True),
                InstrumentMaster(exchange="NFO", symbol="AAA", name="AAA Ltd", token="901", trading_symbol="AAA26MAYFUT", instrument_type="FUTSTK", underlying="AAA", is_fno=True, is_future=True),
            ]
        )
        session.add(FnoUnderlying(symbol="AAA", name="AAA Ltd", exchange="NSE", equity_token="101", nearest_future_token="901", active_expiries="2026-05-28", has_futures=True, has_options=True, lot_size=100))
        session.add_all(
            [
                FnoQuoteCache(symbol="AAA", name="AAA Ltd", exchange="NSE", token="101", ltp=110, open=100, high=112, low=99, previous_close=100, point_change=10, percent_change=10, volume=5000, source="Live: Angel One"),
                FnoQuoteCache(symbol="BBB", name="BBB Bank", exchange="NSE", token="102", ltp=95, previous_close=100, point_change=-5, percent_change=-5, volume=8000, source="Live: Angel One"),
            ]
        )
        session.commit()


def test_stocks_page_loads():
    response = client.get("/stocks")

    assert response.status_code == 200
    assert "Stocks" in response.text
    assert "NSE/BSE/F&O Stock Universe" in response.text
    assert "/api/v1/stocks" in response.text


def test_stocks_fno_universe_returns_rows_and_null_fundamentals():
    _clear_stock_data()
    _seed_stock_data()

    response = client.get("/api/v1/stocks?universe=fno")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    row = payload["rows"][0]
    assert row["symbol"] == "AAA"
    assert row["is_fno"] is True
    assert row["ltp"] == 110
    assert row["market_cap"] is None
    assert row["pe"] is None
    assert row["eps"] is None
    assert "Fundamental fields require fundamentals data source." in payload["warnings"]


def test_stocks_fno_universe_clean_empty_state():
    _clear_stock_data()

    response = client.get("/api/v1/stocks?universe=fno")

    assert response.status_code == 200
    payload = response.json()
    assert payload["rows"] == []
    assert payload["total"] == 0
    assert "Instrument master not synced. Run instrument sync first." in payload["warnings"]


def test_stocks_search_filter_works():
    _clear_stock_data()
    _seed_stock_data()

    response = client.get("/api/v1/stocks?universe=all&search=bank")

    assert response.status_code == 200
    payload = response.json()
    assert [row["symbol"] for row in payload["rows"]] == ["BBB"]


def test_stocks_pagination_works():
    _clear_stock_data()
    _seed_stock_data()

    response = client.get("/api/v1/stocks?universe=all&limit=2&offset=1&sort_by=symbol")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert [row["symbol"] for row in payload["rows"]] == ["BBB", "CCC"]


def test_stocks_sort_by_percent_change_works():
    _clear_stock_data()
    _seed_stock_data()

    response = client.get("/api/v1/stocks?universe=all&sort_by=percent_change&sort_direction=desc")

    assert response.status_code == 200
    payload = response.json()
    assert [row["symbol"] for row in payload["rows"][:2]] == ["AAA", "BBB"]


def test_market_watch_and_screener_still_work_with_stocks_route():
    for path, expected in [
        ("/market-watch", "Live Market Watch"),
        ("/screener", "Enterprise grade stock screener"),
    ]:
        response = client.get(path)

        assert response.status_code == 200
        assert expected in response.text
        assert "/stocks" in response.text
