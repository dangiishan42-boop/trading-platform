from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.config.constants import ANGEL_INDEX_DETAILS, ANGEL_SYMBOL_DETAILS
from app.core.exceptions import InvalidRequestError
from app.schemas.data_schema import AngelDataFetchRequest
from app.services.data.angel_smartapi_service import AngelSmartApiService
from app.services.data.instrument_master_service import InstrumentMasterService


@dataclass(frozen=True)
class ResolvedMarketSymbol:
    symbol: str
    stock_name: str
    exchange: str
    symbol_token: str


class MarketWatchService:
    INTERVAL_TO_ANGEL = {
        "1m": "ONE_MINUTE",
        "5m": "FIVE_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "1H": "ONE_HOUR",
        "1D": "ONE_DAY",
    }
    DEFAULT_LOOKBACK = {
        "1m": timedelta(hours=6),
        "5m": timedelta(days=2),
        "15m": timedelta(days=5),
        "30m": timedelta(days=10),
        "1H": timedelta(days=30),
        "1D": timedelta(days=365),
    }

    def __init__(
        self,
        angel: AngelSmartApiService | None = None,
        instruments: InstrumentMasterService | None = None,
    ) -> None:
        self.angel = angel or AngelSmartApiService()
        self.instruments = instruments or InstrumentMasterService()

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
        normalized_interval = self.INTERVAL_TO_ANGEL.get(interval)
        if not normalized_interval:
            raise InvalidRequestError("Unsupported market-watch interval")
        end = todate or datetime.now()
        start = fromdate or (end - self.DEFAULT_LOOKBACK[interval])
        return AngelDataFetchRequest(
            exchange=resolved.exchange,
            symbol_token=resolved.symbol_token,
            interval=normalized_interval,
            fromdate=start,
            todate=end,
        )

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
