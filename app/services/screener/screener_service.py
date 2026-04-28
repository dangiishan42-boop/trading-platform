from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import pandas as pd

from app.schemas.screener_schema import ScreenerRunRequest, ScreenerSavedScreenCreate
from app.services.data.instrument_master_service import InstrumentMasterService
from app.services.market_data.engine import MarketDataEngine, get_market_data_engine
from app.services.screener.formula_engine import evaluate_formula, validate_formula


class ScreenerService:
    DATA_SOURCE_NOTE = (
        "Screener v1 is running on a safe local preview universe. "
        "Connect an exchange-wide instrument and fundamentals source before treating scans as full NSE/BSE coverage."
    )

    UNIVERSES = ["Indian Equities", "NIFTY 50", "NIFTY 100", "NIFTY 500", "F&O Stocks", "All NSE", "All BSE"]
    EXCHANGES = ["NSE", "BSE", "NSE + BSE"]
    CATEGORIES = [
        "Overview",
        "Price & Volume",
        "Fundamentals",
        "Technical Indicators",
        "Candlestick Patterns",
        "Performance",
        "Valuation",
        "Profitability",
        "Growth",
        "Dividend",
        "Liquidity",
        "Analyst Estimates",
        "Custom Formulas",
    ]
    METRICS = {
        "Price": ["LTP", "% Change", "Volume", "Avg Volume 20D", "Relative Volume", "Volume Spike", "52W High Distance %", "52W Low Distance %", "Gap Up %", "Gap Down %", "Day Range %", "Turnover", "Market Cap"],
        "Price & Volume": ["LTP", "% Change", "Volume", "Avg Volume 20D", "Relative Volume", "Volume Spike", "52W High Distance %", "52W Low Distance %", "Gap Up %", "Gap Down %", "Day Range %", "Turnover"],
        "Fundamentals": ["P/E Ratio", "P/B Ratio", "ROE", "ROCE", "EPS Growth", "Sales Growth", "Debt to Equity", "Dividend Yield"],
        "Technical Indicators": ["RSI (14)", "RSI Oversold", "RSI Overbought", "Price Above EMA20", "Price Above EMA50", "Price Above EMA200", "EMA20 Above EMA50", "EMA50 Above EMA200", "MACD Bullish", "MACD Bearish", "Breakout 20D", "Breakdown 20D", "52W Breakout", "52W Breakdown", "Volume Confirmed Breakout", "Trend Score", "Technical Rating"],
        "Technicals": ["RSI (14)", "RSI Oversold", "RSI Overbought", "Price Above EMA20", "Price Above EMA50", "Price Above EMA200", "EMA20 Above EMA50", "EMA50 Above EMA200", "MACD Bullish", "MACD Bearish", "Breakout 20D", "Breakdown 20D", "52W Breakout", "52W Breakdown", "Volume Confirmed Breakout", "Trend Score", "Technical Rating"],
        "Candlestick Patterns": ["Doji", "Hammer", "Shooting Star", "Bullish Engulfing", "Bearish Engulfing", "Inside Bar", "Outside Bar", "Bullish Marubozu", "Bearish Marubozu", "Gap Up", "Gap Down", "Strong Bullish Candle", "Strong Bearish Candle", "Candlestick Bias"],
    }
    CONDITIONS = ["Greater Than", "Less Than", "Between", "Equal To", "Is True", "Is False"]
    SORT_OPTIONS = ["Market Cap", "% Change", "Volume", "Relative Volume", "Turnover", "Composite Score", "P/E", "ROE", "RSI"]
    MAX_FNO_UNIVERSE = 100
    VOLUME_SPIKE_THRESHOLD = 2.0
    HIGH_TURNOVER_THRESHOLD = 1_000_000_000
    QUICK_FILTERS = [
        {"name": "Volume Spike", "filters": [{"category": "Price & Volume", "metric": "Volume Spike", "condition": "Is True", "value": True}]},
        {"name": "Price Up 3%", "filters": [{"category": "Price & Volume", "metric": "% Change", "condition": "Greater Than", "value": 3}]},
        {"name": "Price Down 3%", "filters": [{"category": "Price & Volume", "metric": "% Change", "condition": "Less Than", "value": -3}]},
        {"name": "Near 52W High", "filters": [{"category": "Price & Volume", "metric": "52W High Distance %", "condition": "Greater Than", "value": -5}]},
        {"name": "Near 52W Low", "filters": [{"category": "Price & Volume", "metric": "52W Low Distance %", "condition": "Less Than", "value": 5}]},
        {"name": "Gap Up", "filters": [{"category": "Price & Volume", "metric": "Gap Up %", "condition": "Greater Than", "value": 1}]},
        {"name": "Gap Down", "filters": [{"category": "Price & Volume", "metric": "Gap Down %", "condition": "Less Than", "value": -1}]},
        {"name": "High Turnover", "filters": [{"category": "Price & Volume", "metric": "Turnover", "condition": "Greater Than", "value": HIGH_TURNOVER_THRESHOLD}]},
        {"name": "RSI Oversold", "filters": [{"category": "Technical Indicators", "metric": "RSI (14)", "condition": "Less Than", "value": 30}]},
        {"name": "RSI Overbought", "filters": [{"category": "Technical Indicators", "metric": "RSI (14)", "condition": "Greater Than", "value": 70}]},
        {"name": "EMA Bullish", "filters": [{"category": "Technical Indicators", "metric": "Price Above EMA20", "condition": "Is True", "value": True}, {"category": "Technical Indicators", "metric": "EMA20 Above EMA50", "condition": "Is True", "value": True, "logical": "AND"}]},
        {"name": "MACD Bullish", "filters": [{"category": "Technical Indicators", "metric": "MACD Bullish", "condition": "Is True", "value": True}]},
        {"name": "20D Breakout", "filters": [{"category": "Technical Indicators", "metric": "Breakout 20D", "condition": "Is True", "value": True}]},
        {"name": "20D Breakdown", "filters": [{"category": "Technical Indicators", "metric": "Breakdown 20D", "condition": "Is True", "value": True}]},
        {"name": "52W Breakout", "filters": [{"category": "Technical Indicators", "metric": "52W Breakout", "condition": "Is True", "value": True}]},
        {"name": "Volume Breakout", "filters": [{"category": "Technical Indicators", "metric": "Volume Confirmed Breakout", "condition": "Is True", "value": True}]},
        {"name": "Strong Technical", "filters": [{"category": "Technical Indicators", "metric": "Trend Score", "condition": "Between", "value": 80, "value_2": 100}]},
        {"name": "Bullish Candles", "filters": [{"category": "Candlestick Patterns", "metric": "Candlestick Bias", "condition": "Equal To", "value": "Bullish"}]},
        {"name": "Bearish Candles", "filters": [{"category": "Candlestick Patterns", "metric": "Candlestick Bias", "condition": "Equal To", "value": "Bearish"}]},
        {"name": "Reversal Candles", "filters": [{"category": "Candlestick Patterns", "metric": "Hammer", "condition": "Is True", "value": True}, {"category": "Candlestick Patterns", "metric": "Shooting Star", "condition": "Is True", "value": True, "logical": "OR"}, {"category": "Candlestick Patterns", "metric": "Bullish Engulfing", "condition": "Is True", "value": True, "logical": "OR"}, {"category": "Candlestick Patterns", "metric": "Bearish Engulfing", "condition": "Is True", "value": True, "logical": "OR"}]},
        {"name": "Breakout Candles", "filters": [{"category": "Candlestick Patterns", "metric": "Gap Up", "condition": "Is True", "value": True}, {"category": "Candlestick Patterns", "metric": "Strong Bullish Candle", "condition": "Is True", "value": True, "logical": "OR"}]},
        {"name": "Breakdown Candles", "filters": [{"category": "Candlestick Patterns", "metric": "Gap Down", "condition": "Is True", "value": True}, {"category": "Candlestick Patterns", "metric": "Strong Bearish Candle", "condition": "Is True", "value": True, "logical": "OR"}]},
        {"name": "Doji / Indecision", "filters": [{"category": "Candlestick Patterns", "metric": "Doji", "condition": "Is True", "value": True}]},
    ]
    FORMULA_PRESETS = [
        {"name": "Momentum Breakout", "expression": "Breakout20D == true AND RelativeVolume > 1.5 AND TrendScore >= 60"},
        {"name": "Oversold Reversal", "expression": "RSI14 < 30 AND (Hammer == true OR BullishEngulfing == true)"},
        {"name": "Strong Trend", "expression": "PriceAboveEMA50 == true AND EMA20AboveEMA50 == true AND MACD_Bullish == true"},
        {"name": "Volume Burst", "expression": "RelativeVolume > 2 AND PercentChange > 1"},
        {"name": "Bearish Breakdown", "expression": "Breakdown20D == true AND RelativeVolume > 1.5 AND TrendScore < 40"},
        {"name": "Candlestick Reversal", "expression": "Hammer == true OR ShootingStar == true OR BullishEngulfing == true OR BearishEngulfing == true"},
    ]

    _saved_screens: list[dict[str, Any]] = [
        {"id": "sample-growth-low-pe", "name": "High Growth Low PE", "config": {}},
        {"id": "sample-quality", "name": "Quality Compounders", "config": {}},
        {"id": "sample-breakout-volume", "name": "Breakout with Volume", "config": {}},
        {"id": "sample-large-cap-value", "name": "Undervalued Large Caps", "config": {}},
        {"id": "sample-custom", "name": "My Custom Screen", "config": {}},
    ]

    SAMPLE_UNIVERSE: list[dict[str, Any]] = [
        {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Energy", "ltp": 2928.4, "change_pct": 1.24, "volume": 6250000, "market_cap_cr": 1980000, "pe_ttm": 24.6, "roe_pct": 15.8, "eps_growth_yoy_pct": 13.5, "rsi_14": 61.2, "debt_equity": 0.42, "exchange": "NSE", "price_above_ema200": True},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Financial Services", "ltp": 1548.2, "change_pct": -0.42, "volume": 11400000, "market_cap_cr": 1175000, "pe_ttm": 18.4, "roe_pct": 17.2, "eps_growth_yoy_pct": 16.1, "rsi_14": 48.6, "debt_equity": 0.0, "exchange": "NSE", "price_above_ema200": True},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Financial Services", "ltp": 1108.7, "change_pct": 0.78, "volume": 8725000, "market_cap_cr": 781000, "pe_ttm": 19.7, "roe_pct": 18.9, "eps_growth_yoy_pct": 18.4, "rsi_14": 57.7, "debt_equity": 0.0, "exchange": "NSE", "price_above_ema200": True},
        {"symbol": "INFY", "name": "Infosys", "sector": "IT", "ltp": 1432.5, "change_pct": 0.33, "volume": 4850000, "market_cap_cr": 594000, "pe_ttm": 22.8, "roe_pct": 31.1, "eps_growth_yoy_pct": 9.2, "rsi_14": 54.1, "debt_equity": 0.08, "exchange": "NSE", "price_above_ema200": False},
        {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT", "ltp": 3875.0, "change_pct": -0.18, "volume": 1850000, "market_cap_cr": 1402000, "pe_ttm": 29.4, "roe_pct": 48.5, "eps_growth_yoy_pct": 8.7, "rsi_14": 63.8, "debt_equity": 0.07, "exchange": "NSE", "price_above_ema200": True},
        {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Industrials", "ltp": 3590.8, "change_pct": 1.62, "volume": 1420000, "market_cap_cr": 493000, "pe_ttm": 31.2, "roe_pct": 14.8, "eps_growth_yoy_pct": 21.3, "rsi_14": 67.4, "debt_equity": 0.58, "exchange": "NSE", "price_above_ema200": True},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG", "ltp": 2240.6, "change_pct": -0.74, "volume": 1020000, "market_cap_cr": 526000, "pe_ttm": 50.1, "roe_pct": 20.7, "eps_growth_yoy_pct": 5.4, "rsi_14": 43.5, "debt_equity": 0.04, "exchange": "NSE", "price_above_ema200": False},
        {"symbol": "ITC", "name": "ITC", "sector": "FMCG", "ltp": 431.2, "change_pct": 0.91, "volume": 14650000, "market_cap_cr": 538000, "pe_ttm": 27.8, "roe_pct": 28.4, "eps_growth_yoy_pct": 12.2, "rsi_14": 58.2, "debt_equity": 0.01, "exchange": "NSE", "price_above_ema200": True},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Financial Services", "ltp": 763.4, "change_pct": 2.08, "volume": 19200000, "market_cap_cr": 681000, "pe_ttm": 10.4, "roe_pct": 16.6, "eps_growth_yoy_pct": 19.8, "rsi_14": 69.2, "debt_equity": 0.0, "exchange": "NSE", "price_above_ema200": True},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Financial Services", "ltp": 6842.0, "change_pct": -1.06, "volume": 980000, "market_cap_cr": 424000, "pe_ttm": 28.9, "roe_pct": 21.5, "eps_growth_yoy_pct": 24.6, "rsi_14": 46.8, "debt_equity": 3.72, "exchange": "NSE", "price_above_ema200": False},
    ]

    METRIC_FIELDS = {
        "LTP": "ltp",
        "% Change": "percent_change",
        "Point Change": "point_change",
        "Volume": "volume",
        "Avg Volume 20D": "avg_volume_20d",
        "Average Volume 20D": "avg_volume_20d",
        "Relative Volume": "relative_volume",
        "Volume Spike": "volume_spike",
        "52W High Distance": "distance_from_52w_high_pct",
        "52W High Distance %": "distance_from_52w_high_pct",
        "52W Low Distance": "distance_from_52w_low_pct",
        "52W Low Distance %": "distance_from_52w_low_pct",
        "Gap Up %": "gap_up_pct",
        "Gap Down %": "gap_down_pct",
        "Day Range %": "day_range_pct",
        "Turnover": "turnover",
        "Market Cap": "market_cap_cr",
        "Market Cap (₹ Cr)": "market_cap_cr",
        "P/E Ratio": "pe_ttm",
        "P/E Ratio (TTM)": "pe_ttm",
        "ROE": "roe_pct",
        "ROE (%)": "roe_pct",
        "EPS Growth": "eps_growth_yoy_pct",
        "EPS Growth YoY (%)": "eps_growth_yoy_pct",
        "EMA 20": "ema_20",
        "EMA 50": "ema_50",
        "EMA 200": "ema_200",
        "SMA 20": "sma_20",
        "SMA 50": "sma_50",
        "SMA 200": "sma_200",
        "RSI": "rsi_14",
        "RSI (14)": "rsi_14",
        "RSI Oversold": "rsi_oversold",
        "RSI Overbought": "rsi_overbought",
        "RSI Status": "rsi_status",
        "Price Above EMA20": "price_above_ema20",
        "Price Above EMA50": "price_above_ema50",
        "Price Above EMA200": "price_above_ema200",
        "EMA20 Above EMA50": "ema20_above_ema50",
        "EMA50 Above EMA200": "ema50_above_ema200",
        "Price Above SMA20": "price_above_sma20",
        "Price Above SMA50": "price_above_sma50",
        "Price Above SMA200": "price_above_sma200",
        "MACD": "macd_line",
        "MACD Line": "macd_line",
        "MACD Signal": "macd_signal",
        "MACD Histogram": "macd_histogram",
        "MACD Bullish": "macd_bullish",
        "MACD Bearish": "macd_bearish",
        "Breakout 20D": "breakout_20d",
        "Breakdown 20D": "breakdown_20d",
        "Breakout 52W": "breakout_52w",
        "52W Breakout": "breakout_52w",
        "Breakdown 52W": "breakdown_52w",
        "52W Breakdown": "breakdown_52w",
        "Volume Confirmed Breakout": "volume_confirmed_breakout",
        "Trend Score": "trend_score",
        "Technical Rating": "technical_rating",
        "Doji": "doji",
        "Hammer": "hammer",
        "Shooting Star": "shooting_star",
        "Bullish Engulfing": "bullish_engulfing",
        "Bearish Engulfing": "bearish_engulfing",
        "Inside Bar": "inside_bar",
        "Outside Bar": "outside_bar",
        "Bullish Marubozu": "bullish_marubozu",
        "Bearish Marubozu": "bearish_marubozu",
        "Gap Up": "gap_up",
        "Gap Down": "gap_down",
        "Strong Bullish Candle": "strong_bullish_candle",
        "Strong Bearish Candle": "strong_bearish_candle",
        "Candlestick Bias": "candlestick_bias",
        "Debt to Equity": "debt_equity",
        "Volume (20D Avg)": "avg_volume_20d",
        "Price Above 200 EMA": "price_above_ema200",
        "Price Above EMA200": "price_above_ema200",
    }
    SORT_FIELDS = {
        "Market Cap": "market_cap_cr",
        "% Change": "change_pct",
        "Volume": "volume",
        "Relative Volume": "relative_volume",
        "Turnover": "turnover",
        "Composite Score": "composite_score",
        "P/E": "pe_ttm",
        "ROE": "roe_pct",
        "RSI": "rsi_14",
        "Trend Score": "trend_score",
    }

    def __init__(self, market_data: MarketDataEngine | None = None) -> None:
        self.market_data = market_data or get_market_data_engine()

    def capabilities(self) -> dict[str, Any]:
        return {
            "universes": self.UNIVERSES,
            "exchanges": self.EXCHANGES,
            "categories": self.CATEGORIES,
            "metrics": self.METRICS,
            "conditions": self.CONDITIONS,
            "logical": ["AND", "OR"],
            "sort_options": self.SORT_OPTIONS,
            "quick_filters": self.QUICK_FILTERS,
            "formula_presets": self.FORMULA_PRESETS,
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def run(self, request: ScreenerRunRequest, session=None) -> dict[str, Any]:
        rows, source_note = self._market_rows()
        if request.universe == "F&O Stocks":
            rows, source_note = self._fno_market_rows(session)
        if rows and all(row.get("ema_20") is None and row.get("rsi_14") is None and row.get("macd_line") is None for row in rows):
            source_note = f"{source_note} Technical data unavailable for this scan; candle-derived fields are shown as --."
        for row in rows:
            row["composite_score"] = self._composite_score(row)
            row["formula_match"] = None
        filtered = [row for row in rows if self._matches_filters(row, request.filters)]
        formula_validation = None
        formula_errors: list[str] = []
        formula_matched_count: int | None = None
        if request.custom_formula_enabled:
            validation = validate_formula(request.custom_formula_expression or "")
            formula_validation = {
                "valid": validation.valid,
                "normalized_expression": validation.normalized_expression,
                "errors": validation.errors,
                "referenced_metrics": validation.referenced_metrics,
            }
            formula_errors = validation.errors
            if validation.valid:
                formula_filtered = []
                for row in filtered:
                    matched = evaluate_formula(validation.normalized_expression, row)
                    row["formula_match"] = matched
                    if matched:
                        formula_filtered.append(row)
                filtered = formula_filtered
                formula_matched_count = len(filtered)
            else:
                filtered = []
                formula_matched_count = 0
        sort_field = self.SORT_FIELDS.get(request.sort_by, "market_cap_cr")
        filtered.sort(key=lambda item: item.get(sort_field) or 0, reverse=request.sort_direction == "desc")
        return {
            "results": filtered,
            "summary": self._summary(filtered, request, universe_total=len(rows)),
            "distributions": self._distributions(filtered),
            "sector_breakdown": self._sector_breakdown(filtered),
            "saved_screens": self.list_saved_screens(),
            "data_source_note": source_note,
            "formula_validation": formula_validation,
            "formula_matched_count": formula_matched_count,
            "formula_errors": formula_errors,
        }

    def list_saved_screens(self) -> list[dict[str, Any]]:
        return list(self._saved_screens)

    def save_screen(self, payload: ScreenerSavedScreenCreate) -> dict[str, Any]:
        row = {"id": str(uuid4()), "name": payload.name, "config": payload.config}
        self._saved_screens.append(row)
        return row

    def delete_screen(self, screen_id: str) -> dict[str, Any]:
        before = len(self._saved_screens)
        self._saved_screens = [row for row in self._saved_screens if row["id"] != screen_id]
        return {"deleted": len(self._saved_screens) != before, "id": screen_id}

    def _matches_filters(self, row: dict[str, Any], filters: list[Any]) -> bool:
        if not filters:
            return True
        result: bool | None = None
        for item in filters:
            current = self._matches_filter(row, item)
            if result is None:
                result = current
            elif item.logical == "OR":
                result = result or current
            else:
                result = result and current
        return bool(result)

    def _matches_filter(self, row: dict[str, Any], item: Any) -> bool:
        field = self.METRIC_FIELDS.get(item.metric)
        if not field:
            return True
        condition = self._normalize_condition(item.condition)
        actual = row.get(field)
        expected = self._coerce(item.value)
        expected_2 = self._coerce(item.value_2)
        if condition == "Is True":
            return actual is True
        if condition == "Is False":
            return actual is False
        if actual is None or expected is None:
            return False
        if condition == "Greater Than":
            return float(actual) > float(expected)
        if condition == "Less Than":
            return float(actual) < float(expected)
        if condition == "Between":
            high = expected_2 if expected_2 is not None else expected
            return float(expected) <= float(actual) <= float(high)
        if condition == "Equal To":
            if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                return float(actual) == float(expected)
            return str(actual).lower() == str(expected).lower()
        return True

    def _summary(self, rows: list[dict[str, Any]], request: ScreenerRunRequest, universe_total: int | None = None) -> dict[str, Any]:
        total_volume = sum(int(row.get("volume") or 0) for row in rows)
        avg_market_cap = self._avg(rows, "market_cap_cr")
        avg_change = self._avg(rows, "change_pct")
        return {
            "matches": len(rows),
            "total_stocks": universe_total if universe_total is not None else len(self.SAMPLE_UNIVERSE),
            "avg_market_cap_cr": round(avg_market_cap, 2),
            "avg_change_pct": round(avg_change, 2),
            "total_volume": total_volume,
            "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_ms": 42,
            "status": "Completed",
            "universe": request.universe,
            "exchange": request.exchange,
            "custom_formula_enabled": request.custom_formula_enabled,
            "custom_formula_name": request.custom_formula_name,
        }

    def _distributions(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "filters": [
                {"label": "M.Cap", "value": 88},
                {"label": "Valuation", "value": 64},
                {"label": "Growth", "value": 71},
                {"label": "Momentum", "value": 58},
                {"label": "Profitability", "value": 76},
                {"label": "Liquidity", "value": 92},
                {"label": "Technicals", "value": 69},
            ],
            "market_cap": [
                {"label": "> ₹50,000 Cr", "value": sum(1 for row in rows if row["market_cap_cr"] > 50000)},
                {"label": "₹10,000 - ₹50,000 Cr", "value": sum(1 for row in rows if 10000 <= row["market_cap_cr"] <= 50000)},
                {"label": "₹2,000 - ₹10,000 Cr", "value": sum(1 for row in rows if 2000 <= row["market_cap_cr"] < 10000)},
                {"label": "₹500 - ₹2,000 Cr", "value": sum(1 for row in rows if 500 <= row["market_cap_cr"] < 2000)},
                {"label": "< ₹500 Cr", "value": sum(1 for row in rows if row["market_cap_cr"] < 500)},
            ],
            "pe": self._histogram(rows, "pe_ttm", [15, 25, 35, 45]),
            "roe": self._histogram(rows, "roe_pct", [15, 20, 30, 40]),
            "top_market_cap": sorted(rows, key=lambda row: row["market_cap_cr"], reverse=True)[:5],
        }

    def _sector_breakdown(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["sector"]] = counts.get(row["sector"], 0) + 1
        return [{"label": sector, "value": value} for sector, value in sorted(counts.items(), key=lambda item: item[1], reverse=True)]

    def _histogram(self, rows: list[dict[str, Any]], field: str, buckets: list[float]) -> list[dict[str, Any]]:
        labels = [f"< {buckets[0]}"] + [f"{buckets[i - 1]}-{buckets[i]}" for i in range(1, len(buckets))] + [f"> {buckets[-1]}"]
        counts = [0 for _ in labels]
        for row in rows:
            value = float(row.get(field) or 0)
            index = 0
            while index < len(buckets) and value >= buckets[index]:
                index += 1
            counts[index] += 1
        return [{"label": label, "value": counts[index]} for index, label in enumerate(labels)]

    def _avg(self, rows: list[dict[str, Any]], field: str) -> float:
        if not rows:
            return 0.0
        values = [float(row[field]) for row in rows if row.get(field) is not None]
        return sum(values) / len(values) if values else 0.0

    def _coerce(self, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            return value.strip().lower() == "true"
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    def _normalize_condition(self, value: Any) -> str:
        aliases = {
            "greater_than": "Greater Than",
            "greater than": "Greater Than",
            "less_than": "Less Than",
            "less than": "Less Than",
            "between": "Between",
            "equal_to": "Equal To",
            "equal to": "Equal To",
            "is_true": "Is True",
            "is true": "Is True",
            "is_false": "Is False",
            "is false": "Is False",
        }
        text = str(value or "").strip()
        return aliases.get(text.lower(), text)

    def _market_rows(self) -> tuple[list[dict[str, Any]], str]:
        rows = [row.copy() for row in self.SAMPLE_UNIVERSE]
        try:
            quote_rows = self.market_data.get_quotes_bulk(
                [{"symbol": row["symbol"], "exchange": row["exchange"]} for row in rows]
            )["items"]
        except Exception as exc:
            return [self._with_sample_price_volume(row) for row in rows], f"{self.DATA_SOURCE_NOTE} Quote refresh unavailable: {exc}. Sample fallback is active."

        source_note = self.DATA_SOURCE_NOTE
        for row, quote in zip(rows, quote_rows):
            candle_data = self._daily_candles(row, quote)
            row.update(self._price_volume_metrics(row, quote, candle_data))
            row.update(self._technical_metrics(row, candle_data))
            row.update(self._candlestick_metrics(candle_data))
            if quote.get("data_source_note"):
                source_note = quote["data_source_note"]
        return rows, source_note

    def _fno_market_rows(self, session=None) -> tuple[list[dict[str, Any]], str]:
        note = (
            "F&O universe is synced from Angel instrument master. Historical availability may be limited "
            "to active/live contracts depending on provider."
        )
        if session is None:
            return [self._with_sample_price_volume(row.copy()) for row in self.SAMPLE_UNIVERSE if row.get("is_fno", True)], f"{note} Sample fallback is active."
        payload = InstrumentMasterService().fno_underlyings(session, limit=1000)
        underlyings = payload["items"][: self.MAX_FNO_UNIVERSE]
        if payload["source"] != "Angel Instrument Master":
            return [self._with_sample_price_volume(row.copy()) for row in self.SAMPLE_UNIVERSE if row.get("is_fno", True)], f"{payload.get('message') or note} Source: {payload['source']}. Sample fallback is active."

        sample_by_symbol = {row["symbol"]: row for row in self.SAMPLE_UNIVERSE}
        rows: list[dict[str, Any]] = []
        for item in underlyings:
            sample = sample_by_symbol.get(item.symbol, {})
            rows.append(
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    "sector": sample.get("sector", "Unknown"),
                    "ltp": float(sample.get("ltp", 0)),
                    "change_pct": float(sample.get("change_pct", 0)),
                    "volume": int(sample.get("volume", 0)),
                    "market_cap_cr": float(sample.get("market_cap_cr", 0)),
                    "pe_ttm": float(sample.get("pe_ttm", 0)),
                    "roe_pct": float(sample.get("roe_pct", 0)),
                    "eps_growth_yoy_pct": float(sample.get("eps_growth_yoy_pct", 0)),
                    "rsi_14": float(sample.get("rsi_14", 50)),
                    "debt_equity": float(sample.get("debt_equity", 0)),
                    "exchange": item.exchange,
                    "price_above_ema200": bool(sample.get("price_above_ema200", False)),
                    "is_fno": True,
                }
            )
        rows, source_note = self._refresh_price_volume_rows(rows, session=session)
        return rows, f"{note} {source_note}" if source_note else note

    def _refresh_price_volume_rows(self, rows: list[dict[str, Any]], session=None) -> tuple[list[dict[str, Any]], str]:
        try:
            quote_rows = self.market_data.get_quotes_bulk(
                [{"symbol": row["symbol"], "exchange": row["exchange"]} for row in rows],
                session=session,
            )["items"]
        except Exception as exc:
            return [self._with_sample_price_volume(row.copy()) for row in rows], f"{self.DATA_SOURCE_NOTE} Quote refresh unavailable: {exc}. Sample fallback is active."
        refreshed = []
        source_note = self.DATA_SOURCE_NOTE
        for row, quote in zip(rows, quote_rows):
            current = row.copy()
            candle_data = self._daily_candles(current, quote, session=session)
            current.update(self._price_volume_metrics(current, quote, candle_data))
            current.update(self._technical_metrics(current, candle_data))
            current.update(self._candlestick_metrics(candle_data))
            refreshed.append(current)
            if quote.get("data_source_note"):
                source_note = quote["data_source_note"]
        return refreshed, source_note

    def _daily_candles(self, row: dict[str, Any], quote: dict[str, Any] | None = None, session=None) -> dict[str, Any]:
        try:
            return self.market_data.get_candles(
                symbol=row.get("symbol"),
                token=(quote or {}).get("symbol_token") or row.get("symbol_token"),
                exchange=row.get("exchange") or "NSE",
                interval="ONE_DAY",
                from_date=datetime.now() - timedelta(days=370),
                to_date=datetime.now(),
                session=session,
            )
        except Exception:
            return {"frame": None, "data_source_badge": "Unavailable", "data_source": "Unavailable"}

    def _price_volume_metrics(self, row: dict[str, Any], quote: dict[str, Any] | None, candle_data: dict[str, Any] | None) -> dict[str, Any]:
        quote = quote or {}
        frame = (candle_data or {}).get("frame")
        latest_candle = self._latest_candle(frame)
        ltp = self._number(quote.get("latest_price"), row.get("ltp"), latest_candle.get("close"))
        previous_close = self._number(quote.get("previous_close"), self._previous_close(frame))
        open_price = self._number(quote.get("open"), latest_candle.get("open"))
        high = self._number(quote.get("high"), latest_candle.get("high"))
        low = self._number(quote.get("low"), latest_candle.get("low"))
        volume = self._number(quote.get("volume"), latest_candle.get("volume"), row.get("volume"))
        point_change = self._diff(ltp, previous_close)
        percent_change = self._number(self._pct(point_change, previous_close), quote.get("change_pct"), row.get("change_pct"))
        point_change = self._number(point_change, quote.get("change"))
        avg_volume_20d = self._avg_volume(frame, 20)
        relative_volume = self._ratio(volume, avg_volume_20d)
        high_52w = self._number(quote.get("week_52_high"), self._column_extreme(frame, "high", max))
        low_52w = self._number(quote.get("week_52_low"), self._column_extreme(frame, "low", min))
        gap_pct = self._pct(self._diff(open_price, previous_close), previous_close)
        return {
            "ltp": ltp,
            "previous_close": previous_close,
            "percent_change": percent_change,
            "change_pct": percent_change,
            "point_change": point_change,
            "volume": volume,
            "avg_volume_20d": avg_volume_20d,
            "relative_volume": relative_volume,
            "volume_spike": relative_volume >= self.VOLUME_SPIKE_THRESHOLD if relative_volume is not None else None,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "distance_from_52w_high_pct": self._pct(self._diff(ltp, high_52w), high_52w),
            "distance_from_52w_low_pct": self._pct(self._diff(ltp, low_52w), low_52w),
            "gap_up_pct": gap_pct,
            "gap_down_pct": gap_pct,
            "day_range_pct": self._pct(self._diff(high, low), previous_close),
            "turnover": self._product(ltp, volume),
            "data_source": self._row_source(quote, candle_data),
        }

    def _with_sample_price_volume(self, row: dict[str, Any]) -> dict[str, Any]:
        ltp = self._number(row.get("ltp"))
        percent_change = self._number(row.get("change_pct"))
        row.update(
            {
                "previous_close": None,
                "percent_change": percent_change,
                "change_pct": percent_change,
                "point_change": None,
                "avg_volume_20d": None,
                "relative_volume": None,
                "volume_spike": None,
                "high_52w": None,
                "low_52w": None,
                "distance_from_52w_high_pct": None,
                "distance_from_52w_low_pct": None,
                "gap_up_pct": None,
                "gap_down_pct": None,
                "day_range_pct": None,
                "turnover": self._product(ltp, self._number(row.get("volume"))),
                "data_source": "Sample",
                "ema_20": None,
                "ema_50": None,
                "ema_200": None,
                "price_above_ema20": None,
                "price_above_ema50": None,
                "price_above_ema200": None,
                "ema20_above_ema50": None,
                "ema50_above_ema200": None,
                "sma_20": None,
                "sma_50": None,
                "sma_200": None,
                "price_above_sma20": None,
                "price_above_sma50": None,
                "price_above_sma200": None,
                "rsi_14": None,
                "rsi_status": None,
                "rsi_oversold": None,
                "rsi_overbought": None,
                "macd_line": None,
                "macd_signal": None,
                "macd_histogram": None,
                "macd_bullish": None,
                "macd_bearish": None,
                "breakout_20d": None,
                "breakdown_20d": None,
                "breakout_52w": None,
                "breakdown_52w": None,
                "volume_confirmed_breakout": None,
                "trend_score": None,
                "technical_rating": None,
                **self._empty_candlestick_metrics(),
            }
        )
        return row

    def _technical_metrics(self, row: dict[str, Any], candle_data: dict[str, Any] | None) -> dict[str, Any]:
        frame = (candle_data or {}).get("frame")
        close = self._numeric_series(frame, "close")
        high = self._numeric_series(frame, "high")
        low = self._numeric_series(frame, "low")
        if close is None or close.empty:
            return self._empty_technical_metrics(row)

        close_today = self._number(close.iloc[-1], row.get("ltp"))
        ema_20 = self._last_ema(close, 20)
        ema_50 = self._last_ema(close, 50)
        ema_200 = self._last_ema(close, 200)
        sma_20 = self._last_sma(close, 20)
        sma_50 = self._last_sma(close, 50)
        sma_200 = self._last_sma(close, 200)
        rsi_14 = self._last_rsi(close, 14)
        macd = self._last_macd(close)
        previous_high_20 = self._previous_extreme(high, 20, max)
        previous_low_20 = self._previous_extreme(low, 20, min)
        high_52w = self._number(row.get("high_52w"), self._series_extreme(high, max))
        low_52w = self._number(row.get("low_52w"), self._series_extreme(low, min))
        breakout_20d = close_today > previous_high_20 if close_today is not None and previous_high_20 is not None else None
        breakdown_20d = close_today < previous_low_20 if close_today is not None and previous_low_20 is not None else None
        breakout_52w = close_today >= high_52w if close_today is not None and high_52w is not None else None
        breakdown_52w = close_today <= low_52w if close_today is not None and low_52w is not None else None
        relative_volume = self._number(row.get("relative_volume"))
        macd_line = macd.get("line")
        macd_signal = macd.get("signal")
        macd_bullish = macd_line > macd_signal if macd_line is not None and macd_signal is not None else None
        macd_bearish = macd_line < macd_signal if macd_line is not None and macd_signal is not None else None
        rsi_status = self._rsi_status(rsi_14)
        trend_score = self._trend_score(
            close_today=close_today,
            ema_20=ema_20,
            ema_50=ema_50,
            rsi_14=rsi_14,
            macd_bullish=macd_bullish,
        )
        return {
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "price_above_ema20": close_today > ema_20 if close_today is not None and ema_20 is not None else None,
            "price_above_ema50": close_today > ema_50 if close_today is not None and ema_50 is not None else None,
            "price_above_ema200": close_today > ema_200 if close_today is not None and ema_200 is not None else None,
            "ema20_above_ema50": ema_20 > ema_50 if ema_20 is not None and ema_50 is not None else None,
            "ema50_above_ema200": ema_50 > ema_200 if ema_50 is not None and ema_200 is not None else None,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "price_above_sma20": close_today > sma_20 if close_today is not None and sma_20 is not None else None,
            "price_above_sma50": close_today > sma_50 if close_today is not None and sma_50 is not None else None,
            "price_above_sma200": close_today > sma_200 if close_today is not None and sma_200 is not None else None,
            "rsi_14": rsi_14,
            "rsi_status": rsi_status,
            "rsi_oversold": rsi_14 < 30 if rsi_14 is not None else None,
            "rsi_overbought": rsi_14 > 70 if rsi_14 is not None else None,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd.get("histogram"),
            "macd_bullish": macd_bullish,
            "macd_bearish": macd_bearish,
            "breakout_20d": breakout_20d,
            "breakdown_20d": breakdown_20d,
            "breakout_52w": breakout_52w,
            "breakdown_52w": breakdown_52w,
            "volume_confirmed_breakout": bool(breakout_20d and relative_volume is not None and relative_volume >= 1.5) if breakout_20d is not None else None,
            "trend_score": trend_score,
            "technical_rating": self._technical_rating(trend_score),
        }

    def _empty_technical_metrics(self, row: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ema_20": None,
            "ema_50": None,
            "ema_200": None,
            "price_above_ema20": None,
            "price_above_ema50": None,
            "price_above_ema200": None,
            "ema20_above_ema50": None,
            "ema50_above_ema200": None,
            "sma_20": None,
            "sma_50": None,
            "sma_200": None,
            "price_above_sma20": None,
            "price_above_sma50": None,
            "price_above_sma200": None,
            "rsi_14": None,
            "rsi_status": None,
            "rsi_oversold": None,
            "rsi_overbought": None,
            "macd_line": None,
            "macd_signal": None,
            "macd_histogram": None,
            "macd_bullish": None,
            "macd_bearish": None,
            "breakout_20d": None,
            "breakdown_20d": None,
            "breakout_52w": None,
            "breakdown_52w": None,
            "volume_confirmed_breakout": None,
            "trend_score": None,
            "technical_rating": None,
        }

    def _candlestick_metrics(self, candle_data: dict[str, Any] | None) -> dict[str, Any]:
        frame = (candle_data or {}).get("frame")
        if frame is None or getattr(frame, "empty", True):
            return self._empty_candlestick_metrics()
        latest = self._latest_candle(frame)
        previous = self._previous_candle(frame)
        open_price = latest.get("open")
        high = latest.get("high")
        low = latest.get("low")
        close = latest.get("close")
        if None in (open_price, high, low, close):
            return self._empty_candlestick_metrics()

        body = abs(close - open_price)
        candle_range = high - low
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low
        patterns: dict[str, bool | None] = {
            "doji": candle_range > 0 and body <= 0.10 * candle_range,
            "hammer": candle_range > 0 and lower_wick >= 2 * body and upper_wick <= body,
            "shooting_star": candle_range > 0 and upper_wick >= 2 * body and lower_wick <= body,
            "bullish_marubozu": candle_range > 0 and close > open_price and upper_wick <= 0.05 * candle_range and lower_wick <= 0.05 * candle_range,
            "bearish_marubozu": candle_range > 0 and close < open_price and upper_wick <= 0.05 * candle_range and lower_wick <= 0.05 * candle_range,
            "strong_bullish_candle": candle_range > 0 and close > open_price and body >= 0.60 * candle_range,
            "strong_bearish_candle": candle_range > 0 and close < open_price and body >= 0.60 * candle_range,
        }
        if previous:
            prev_open = previous.get("open")
            prev_high = previous.get("high")
            prev_low = previous.get("low")
            prev_close = previous.get("close")
            patterns.update(
                {
                    "bullish_engulfing": prev_close < prev_open and close > open_price and open_price <= prev_close and close >= prev_open if None not in (prev_open, prev_close) else None,
                    "bearish_engulfing": prev_close > prev_open and close < open_price and open_price >= prev_close and close <= prev_open if None not in (prev_open, prev_close) else None,
                    "inside_bar": high < prev_high and low > prev_low if None not in (prev_high, prev_low) else None,
                    "outside_bar": high > prev_high and low < prev_low if None not in (prev_high, prev_low) else None,
                    "gap_up": open_price > prev_high if prev_high is not None else None,
                    "gap_down": open_price < prev_low if prev_low is not None else None,
                }
            )
        else:
            patterns.update(
                {
                    "bullish_engulfing": None,
                    "bearish_engulfing": None,
                    "inside_bar": None,
                    "outside_bar": None,
                    "gap_up": None,
                    "gap_down": None,
                }
            )

        detected = self._detected_patterns(patterns)
        bullish_count = sum(1 for key in self.BULLISH_CANDLE_PATTERNS if patterns.get(key) is True)
        bearish_count = sum(1 for key in self.BEARISH_CANDLE_PATTERNS if patterns.get(key) is True)
        neutral_count = sum(1 for key in self.NEUTRAL_CANDLE_PATTERNS if patterns.get(key) is True)
        bias = "Bullish" if bullish_count > bearish_count else "Bearish" if bearish_count > bullish_count else "Neutral"
        return {
            **patterns,
            "candle_open": open_price,
            "candle_high": high,
            "candle_low": low,
            "candle_close": close,
            "candle_body": round(body, 2),
            "candle_range": round(candle_range, 2),
            "upper_wick": round(upper_wick, 2),
            "lower_wick": round(lower_wick, 2),
            "detected_patterns": detected,
            "bullish_pattern_count": bullish_count,
            "bearish_pattern_count": bearish_count,
            "neutral_pattern_count": neutral_count,
            "candlestick_bias": bias,
            "pattern_status": "Available",
        }

    CANDLE_PATTERN_LABELS = {
        "doji": "Doji",
        "hammer": "Hammer",
        "shooting_star": "Shooting Star",
        "bullish_engulfing": "Bullish Engulfing",
        "bearish_engulfing": "Bearish Engulfing",
        "inside_bar": "Inside Bar",
        "outside_bar": "Outside Bar",
        "bullish_marubozu": "Bullish Marubozu",
        "bearish_marubozu": "Bearish Marubozu",
        "gap_up": "Gap Up",
        "gap_down": "Gap Down",
        "strong_bullish_candle": "Strong Bullish Candle",
        "strong_bearish_candle": "Strong Bearish Candle",
    }
    BULLISH_CANDLE_PATTERNS = {"hammer", "bullish_engulfing", "bullish_marubozu", "gap_up", "strong_bullish_candle"}
    BEARISH_CANDLE_PATTERNS = {"shooting_star", "bearish_engulfing", "bearish_marubozu", "gap_down", "strong_bearish_candle"}
    NEUTRAL_CANDLE_PATTERNS = {"doji", "inside_bar", "outside_bar"}

    def _detected_patterns(self, patterns: dict[str, bool | None]) -> list[str]:
        return [label for key, label in self.CANDLE_PATTERN_LABELS.items() if patterns.get(key) is True]

    def _empty_candlestick_metrics(self) -> dict[str, Any]:
        return {
            "doji": None,
            "hammer": None,
            "shooting_star": None,
            "bullish_engulfing": None,
            "bearish_engulfing": None,
            "inside_bar": None,
            "outside_bar": None,
            "bullish_marubozu": None,
            "bearish_marubozu": None,
            "gap_up": None,
            "gap_down": None,
            "strong_bullish_candle": None,
            "strong_bearish_candle": None,
            "candle_open": None,
            "candle_high": None,
            "candle_low": None,
            "candle_close": None,
            "candle_body": None,
            "candle_range": None,
            "upper_wick": None,
            "lower_wick": None,
            "detected_patterns": [],
            "bullish_pattern_count": 0,
            "bearish_pattern_count": 0,
            "neutral_pattern_count": 0,
            "candlestick_bias": "Unavailable",
            "pattern_status": "Unavailable",
        }

    def _latest_candle(self, frame: Any) -> dict[str, float | None]:
        if frame is None or getattr(frame, "empty", True):
            return {}
        latest = frame.iloc[-1]
        return {
            "open": self._number(self._series_value(latest, "open")),
            "high": self._number(self._series_value(latest, "high")),
            "low": self._number(self._series_value(latest, "low")),
            "close": self._number(self._series_value(latest, "close")),
            "volume": self._number(self._series_value(latest, "volume")),
        }

    def _previous_candle(self, frame: Any) -> dict[str, float | None]:
        if frame is None or getattr(frame, "empty", True) or len(frame) < 2:
            return {}
        previous = frame.iloc[-2]
        return {
            "open": self._number(self._series_value(previous, "open")),
            "high": self._number(self._series_value(previous, "high")),
            "low": self._number(self._series_value(previous, "low")),
            "close": self._number(self._series_value(previous, "close")),
        }

    def _previous_close(self, frame: Any) -> float | None:
        if frame is None or getattr(frame, "empty", True) or len(frame) < 2:
            return None
        return self._number(self._series_value(frame.iloc[-2], "close"))

    def _avg_volume(self, frame: Any, days: int) -> float | None:
        column = self._column_name(frame, "volume")
        if frame is None or getattr(frame, "empty", True) or column is None:
            return None
        values = [self._number(value) for value in frame[column].tail(days)]
        values = [value for value in values if value is not None]
        return round(sum(values) / len(values), 2) if values else None

    def _column_extreme(self, frame: Any, column: str, func) -> float | None:
        column_name = self._column_name(frame, column)
        if frame is None or getattr(frame, "empty", True) or column_name is None:
            return None
        values = [self._number(value) for value in frame[column_name]]
        values = [value for value in values if value is not None]
        return round(float(func(values)), 2) if values else None

    def _numeric_series(self, frame: Any, column: str) -> pd.Series | None:
        column_name = self._column_name(frame, column)
        if frame is None or getattr(frame, "empty", True) or column_name is None:
            return None
        series = pd.to_numeric(frame[column_name], errors="coerce").dropna()
        return series.reset_index(drop=True)

    def _last_ema(self, series: pd.Series, period: int) -> float | None:
        if len(series) < period:
            return None
        return self._number(series.ewm(span=period, adjust=False).mean().iloc[-1])

    def _last_sma(self, series: pd.Series, period: int) -> float | None:
        if len(series) < period:
            return None
        return self._number(series.tail(period).mean())

    def _last_rsi(self, series: pd.Series, period: int = 14) -> float | None:
        if len(series) <= period:
            return None
        delta = series.diff().dropna()
        gains = delta.clip(lower=0).tail(period)
        losses = (-delta.clip(upper=0)).tail(period)
        avg_gain = float(gains.mean())
        avg_loss = float(losses.mean())
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else None
        rs = avg_gain / avg_loss
        return self._number(100 - (100 / (1 + rs)))

    def _last_macd(self, series: pd.Series) -> dict[str, float | None]:
        if len(series) < 35:
            return {"line": None, "signal": None, "histogram": None}
        macd_line = series.ewm(span=12, adjust=False).mean() - series.ewm(span=26, adjust=False).mean()
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        return {
            "line": self._number(macd_line.iloc[-1]),
            "signal": self._number(signal_line.iloc[-1]),
            "histogram": self._number(histogram.iloc[-1]),
        }

    def _previous_extreme(self, series: pd.Series | None, periods: int, func) -> float | None:
        if series is None or len(series) <= periods:
            return None
        values = [self._number(value) for value in series.iloc[-periods - 1 : -1]]
        values = [value for value in values if value is not None]
        return self._number(func(values)) if values else None

    def _series_extreme(self, series: pd.Series | None, func) -> float | None:
        if series is None or series.empty:
            return None
        values = [self._number(value) for value in series]
        values = [value for value in values if value is not None]
        return self._number(func(values)) if values else None

    def _rsi_status(self, rsi: float | None) -> str | None:
        if rsi is None:
            return None
        if rsi < 30:
            return "Oversold"
        if rsi > 70:
            return "Overbought"
        return "Neutral"

    def _trend_score(
        self,
        *,
        close_today: float | None,
        ema_20: float | None,
        ema_50: float | None,
        rsi_14: float | None,
        macd_bullish: bool | None,
    ) -> int | None:
        if None in (close_today, ema_20, ema_50, rsi_14, macd_bullish):
            return None
        score = 0
        if close_today > ema_20:
            score += 20
        if close_today > ema_50:
            score += 20
        if ema_20 > ema_50:
            score += 20
        if macd_bullish:
            score += 20
        if 45 <= rsi_14 <= 70:
            score += 20
        return score

    def _technical_rating(self, score: int | None) -> str | None:
        if score is None:
            return None
        if score >= 80:
            return "Strong Buy"
        if score >= 60:
            return "Buy"
        if score >= 40:
            return "Neutral"
        if score >= 20:
            return "Sell"
        return "Strong Sell"

    def _column_name(self, frame: Any, wanted: str) -> str | None:
        if frame is None or not hasattr(frame, "columns"):
            return None
        wanted_lower = wanted.lower()
        for column in frame.columns:
            if str(column).lower() == wanted_lower:
                return column
        return None

    def _series_value(self, series: Any, wanted: str) -> Any:
        key = self._column_name(getattr(series, "to_frame", lambda: None)().T, wanted) if hasattr(series, "to_frame") else None
        return series.get(key) if key is not None else None

    def _number(self, *values: Any) -> float | None:
        for value in values:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            return round(number, 2)
        return None

    def _diff(self, left: float | None, right: float | None) -> float | None:
        if left is None or right is None:
            return None
        return round(left - right, 2)

    def _pct(self, numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator in (None, 0):
            return None
        return round((numerator / denominator) * 100, 2)

    def _ratio(self, numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator in (None, 0):
            return None
        return round(numerator / denominator, 2)

    def _product(self, left: float | None, right: float | None) -> float | None:
        if left is None or right is None:
            return None
        return round(float(left) * float(right), 2)

    def _composite_score(self, row: dict[str, Any]) -> float | None:
        trend_score = self._number(row.get("trend_score"))
        relative_volume = self._number(row.get("relative_volume"))
        percent_change = self._number(row.get("percent_change"), row.get("change_pct"))
        if trend_score is None and relative_volume is None and percent_change is None and row.get("candlestick_bias") in (None, "Unavailable"):
            return None
        trend_component = self._clamp(trend_score or 0, 0, 100)
        relative_volume_component = self._clamp(((relative_volume or 0) / 3) * 100, 0, 100)
        pattern_component = {"Bullish": 100, "Neutral": 50, "Bearish": 0}.get(row.get("candlestick_bias"), 0)
        percent_component = self._clamp(((percent_change or -5) + 5) * 10, 0, 100)
        return round(
            (0.35 * trend_component)
            + (0.25 * relative_volume_component)
            + (0.20 * pattern_component)
            + (0.20 * percent_component),
            2,
        )

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, float(value)))

    def _row_source(self, quote: dict[str, Any], candle_data: dict[str, Any] | None) -> str:
        labels = [quote.get("data_source_badge"), (candle_data or {}).get("data_source_badge")]
        if "Live: Angel One" in labels:
            return "Live"
        if "Sample" in labels:
            return "Sample"
        if "Cached" in labels:
            return "Cached"
        return "Unavailable"
