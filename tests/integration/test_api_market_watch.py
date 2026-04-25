from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_market_watch_home_page_loads():
    response = client.get("/")

    assert response.status_code == 200
    assert "Live Market Watch" in response.text
    assert "/dashboard" in response.text


def test_dashboard_page_still_loads():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Optimization Results" in response.text


def test_market_watch_large_chart_page_loads():
    response = client.get("/market-watch/chart")

    assert response.status_code == 200
    assert "Advanced Chart" in response.text
    assert "Open Large Chart" in response.text


def test_market_watch_quote_uses_service(monkeypatch):
    class FakeMarketWatchService:
        def quote(self, query, exchange, symbol_token):
            return {
                "symbol": "RELIANCE",
                "stock_name": "Reliance Industries",
                "exchange": "NSE",
                "symbol_token": "2885",
                "latest_price": 2500.0,
                "change": 12.5,
                "change_pct": 0.5,
                "available": True,
            }

    monkeypatch.setattr("app.api.v1.endpoints.market_watch.MarketWatchService", FakeMarketWatchService)

    response = client.post(
        "/api/v1/market-watch/quote",
        json={"query": "RELIANCE", "exchange": "NSE"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "RELIANCE"
    assert payload["latest_price"] == 2500.0


def test_market_watch_candles_uses_service(monkeypatch):
    class FakeMarketWatchService:
        def candles(self, query, exchange, symbol_token, interval, fromdate, todate):
            return {
                "symbol": "TCS",
                "stock_name": "Tata Consultancy Services",
                "exchange": "NSE",
                "symbol_token": "11536",
                "interval": interval,
                "rows": [
                    {"datetime": "2026-04-24T09:15:00", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100}
                ],
            }

    monkeypatch.setattr("app.api.v1.endpoints.market_watch.MarketWatchService", FakeMarketWatchService)

    response = client.post(
        "/api/v1/market-watch/candles",
        json={"query": "TCS", "exchange": "NSE", "interval": "5m"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "TCS"
    assert payload["rows"][0]["close"] == 2
