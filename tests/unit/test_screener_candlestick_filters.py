from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.schemas.screener_schema import ScreenerFilter, ScreenerRunRequest
from app.services.screener.screener_service import ScreenerService


class CandlestickMarketData:
    def __init__(self, mode: str = "doji", candles_available: bool = True) -> None:
        self.mode = mode
        self.candles_available = candles_available

    def get_quotes_bulk(self, instruments, session=None):
        return {"items": [self._quote(item["symbol"], item.get("exchange", "NSE")) for item in instruments]}

    def get_candles(self, **kwargs):
        if not self.candles_available:
            raise RuntimeError("candles unavailable")
        return {"frame": self._frame(), "data_source_badge": "Cached"}

    def _quote(self, symbol: str, exchange: str):
        frame = self._frame()
        latest = frame.iloc[-1]
        previous = frame.iloc[-2]
        return {
            "symbol": symbol,
            "stock_name": symbol,
            "exchange": exchange,
            "latest_price": float(latest["Close"]),
            "previous_close": float(previous["Close"]),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "volume": float(latest["Volume"]),
            "week_52_high": float(frame["High"].max()),
            "week_52_low": float(frame["Low"].min()),
            "data_source_badge": "Cached",
            "data_source_note": "Showing cached market data.",
        }

    def _frame(self):
        dates = pd.date_range(end=datetime(2026, 4, 27), periods=220)
        rows = [{"Open": 100 + i * 0.1, "High": 103 + i * 0.1, "Low": 98 + i * 0.1, "Close": 101 + i * 0.1, "Volume": 2500} for i in range(218)]
        previous, current = self._latest_pair()
        rows.extend([previous, current])
        frame = pd.DataFrame(rows)
        frame.insert(0, "Date", dates)
        return frame

    def _latest_pair(self):
        pairs = {
            "doji": (self._candle(100, 105, 95, 102), self._candle(100, 110, 90, 101)),
            "hammer": (self._candle(100, 105, 95, 102), self._candle(100, 103, 94, 102)),
            "shooting_star": (self._candle(100, 105, 95, 102), self._candle(100, 108, 99, 102)),
            "bullish_engulfing": (self._candle(105, 106, 99, 100), self._candle(99, 107, 98, 106)),
            "bearish_engulfing": (self._candle(100, 106, 99, 105), self._candle(106, 107, 98, 99)),
            "inside_bar": (self._candle(100, 110, 90, 104), self._candle(101, 105, 95, 103)),
            "outside_bar": (self._candle(100, 105, 95, 102), self._candle(101, 110, 90, 103)),
            "gap_up": (self._candle(100, 105, 95, 102), self._candle(106, 112, 105, 110)),
            "gap_down": (self._candle(100, 105, 95, 102), self._candle(94, 95, 88, 90)),
            "strong_bullish": (self._candle(100, 105, 95, 102), self._candle(100, 112, 99, 110)),
            "strong_bearish": (self._candle(100, 105, 95, 102), self._candle(110, 111, 98, 100)),
        }
        return pairs[self.mode]

    def _candle(self, open_price, high, low, close):
        return {"Open": open_price, "High": high, "Low": low, "Close": close, "Volume": 5000}


def _run(mode: str, filters=None, candles_available: bool = True):
    service = ScreenerService(market_data=CandlestickMarketData(mode=mode, candles_available=candles_available))
    return service.run(ScreenerRunRequest(filters=filters or []))


def test_doji_formula_correct():
    row = _run("doji")["results"][0]
    assert row["doji"] is True
    assert "Doji" in row["detected_patterns"]


def test_hammer_formula_correct():
    row = _run("hammer")["results"][0]
    assert row["hammer"] is True


def test_shooting_star_formula_correct():
    row = _run("shooting_star")["results"][0]
    assert row["shooting_star"] is True


def test_bullish_engulfing_formula_correct():
    row = _run("bullish_engulfing")["results"][0]
    assert row["bullish_engulfing"] is True


def test_bearish_engulfing_formula_correct():
    row = _run("bearish_engulfing")["results"][0]
    assert row["bearish_engulfing"] is True


def test_inside_bar_formula_correct():
    row = _run("inside_bar")["results"][0]
    assert row["inside_bar"] is True


def test_gap_up_gap_down_formulas_correct():
    assert _run("gap_up")["results"][0]["gap_up"] is True
    assert _run("gap_down")["results"][0]["gap_down"] is True


def test_strong_bullish_bearish_candle_formulas_correct():
    assert _run("strong_bullish")["results"][0]["strong_bullish_candle"] is True
    assert _run("strong_bearish")["results"][0]["strong_bearish_candle"] is True


def test_candlestick_bias_correct():
    assert _run("bullish_engulfing")["results"][0]["candlestick_bias"] == "Bullish"
    assert _run("bearish_engulfing")["results"][0]["candlestick_bias"] == "Bearish"


def test_bullish_candles_preset_works():
    filters = [ScreenerFilter(category="Candlestick Patterns", metric="Candlestick Bias", condition="equal_to", value="Bullish")]
    assert len(_run("bullish_engulfing", filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_bearish_candles_preset_works():
    filters = [ScreenerFilter(category="Candlestick Patterns", metric="Candlestick Bias", condition="equal_to", value="Bearish")]
    assert len(_run("bearish_engulfing", filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_missing_candle_data_does_not_crash_for_patterns():
    row = _run("doji", candles_available=False)["results"][0]
    assert row["ltp"] is not None
    assert row["doji"] is None
    assert row["detected_patterns"] == []
    assert row["candlestick_bias"] == "Unavailable"
    assert row["pattern_status"] == "Unavailable"
