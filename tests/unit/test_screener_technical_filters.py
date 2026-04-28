from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.schemas.screener_schema import ScreenerFilter, ScreenerRunRequest
from app.services.screener.screener_service import ScreenerService


class TechnicalMarketData:
    def __init__(self, mode: str = "breakout", candles_available: bool = True) -> None:
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
        latest = float(frame.iloc[-1]["Close"])
        previous = float(frame.iloc[-2]["Close"])
        return {
            "symbol": symbol,
            "stock_name": symbol,
            "exchange": exchange,
            "latest_price": latest,
            "previous_close": previous,
            "change": latest - previous,
            "change_pct": ((latest - previous) / previous) * 100,
            "open": float(frame.iloc[-1]["Open"]),
            "high": float(frame.iloc[-1]["High"]),
            "low": float(frame.iloc[-1]["Low"]),
            "volume": float(frame.iloc[-1]["Volume"]),
            "week_52_high": float(frame["High"].max()),
            "week_52_low": float(frame["Low"].min()),
            "data_source_badge": "Cached",
            "data_source_note": "Showing cached market data.",
        }

    def _frame(self):
        dates = pd.date_range(end=datetime(2026, 4, 27), periods=220)
        if self.mode == "oversold":
            closes = [300 - (i * 1.0) for i in range(220)]
        elif self.mode == "breakdown":
            closes = [100 + (i * 0.1) for i in range(219)] + [80]
        else:
            closes = [100 + (i * 0.35) for i in range(219)] + [205]
        highs = [value + 2 for value in closes]
        lows = [value - 2 for value in closes]
        if self.mode == "breakout":
            highs[-1] = closes[-1]
            highs[-2] = min(highs[-2], closes[-1] - 5)
        if self.mode == "breakdown":
            lows[-1] = closes[-1]
            lows[-2] = max(lows[-2], closes[-1] + 5)
        return pd.DataFrame(
            {
                "Date": dates,
                "Open": [value - 0.5 for value in closes],
                "High": highs,
                "Low": lows,
                "Close": closes,
                "Volume": [2500] * 200 + [5000] * 20,
            }
        )


def _run(mode: str = "breakout", filters=None, candles_available: bool = True):
    service = ScreenerService(market_data=TechnicalMarketData(mode=mode, candles_available=candles_available))
    return service.run(ScreenerRunRequest(filters=filters or []))


def _expected_frame(mode: str = "breakout"):
    return TechnicalMarketData(mode=mode)._frame()


def test_ema_formula_correct():
    row = _run()["results"][0]
    expected = _expected_frame()["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
    assert row["ema_20"] == round(float(expected), 2)


def test_sma_formula_correct():
    row = _run()["results"][0]
    expected = _expected_frame()["Close"].tail(20).mean()
    assert row["sma_20"] == round(float(expected), 2)


def test_rsi_formula_correct():
    row = _run("breakdown")["results"][0]
    close = _expected_frame("breakdown")["Close"]
    delta = close.diff().dropna()
    gain = delta.clip(lower=0).tail(14).mean()
    loss = (-delta.clip(upper=0)).tail(14).mean()
    expected = 100 - (100 / (1 + (gain / loss)))
    assert row["rsi_14"] == round(float(expected), 2)


def test_macd_formula_correct():
    row = _run()["results"][0]
    close = _expected_frame()["Close"]
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    assert row["macd_line"] == round(float(macd.iloc[-1]), 2)
    assert row["macd_signal"] == round(float(signal.iloc[-1]), 2)
    assert row["macd_histogram"] == round(float((macd - signal).iloc[-1]), 2)


def test_breakout_20d_formula_correct():
    assert _run()["results"][0]["breakout_20d"] is True


def test_breakdown_20d_formula_correct():
    assert _run("breakdown")["results"][0]["breakdown_20d"] is True


def test_trend_score_correct():
    row = _run()["results"][0]
    expected = 0
    expected += 20 if row["ltp"] > row["ema_20"] else 0
    expected += 20 if row["ltp"] > row["ema_50"] else 0
    expected += 20 if row["ema_20"] > row["ema_50"] else 0
    expected += 20 if row["macd_bullish"] else 0
    expected += 20 if 45 <= row["rsi_14"] <= 70 else 0
    assert row["trend_score"] == expected


def test_rsi_oversold_filter_works():
    filters = [ScreenerFilter(category="Technical Indicators", metric="RSI (14)", condition="less_than", value=30)]
    assert len(_run("oversold", filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_ema_bullish_preset_works():
    filters = [
        ScreenerFilter(category="Technical Indicators", metric="Price Above EMA20", condition="is_true", value=True),
        ScreenerFilter(category="Technical Indicators", metric="EMA20 Above EMA50", condition="is_true", value=True),
    ]
    assert len(_run("breakout", filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_macd_bullish_preset_works():
    filters = [ScreenerFilter(category="Technical Indicators", metric="MACD Bullish", condition="is_true", value=True)]
    assert len(_run("breakout", filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_20d_breakout_preset_works():
    filters = [ScreenerFilter(category="Technical Indicators", metric="Breakout 20D", condition="is_true", value=True)]
    assert len(_run("breakout", filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_missing_candle_data_does_not_crash_for_technical_fields():
    row = _run(candles_available=False)["results"][0]
    assert row["ltp"] is not None
    assert row["ema_20"] is None
    assert row["rsi_14"] is None
    assert row["technical_rating"] is None
