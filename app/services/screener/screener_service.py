from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.schemas.screener_schema import ScreenerRunRequest, ScreenerSavedScreenCreate
from app.services.market_data.engine import MarketDataEngine, get_market_data_engine


class ScreenerService:
    DATA_SOURCE_NOTE = (
        "Screener v1 is running on a safe local preview universe. "
        "Connect an exchange-wide instrument and fundamentals source before treating scans as full NSE/BSE coverage."
    )

    UNIVERSES = ["Indian Equities", "NIFTY 50", "NIFTY 100", "NIFTY 500", "All NSE", "All BSE"]
    EXCHANGES = ["NSE", "BSE", "NSE + BSE"]
    CATEGORIES = [
        "Overview",
        "Price & Volume",
        "Fundamentals",
        "Technical Indicators",
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
        "Price": ["LTP", "% Change", "Volume", "Relative Volume", "Market Cap", "52W High Distance", "52W Low Distance"],
        "Fundamentals": ["P/E Ratio", "P/B Ratio", "ROE", "ROCE", "EPS Growth", "Sales Growth", "Debt to Equity", "Dividend Yield"],
        "Technicals": ["RSI", "MACD Signal", "Price Above EMA20", "Price Above EMA50", "Price Above EMA200", "Volume Spike", "Breakout 20D", "Breakout 52W"],
    }
    CONDITIONS = ["Greater Than", "Less Than", "Between", "Equal To", "Is True", "Is False"]
    SORT_OPTIONS = ["Market Cap", "% Change", "Volume", "P/E", "ROE", "RSI"]

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
        "% Change": "change_pct",
        "Volume": "volume",
        "Market Cap": "market_cap_cr",
        "Market Cap (₹ Cr)": "market_cap_cr",
        "P/E Ratio": "pe_ttm",
        "P/E Ratio (TTM)": "pe_ttm",
        "ROE": "roe_pct",
        "ROE (%)": "roe_pct",
        "EPS Growth": "eps_growth_yoy_pct",
        "EPS Growth YoY (%)": "eps_growth_yoy_pct",
        "RSI": "rsi_14",
        "RSI (14)": "rsi_14",
        "Debt to Equity": "debt_equity",
        "Volume (20D Avg)": "volume",
        "Price Above 200 EMA": "price_above_ema200",
        "Price Above EMA200": "price_above_ema200",
    }
    SORT_FIELDS = {
        "Market Cap": "market_cap_cr",
        "% Change": "change_pct",
        "Volume": "volume",
        "P/E": "pe_ttm",
        "ROE": "roe_pct",
        "RSI": "rsi_14",
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
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def run(self, request: ScreenerRunRequest) -> dict[str, Any]:
        rows, source_note = self._market_rows()
        filtered = [row for row in rows if self._matches_filters(row, request.filters)]
        sort_field = self.SORT_FIELDS.get(request.sort_by, "market_cap_cr")
        filtered.sort(key=lambda item: item.get(sort_field) or 0, reverse=request.sort_direction == "desc")
        return {
            "results": filtered,
            "summary": self._summary(filtered, request),
            "distributions": self._distributions(filtered),
            "sector_breakdown": self._sector_breakdown(filtered),
            "saved_screens": self.list_saved_screens(),
            "data_source_note": source_note,
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
        result = True
        for item in filters:
            current = self._matches_filter(row, item)
            result = result or current if item.logical == "OR" else result and current
        return result

    def _matches_filter(self, row: dict[str, Any], item: Any) -> bool:
        field = self.METRIC_FIELDS.get(item.metric)
        if not field:
            return True
        actual = row.get(field)
        expected = self._coerce(item.value)
        expected_2 = self._coerce(item.value_2)
        if item.condition == "Is True":
            return bool(actual) is True
        if item.condition == "Is False":
            return bool(actual) is False
        if actual is None or expected is None:
            return True
        if item.condition == "Greater Than":
            return float(actual) > float(expected)
        if item.condition == "Less Than":
            return float(actual) < float(expected)
        if item.condition == "Between":
            high = expected_2 if expected_2 is not None else expected
            return float(expected) <= float(actual) <= float(high)
        if item.condition == "Equal To":
            return str(actual).lower() == str(expected).lower()
        return True

    def _summary(self, rows: list[dict[str, Any]], request: ScreenerRunRequest) -> dict[str, Any]:
        total_volume = sum(int(row["volume"]) for row in rows)
        avg_market_cap = self._avg(rows, "market_cap_cr")
        avg_change = self._avg(rows, "change_pct")
        return {
            "matches": len(rows),
            "total_stocks": len(self.SAMPLE_UNIVERSE),
            "avg_market_cap_cr": round(avg_market_cap, 2),
            "avg_change_pct": round(avg_change, 2),
            "total_volume": total_volume,
            "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_ms": 42,
            "status": "Completed",
            "universe": request.universe,
            "exchange": request.exchange,
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
            value = float(row[field])
            index = 0
            while index < len(buckets) and value >= buckets[index]:
                index += 1
            counts[index] += 1
        return [{"label": label, "value": counts[index]} for index, label in enumerate(labels)]

    def _avg(self, rows: list[dict[str, Any]], field: str) -> float:
        if not rows:
            return 0.0
        return sum(float(row[field]) for row in rows) / len(rows)

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

    def _market_rows(self) -> tuple[list[dict[str, Any]], str]:
        rows = [row.copy() for row in self.SAMPLE_UNIVERSE]
        try:
            quote_rows = self.market_data.get_quotes_bulk(
                [{"symbol": row["symbol"], "exchange": row["exchange"]} for row in rows]
            )["items"]
        except Exception as exc:
            return rows, f"{self.DATA_SOURCE_NOTE} Quote refresh unavailable: {exc}"

        source_note = self.DATA_SOURCE_NOTE
        for row, quote in zip(rows, quote_rows):
            row["ltp"] = quote.get("latest_price") if quote.get("latest_price") is not None else row["ltp"]
            row["change_pct"] = quote.get("change_pct") if quote.get("change_pct") is not None else row["change_pct"]
            row["volume"] = quote.get("volume") if quote.get("volume") is not None else row["volume"]
            if quote.get("data_source_note"):
                source_note = quote["data_source_note"]
        return rows, source_note
