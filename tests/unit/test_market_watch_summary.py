from app.services.data.market_watch_service import MarketWatchService


class FakeMarketData:
    QUOTES = {
        "RELIANCE": {"latest_price": 100, "change": 5, "change_pct": 5, "volume": 1000},
        "TCS": {"latest_price": 200, "change": -4, "change_pct": -2, "volume": 2000},
        "INFY": {"latest_price": 300, "change": 0, "change_pct": 0, "volume": 3000},
        "HDFCBANK": {"latest_price": None, "change": None, "change_pct": None, "volume": None, "available": False},
    }

    def get_quote(self, *, symbol=None, token=None, exchange="NSE", session=None):
        data = self.QUOTES.get(symbol, {"latest_price": 50, "change": 1, "change_pct": 1, "volume": 10})
        return {
            "symbol": symbol,
            "stock_name": symbol,
            "exchange": exchange,
            "symbol_token": token,
            "available": data.get("available", True),
            "data_source_badge": "Live: Angel One",
            "data_source_note": "test",
            **data,
        }

    def get_indices(self):
        return [
            {"name": "NIFTY 50", "exchange": "NSE", "latest_price": 22000, "change": 10, "change_pct": 0.05, "available": True, "data_source_badge": "Live: Angel One"},
            {"name": "SENSEX", "exchange": "BSE", "latest_price": None, "change": None, "change_pct": None, "available": False, "data_source_badge": "Unavailable"},
        ]


def test_summary_sorts_top_gainers_and_losers():
    service = MarketWatchService(market_data=FakeMarketData())
    service.SUMMARY_UNIVERSE = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]

    payload = service.summary()

    assert payload["top_gainers"][0]["symbol"] == "RELIANCE"
    assert payload["top_losers"][0]["symbol"] == "TCS"


def test_summary_market_breadth_counts_unavailable_separately():
    service = MarketWatchService(market_data=FakeMarketData())
    service.SUMMARY_UNIVERSE = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]

    breadth = service.summary()["market_breadth"]

    assert breadth["advancers"] == 1
    assert breadth["decliners"] == 1
    assert breadth["unchanged"] == 1
    assert breadth["unavailable"] == 1
    assert breadth["total_symbols"] == 4


def test_summary_indices_contain_only_index_rows():
    service = MarketWatchService(market_data=FakeMarketData())
    service.SUMMARY_UNIVERSE = ["RELIANCE", "TCS"]

    indices = service.summary()["indices"]

    assert {row["name"] for row in indices} == {"NIFTY 50", "SENSEX"}
    assert "RELIANCE" not in {row["name"] for row in indices}


def test_summary_fii_dii_source_not_connected():
    service = MarketWatchService(market_data=FakeMarketData())
    service.SUMMARY_UNIVERSE = ["RELIANCE"]

    fii_dii = service.summary()["fii_dii_status"]

    assert fii_dii["status"] == "source_not_connected"
    assert fii_dii["message"] == "FII/DII live data source not connected yet"
