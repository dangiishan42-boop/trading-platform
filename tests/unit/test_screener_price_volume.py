from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.schemas.screener_schema import ScreenerFilter, ScreenerRunRequest
from app.services.screener.screener_service import ScreenerService


class StaticMarketData:
    def __init__(self, candles_available: bool = True) -> None:
        self.candles_available = candles_available

    def get_quotes_bulk(self, instruments, session=None):
        return {"items": [self._quote(item["symbol"], item.get("exchange", "NSE")) for item in instruments]}

    def get_candles(self, **kwargs):
        if not self.candles_available:
            raise RuntimeError("candles unavailable")
        return {"frame": self._frame(), "data_source_badge": "Cached"}

    def _quote(self, symbol: str, exchange: str):
        return {
            "symbol": symbol,
            "stock_name": symbol,
            "exchange": exchange,
            "latest_price": 110,
            "previous_close": 100,
            "change": 10,
            "change_pct": 10,
            "open": 103,
            "high": 115,
            "low": 95,
            "volume": 5000,
            "week_52_high": 120,
            "week_52_low": 80,
            "data_source_badge": "Cached",
            "data_source_note": "Showing cached market data.",
        }

    def _frame(self):
        dates = pd.date_range(end=datetime(2026, 4, 27), periods=20)
        return pd.DataFrame(
            {
                "Date": dates,
                "Open": [100] * 20,
                "High": [118] * 19 + [115],
                "Low": [82] * 19 + [95],
                "Close": [100] * 19 + [110],
                "Volume": [2500] * 20,
            }
        )


def _service(candles_available: bool = True) -> ScreenerService:
    return ScreenerService(market_data=StaticMarketData(candles_available=candles_available))


def _run(service: ScreenerService, filters=None):
    return service.run(ScreenerRunRequest(filters=filters or []))


def test_percent_change_formula_correct():
    row = _run(_service())["results"][0]
    assert row["point_change"] == 10
    assert row["percent_change"] == 10


def test_relative_volume_formula_correct():
    row = _run(_service())["results"][0]
    assert row["avg_volume_20d"] == 2500
    assert row["relative_volume"] == 2


def test_52w_high_low_distance_formulas_correct():
    row = _run(_service())["results"][0]
    assert row["distance_from_52w_high_pct"] == -8.33
    assert row["distance_from_52w_low_pct"] == 37.5


def test_gap_up_down_formulas_correct():
    row = _run(_service())["results"][0]
    assert row["gap_up_pct"] == 3
    assert row["gap_down_pct"] == 3


def test_turnover_formula_correct():
    row = _run(_service())["results"][0]
    assert row["turnover"] == 550000


def test_filter_greater_than_works():
    filters = [ScreenerFilter(category="Price & Volume", metric="LTP", condition="greater_than", value=105)]
    assert len(_run(_service(), filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)

    filters = [ScreenerFilter(category="Price & Volume", metric="LTP", condition="greater_than", value=200)]
    assert len(_run(_service(), filters)["results"]) == 0


def test_filter_between_works():
    filters = [ScreenerFilter(category="Price & Volume", metric="% Change", condition="between", value=9, value_2=11)]
    assert len(_run(_service(), filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_volume_spike_preset_works():
    filters = [ScreenerFilter(category="Price & Volume", metric="Volume Spike", condition="is_true", value=True)]
    assert len(_run(_service(), filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_near_52w_high_preset_works():
    filters = [ScreenerFilter(category="Price & Volume", metric="52W High Distance %", condition="greater_than", value=-10)]
    assert len(_run(_service(), filters)["results"]) == len(ScreenerService.SAMPLE_UNIVERSE)


def test_missing_candle_data_does_not_crash():
    row = _run(_service(candles_available=False))["results"][0]
    assert row["ltp"] == 110
    assert row["avg_volume_20d"] is None
    assert row["relative_volume"] is None
