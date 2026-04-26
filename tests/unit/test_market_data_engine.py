from datetime import datetime, timedelta

import pandas as pd

from app.services.market_data.engine import MarketDataEngine
from app.services.market_data.providers import MarketDataProvider, SampleMarketDataProvider


class FailingProvider(MarketDataProvider):
    name = "failing"
    label = "Error"

    def search_instruments(self, query, exchange=None, session=None, instrument_type=None):
        raise RuntimeError("provider down")

    def get_quote(self, *, symbol=None, token=None, exchange="NSE", session=None):
        raise RuntimeError("provider down")

    def get_quotes_bulk(self, instruments, session=None):
        raise RuntimeError("provider down")

    def get_candles(self, *, symbol=None, token=None, exchange="NSE", interval, from_date, to_date, session=None):
        raise RuntimeError("provider down")

    def get_indices(self):
        raise RuntimeError("provider down")

    def get_market_status(self):
        raise RuntimeError("provider down")


def test_market_data_engine_falls_back_to_sample_quote(tmp_path):
    engine = MarketDataEngine(primary=FailingProvider(), fallback=SampleMarketDataProvider(), candle_cache_dir=tmp_path)

    quote = engine.get_quote(symbol="RELIANCE", exchange="NSE")

    assert quote["symbol"] == "RELIANCE"
    assert quote["available"] is True
    assert quote["data_source_badge"] == "Sample"


def test_market_data_engine_candle_endpoint_uses_sample_fallback(tmp_path):
    engine = MarketDataEngine(primary=FailingProvider(), fallback=SampleMarketDataProvider(), candle_cache_dir=tmp_path)

    candles = engine.get_candles(
        symbol="RELIANCE",
        exchange="NSE",
        interval="ONE_DAY",
        from_date=datetime.now() - timedelta(days=10),
        to_date=datetime.now(),
    )

    assert not candles["frame"].empty
    assert candles["data_source_badge"] == "Sample"


def test_market_data_engine_reuses_exact_candle_cache(tmp_path):
    class OneShotProvider(SampleMarketDataProvider):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def get_candles(self, **kwargs):
            self.calls += 1
            return pd.DataFrame([{"Date": "2026-04-01", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 10}])

    provider = OneShotProvider()
    engine = MarketDataEngine(primary=provider, fallback=SampleMarketDataProvider(), candle_cache_dir=tmp_path)
    kwargs = {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "interval": "ONE_DAY",
        "from_date": datetime(2026, 4, 1),
        "to_date": datetime(2026, 4, 2),
    }

    first = engine.get_candles(**kwargs)
    second = engine.get_candles(**kwargs)

    assert provider.calls == 1
    assert first["frame"].iloc[0]["Close"] == 2
    assert second["is_cached"] is True


def test_market_data_engine_instrument_search_fallback(tmp_path):
    engine = MarketDataEngine(primary=FailingProvider(), fallback=SampleMarketDataProvider(), candle_cache_dir=tmp_path)

    result = engine.search_instruments("rel", exchange="NSE")

    assert result["items"][0]["symbol"] == "RELIANCE"
    assert result["data_source_badge"] == "Sample"
