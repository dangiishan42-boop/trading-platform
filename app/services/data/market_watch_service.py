from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.config.constants import ANGEL_INDEX_DETAILS, ANGEL_SYMBOL_DETAILS, MARKET_WATCH_PEERS
from app.core.exceptions import InvalidRequestError
from app.schemas.data_schema import AngelDataFetchRequest
from app.services.data.angel_smartapi_service import AngelSmartApiService
from app.services.data.data_resampler_service import DataResamplerService
from app.services.data.instrument_master_service import InstrumentMasterService


@dataclass(frozen=True)
class ResolvedMarketSymbol:
    symbol: str
    stock_name: str
    exchange: str
    symbol_token: str


@dataclass(frozen=True)
class MarketWatchIntervalConfig:
    angel_interval: str
    lookback: timedelta
    resample_rule: str | None = None


class MarketWatchService:
    INTERVAL_CONFIG = {
        "1m": MarketWatchIntervalConfig("ONE_MINUTE", timedelta(hours=6)),
        "3m": MarketWatchIntervalConfig("ONE_MINUTE", timedelta(hours=12), "3min"),
        "5m": MarketWatchIntervalConfig("FIVE_MINUTE", timedelta(days=2)),
        "15m": MarketWatchIntervalConfig("FIFTEEN_MINUTE", timedelta(days=5)),
        "30m": MarketWatchIntervalConfig("THIRTY_MINUTE", timedelta(days=10)),
        "1H": MarketWatchIntervalConfig("ONE_HOUR", timedelta(days=30)),
        "4H": MarketWatchIntervalConfig("ONE_HOUR", timedelta(days=90), "4h"),
        "1D": MarketWatchIntervalConfig("ONE_DAY", timedelta(days=365)),
        "1W": MarketWatchIntervalConfig("ONE_DAY", timedelta(days=365 * 3), "W"),
        "1M": MarketWatchIntervalConfig("ONE_DAY", timedelta(days=365 * 5), "ME"),
    }

    def __init__(
        self,
        angel: AngelSmartApiService | None = None,
        instruments: InstrumentMasterService | None = None,
        resampler: DataResamplerService | None = None,
    ) -> None:
        self.angel = angel or AngelSmartApiService()
        self.instruments = instruments or InstrumentMasterService()
        self.resampler = resampler or DataResamplerService()

    def resolve_symbol(
        self,
        query: str | None,
        exchange: str = "NSE",
        symbol_token: str | None = None,
        session=None,
    ) -> ResolvedMarketSymbol:
        instrument = self.instruments.resolve(session, query=query, exchange=exchange, token=symbol_token)
        if instrument is not None:
            return ResolvedMarketSymbol(
                symbol=instrument.symbol,
                stock_name=instrument.name,
                exchange=instrument.exchange,
                symbol_token=instrument.token,
            )

        normalized_query = self._normalize_query(query)
        if normalized_query:
            for symbol, details in ANGEL_SYMBOL_DETAILS.items():
                names = {symbol, details["name"].upper(), details["name"].replace(" ", "").upper()}
                if normalized_query in names:
                    return ResolvedMarketSymbol(
                        symbol=symbol,
                        stock_name=details["name"],
                        exchange=details["exchange"],
                        symbol_token=details["token"],
                    )

        if symbol_token:
            symbol = normalized_query or f"TOKEN_{symbol_token}"
            return ResolvedMarketSymbol(
                symbol=symbol,
                stock_name=symbol.replace("_", " "),
                exchange=exchange.upper(),
                symbol_token=symbol_token,
            )

        raise InvalidRequestError("Symbol is not in the local map. Enter a manual Angel token to continue.")

    def quote(self, query: str | None, exchange: str = "NSE", symbol_token: str | None = None, session=None) -> dict[str, Any]:
        resolved = self.resolve_symbol(query, exchange, symbol_token, session=session)
        base = self._empty_quote(resolved)
        if not self.angel.has_credentials():
            base["message"] = "Angel One credentials are not configured. Showing mapped symbol only."
            return base

        try:
            ltp_response = self.angel.fetch_ltp(
                exchange=resolved.exchange,
                symbol=self._angel_trading_symbol(resolved),
                symbol_token=resolved.symbol_token,
            )
            ltp_data = ltp_response.get("data") or {}
            daily_frame = self._try_daily_frame(resolved)
            return self._quote_from_angel(resolved, ltp_data, daily_frame)
        except Exception as exc:
            base["message"] = str(exc)
            return base

    def candles(
        self,
        query: str | None,
        exchange: str,
        symbol_token: str | None,
        interval: str,
        fromdate: datetime | None,
        todate: datetime | None,
        session=None,
    ) -> dict[str, Any]:
        resolved = self.resolve_symbol(query, exchange, symbol_token, session=session)
        request = self._candle_request(resolved, interval, fromdate, todate)
        frame = self.angel.fetch_frame(request)
        frame = self._prepare_interval_frame(frame, interval)
        return {
            "symbol": resolved.symbol,
            "stock_name": resolved.stock_name,
            "exchange": resolved.exchange,
            "symbol_token": resolved.symbol_token,
            "interval": interval,
            "rows": self._frame_rows(frame),
        }

    def indices(self) -> list[dict[str, Any]]:
        rows = []
        for name, details in ANGEL_INDEX_DETAILS.items():
            token = details.get("token")
            if not token or not self.angel.has_credentials():
                rows.append(
                    {
                        "name": name,
                        "exchange": details["exchange"],
                        "available": False,
                        "message": "Index token or Angel credentials are not configured.",
                    }
                )
                continue

            try:
                response = self.angel.fetch_ltp(exchange=details["exchange"], symbol=name, symbol_token=token)
                data = response.get("data") or {}
                latest = self._number(data.get("ltp"))
                previous_close = self._number(data.get("close"))
                change = latest - previous_close if latest is not None and previous_close is not None else None
                rows.append(
                    {
                        "name": name,
                        "exchange": details["exchange"],
                        "latest_price": latest,
                        "change": self._round(change),
                        "change_pct": self._change_pct(change, previous_close),
                        "available": latest is not None,
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "name": name,
                        "exchange": details["exchange"],
                        "available": False,
                        "message": str(exc),
                    }
                )
        return rows

    def fundamentals_placeholder(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_query(symbol)
        peer_group = MARKET_WATCH_PEERS.get(normalized, {})
        return {
            "symbol": normalized,
            "available": False,
            "message": "Fundamental data source not connected yet",
            "sector": peer_group.get("sector"),
            "industry": peer_group.get("industry"),
            "fields": {
                "market_cap": None,
                "pe_ratio": None,
                "eps": None,
                "book_value": None,
                "roe": None,
                "debt_equity": None,
                "dividend_yield": None,
                "face_value": None,
                "sector": peer_group.get("sector"),
                "industry": peer_group.get("industry"),
                "week_52_high": None,
                "week_52_low": None,
            },
        }

    def option_chain_placeholder(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_query(symbol)
        return {
            "symbol": normalized,
            "available": False,
            "message": "Option chain data source not connected yet",
            "expiries": [],
            "summary": {
                "pcr": None,
                "max_pain": None,
                "total_ce_oi": None,
                "total_pe_oi": None,
                "atm_strike": None,
            },
            "rows": [],
        }

    def peers(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_query(symbol)
        group = MARKET_WATCH_PEERS.get(normalized, {})
        rows = []
        for peer_symbol in group.get("peers", []):
            details = ANGEL_SYMBOL_DETAILS.get(peer_symbol, {})
            rows.append(
                {
                    "symbol": peer_symbol,
                    "name": details.get("name", peer_symbol),
                    "exchange": details.get("exchange", "NSE"),
                    "sector": group.get("sector"),
                    "industry": group.get("industry"),
                    "latest_price": None,
                    "change_pct": None,
                }
            )
        return {
            "symbol": normalized,
            "sector": group.get("sector"),
            "industry": group.get("industry"),
            "peers": rows,
        }

    def technical_detail(
        self,
        symbol: str,
        exchange: str = "NSE",
        symbol_token: str | None = None,
        session=None,
    ) -> dict[str, Any]:
        normalized = self._normalize_query(symbol)
        if not self.angel.has_credentials():
            return {
                "symbol": normalized,
                "available": False,
                "message": "Candle data source not connected yet",
                "signals": {},
                "support": None,
                "resistance": None,
                "overall_rating": "Neutral",
            }

        try:
            candle_data = self.candles(normalized, exchange, symbol_token, "1D", datetime.now() - timedelta(days=260), datetime.now(), session=session)
        except Exception as exc:
            return {
                "symbol": normalized,
                "available": False,
                "message": str(exc),
                "signals": {},
                "support": None,
                "resistance": None,
                "overall_rating": "Neutral",
            }

        rows = candle_data.get("rows", [])
        return self._technical_from_rows(normalized, rows)

    def _technical_from_rows(self, symbol: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if len(rows) < 20:
            return {
                "symbol": symbol,
                "available": False,
                "message": "Insufficient candle data for technical signals",
                "signals": {},
                "support": None,
                "resistance": None,
                "overall_rating": "Neutral",
            }

        closes = [float(row["close"]) for row in rows]
        highs = [float(row["high"]) for row in rows]
        lows = [float(row["low"]) for row in rows]
        volumes = [float(row["volume"]) for row in rows]
        latest = closes[-1]
        ema20 = self._simple_average(closes[-20:])
        ema50 = self._simple_average(closes[-50:]) if len(closes) >= 50 else None
        ema200 = self._simple_average(closes[-200:]) if len(closes) >= 200 else None
        rsi_value = self._rsi(closes)
        avg_volume = self._simple_average(volumes[-20:])
        volume_spike = volumes[-1] > avg_volume * 1.5 if avg_volume else False
        resistance = max(highs[-20:])
        support = min(lows[-20:])
        breakout = latest >= resistance * 0.995
        trend = "Sideways"
        if ema50 is not None and latest > ema20 > ema50:
            trend = "Bullish"
        elif ema50 is not None and latest < ema20 < ema50:
            trend = "Bearish"

        score = 0
        score += 1 if trend == "Bullish" else -1 if trend == "Bearish" else 0
        score += 1 if rsi_value is not None and 45 <= rsi_value <= 70 else -1 if rsi_value is not None and rsi_value < 35 else 0
        score += 1 if ema50 is not None and ema20 > ema50 else -1 if ema50 is not None and ema20 < ema50 else 0
        score += 1 if ema200 is not None and latest > ema200 else -1 if ema200 is not None and latest < ema200 else 0
        score += 1 if breakout else 0
        rating = "Strong Buy" if score >= 4 else "Buy" if score >= 2 else "Sell" if score <= -2 else "Neutral"
        if score <= -4:
            rating = "Strong Sell"

        return {
            "symbol": symbol,
            "available": True,
            "message": None,
            "signals": {
                "trend": trend,
                "rsi": self._round(rsi_value),
                "rsi_status": self._rsi_status(rsi_value),
                "ema20": self._round(ema20),
                "ema50": self._round(ema50),
                "ema20_vs_ema50": "Above" if ema50 is not None and ema20 > ema50 else "Below" if ema50 is not None else "Insufficient data",
                "ema200": self._round(ema200),
                "price_vs_ema200": "Above" if ema200 is not None and latest > ema200 else "Below" if ema200 is not None else "Insufficient data",
                "volume_spike": volume_spike,
                "breakout": breakout,
                "average_volume": self._round(avg_volume),
            },
            "support": self._round(support),
            "resistance": self._round(resistance),
            "overall_rating": rating,
        }

    def _simple_average(self, values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    def _rsi(self, closes: list[float], period: int = 14) -> float | None:
        if len(closes) <= period:
            return None
        gains = 0.0
        losses = 0.0
        for index in range(len(closes) - period, len(closes)):
            diff = closes[index] - closes[index - 1]
            if diff >= 0:
                gains += diff
            else:
                losses -= diff
        if losses == 0:
            return 100.0
        return 100 - (100 / (1 + gains / losses))

    def _rsi_status(self, value: float | None) -> str:
        if value is None:
            return "Insufficient data"
        if value >= 70:
            return "Overbought"
        if value <= 30:
            return "Oversold"
        return "Neutral"

    def _normalize_query(self, query: str | None) -> str:
        return str(query or "").strip().upper().replace(" ", "")

    def _empty_quote(self, resolved: ResolvedMarketSymbol) -> dict[str, Any]:
        return {
            "symbol": resolved.symbol,
            "stock_name": resolved.stock_name,
            "exchange": resolved.exchange,
            "symbol_token": resolved.symbol_token,
            "available": False,
        }

    def _angel_trading_symbol(self, resolved: ResolvedMarketSymbol) -> str:
        if resolved.exchange == "NSE" and not resolved.symbol.endswith("-EQ"):
            return f"{resolved.symbol}-EQ"
        return resolved.symbol

    def _quote_from_angel(self, resolved: ResolvedMarketSymbol, ltp_data: dict[str, Any], daily_frame: pd.DataFrame | None) -> dict[str, Any]:
        latest = self._number(ltp_data.get("ltp"))
        previous_close = self._number(ltp_data.get("close"))
        open_price = self._number(ltp_data.get("open"))
        high = self._number(ltp_data.get("high"))
        low = self._number(ltp_data.get("low"))
        change = latest - previous_close if latest is not None and previous_close is not None else None

        if daily_frame is not None and not daily_frame.empty:
            latest_row = daily_frame.iloc[-1]
            open_price = open_price if open_price is not None else self._number(latest_row["Open"])
            high = high if high is not None else self._number(latest_row["High"])
            low = low if low is not None else self._number(latest_row["Low"])
            latest = latest if latest is not None else self._number(latest_row["Close"])
            previous_close = previous_close if previous_close is not None and previous_close > 0 else self._previous_close(daily_frame)

        volume = self._latest_volume(daily_frame)
        vwap = self._vwap(daily_frame)
        return {
            **self._empty_quote(resolved),
            "latest_price": latest,
            "change": self._round(change),
            "change_pct": self._change_pct(change, previous_close),
            "last_updated": datetime.now().isoformat(timespec="seconds"),
            "open": open_price,
            "high": high,
            "low": low,
            "previous_close": previous_close,
            "volume": volume,
            "day_range": f"{low} - {high}" if low is not None and high is not None else None,
            "week_52_high": self._column_max(daily_frame, "High"),
            "week_52_low": self._column_min(daily_frame, "Low"),
            "vwap": vwap,
            "value_traded": self._round(volume * latest) if volume is not None and latest is not None else None,
            "available": latest is not None,
        }

    def _try_daily_frame(self, resolved: ResolvedMarketSymbol) -> pd.DataFrame | None:
        try:
            request = self._candle_request(resolved, "1D", datetime.now() - timedelta(days=370), datetime.now())
            return self.angel.fetch_frame(request)
        except Exception:
            return None

    def _candle_request(
        self,
        resolved: ResolvedMarketSymbol,
        interval: str,
        fromdate: datetime | None,
        todate: datetime | None,
    ) -> AngelDataFetchRequest:
        interval_config = self.INTERVAL_CONFIG.get(interval)
        if not interval_config:
            raise InvalidRequestError("Unsupported market-watch interval")
        end = todate or datetime.now()
        start = fromdate or (end - interval_config.lookback)
        return AngelDataFetchRequest(
            exchange=resolved.exchange,
            symbol_token=resolved.symbol_token,
            interval=interval_config.angel_interval,
            fromdate=start,
            todate=end,
        )

    def _prepare_interval_frame(self, frame: pd.DataFrame, interval: str) -> pd.DataFrame:
        interval_config = self.INTERVAL_CONFIG.get(interval)
        if not interval_config or not interval_config.resample_rule:
            return frame

        prepared = frame.copy()
        prepared["Date"] = pd.to_datetime(prepared["Date"], errors="coerce")
        if getattr(prepared["Date"].dt, "tz", None) is not None:
            prepared["Date"] = prepared["Date"].dt.tz_localize(None)
        for column in ("Open", "High", "Low", "Close", "Volume"):
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
        prepared = prepared.dropna(subset=["Date", "Open", "High", "Low", "Close", "Volume"])
        if prepared.empty:
            return prepared
        return self.resampler.resample(prepared.sort_values("Date"), interval_config.resample_rule)

    def _frame_rows(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        rows = []
        for _, row in frame.iterrows():
            rows.append(
                {
                    "datetime": str(row["Date"]),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
            )
        return rows

    def _number(self, value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return round(number, 2)

    def _round(self, value: float | None) -> float | None:
        return round(float(value), 2) if value is not None else None

    def _change_pct(self, change: float | None, previous_close: float | None) -> float | None:
        if change is None or not previous_close:
            return None
        return round((change / previous_close) * 100, 2)

    def _previous_close(self, frame: pd.DataFrame) -> float | None:
        if len(frame) < 2:
            return None
        return self._number(frame.iloc[-2]["Close"])

    def _latest_volume(self, frame: pd.DataFrame | None) -> float | None:
        if frame is None or frame.empty:
            return None
        return self._number(frame.iloc[-1]["Volume"])

    def _column_max(self, frame: pd.DataFrame | None, column: str) -> float | None:
        if frame is None or frame.empty:
            return None
        return self._number(frame[column].max())

    def _column_min(self, frame: pd.DataFrame | None, column: str) -> float | None:
        if frame is None or frame.empty:
            return None
        return self._number(frame[column].min())

    def _vwap(self, frame: pd.DataFrame | None) -> float | None:
        if frame is None or frame.empty:
            return None
        typical_price = (frame["High"].astype(float) + frame["Low"].astype(float) + frame["Close"].astype(float)) / 3
        volume = frame["Volume"].astype(float)
        total_volume = volume.sum()
        if total_volume == 0:
            return None
        return round(float((typical_price * volume).sum() / total_volume), 2)
