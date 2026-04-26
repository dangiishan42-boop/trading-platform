from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.config.constants import ANGEL_INDEX_DETAILS, ANGEL_SYMBOL_DETAILS
from app.config.settings import get_settings
from app.core.exceptions import InvalidRequestError
from app.schemas.data_schema import AngelDataFetchRequest
from app.services.data.angel_smartapi_service import AngelSmartApiService
from app.services.data.data_loader_service import DataLoaderService
from app.services.data.instrument_master_service import InstrumentMasterService


@dataclass(frozen=True)
class MarketInstrument:
    symbol: str
    name: str
    exchange: str
    token: str
    instrument_type: str = "EQ"
    lot_size: int | None = None
    tick_size: float | None = None


class MarketDataProvider(ABC):
    name: str
    label: str

    @abstractmethod
    def search_instruments(self, query: str, exchange: str | None = None, session=None, instrument_type: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, *, symbol: str | None = None, token: str | None = None, exchange: str = "NSE", session=None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_quotes_bulk(self, instruments: list[dict[str, str]], session=None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_candles(
        self,
        *,
        symbol: str | None = None,
        token: str | None = None,
        exchange: str = "NSE",
        interval: str,
        from_date: datetime,
        to_date: datetime,
        session=None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_indices(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_market_status(self) -> dict[str, Any]:
        raise NotImplementedError


class AngelMarketDataProvider(MarketDataProvider):
    name = "angel"
    label = "Live: Angel One"

    def __init__(
        self,
        angel: AngelSmartApiService | None = None,
        instruments: InstrumentMasterService | None = None,
    ) -> None:
        self.angel = angel or AngelSmartApiService()
        self.instruments = instruments or InstrumentMasterService()

    def search_instruments(self, query: str, exchange: str | None = None, session=None, instrument_type: str | None = None) -> list[dict[str, Any]]:
        if session is None:
            return SampleMarketDataProvider().search_instruments(query, exchange)
        return [self._instrument_dict(item) for item in self.instruments.search(session, query, exchange, instrument_type=instrument_type)]

    def get_quote(self, *, symbol: str | None = None, token: str | None = None, exchange: str = "NSE", session=None) -> dict[str, Any]:
        self.angel.settings = get_settings()
        instrument = self.resolve(symbol=symbol, token=token, exchange=exchange, session=session)
        response = self.angel.fetch_ltp(
            exchange=instrument.exchange,
            symbol=self._angel_trading_symbol(instrument),
            symbol_token=instrument.token,
        )
        ltp_data = response.get("data") or {}
        daily_frame = self._try_daily_frame(instrument)
        return self._quote_from_angel(instrument, ltp_data, daily_frame)

    def get_quotes_bulk(self, instruments: list[dict[str, str]], session=None) -> list[dict[str, Any]]:
        rows = []
        for item in instruments:
            rows.append(
                self.get_quote(
                    symbol=item.get("symbol"),
                    token=item.get("token") or item.get("symbol_token"),
                    exchange=item.get("exchange") or "NSE",
                    session=session,
                )
            )
        return rows

    def get_candles(
        self,
        *,
        symbol: str | None = None,
        token: str | None = None,
        exchange: str = "NSE",
        interval: str,
        from_date: datetime,
        to_date: datetime,
        session=None,
    ) -> pd.DataFrame:
        self.angel.settings = get_settings()
        instrument = self.resolve(symbol=symbol, token=token, exchange=exchange, session=session)
        return self.angel.fetch_frame(
            AngelDataFetchRequest(
                exchange=instrument.exchange,
                symbol_token=instrument.token,
                interval=interval,
                fromdate=from_date,
                todate=to_date,
            )
        )

    def get_indices(self) -> list[dict[str, Any]]:
        self.angel.settings = get_settings()
        rows = []
        for name, details in ANGEL_INDEX_DETAILS.items():
            token = details.get("token")
            if not token:
                rows.append({"name": name, "exchange": details["exchange"], "available": False, "message": "Index token is not configured."})
                continue
            data = self.angel.fetch_ltp(exchange=details["exchange"], symbol=name, symbol_token=token).get("data") or {}
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
        return rows

    def get_market_status(self) -> dict[str, Any]:
        now = datetime.now()
        is_weekday = now.weekday() < 5
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        return {
            "exchange": "NSE/BSE",
            "is_open": bool(is_weekday and market_open <= now <= market_close),
            "checked_at": now.isoformat(timespec="seconds"),
            "source": self.name,
            "data_source": self.label,
        }

    def resolve(self, *, symbol: str | None, token: str | None, exchange: str = "NSE", session=None) -> MarketInstrument:
        found = self.instruments.resolve(session, query=symbol, exchange=exchange, token=token)
        if found is not None:
            return MarketInstrument(
                symbol=found.symbol,
                name=found.name,
                exchange=found.exchange,
                token=found.token,
                instrument_type=found.instrument_type,
                lot_size=found.lot_size,
                tick_size=found.tick_size,
            )
        normalized = self._normalize_symbol(symbol)
        if token:
            return MarketInstrument(symbol=normalized or f"TOKEN_{token}", name=(normalized or token), exchange=exchange.upper(), token=token)
        raise InvalidRequestError("Symbol is not available in the instrument master or local fallback map.")

    def _try_daily_frame(self, instrument: MarketInstrument) -> pd.DataFrame | None:
        try:
            return self.get_candles(
                symbol=instrument.symbol,
                token=instrument.token,
                exchange=instrument.exchange,
                interval="ONE_DAY",
                from_date=datetime.now() - timedelta(days=370),
                to_date=datetime.now(),
            )
        except Exception:
            return None

    def _quote_from_angel(self, instrument: MarketInstrument, ltp_data: dict[str, Any], daily_frame: pd.DataFrame | None) -> dict[str, Any]:
        latest = self._number(ltp_data.get("ltp"))
        previous_close = self._number(ltp_data.get("close"))
        open_price = self._number(ltp_data.get("open"))
        high = self._number(ltp_data.get("high"))
        low = self._number(ltp_data.get("low"))
        if daily_frame is not None and not daily_frame.empty:
            latest_row = daily_frame.iloc[-1]
            latest = latest if latest is not None else self._number(latest_row["Close"])
            previous_close = previous_close if previous_close is not None and previous_close > 0 else self._previous_close(daily_frame)
            open_price = open_price if open_price is not None else self._number(latest_row["Open"])
            high = high if high is not None else self._number(latest_row["High"])
            low = low if low is not None else self._number(latest_row["Low"])
        change = latest - previous_close if latest is not None and previous_close is not None else None
        volume = self._latest_volume(daily_frame)
        return {
            "symbol": instrument.symbol,
            "stock_name": instrument.name,
            "exchange": instrument.exchange,
            "symbol_token": instrument.token,
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
            "vwap": self._vwap(daily_frame),
            "value_traded": self._round(volume * latest) if volume is not None and latest is not None else None,
            "available": latest is not None,
        }

    def _instrument_dict(self, item: Any) -> dict[str, Any]:
        return {
            "symbol": item.symbol,
            "name": item.name,
            "exchange": item.exchange,
            "token": item.token,
            "trading_symbol": item.trading_symbol,
            "instrument_type": item.instrument_type,
            "expiry": item.expiry,
            "strike": item.strike,
            "option_type": item.option_type,
            "lot_size": item.lot_size,
            "tick_size": item.tick_size,
            "underlying": item.underlying,
            "is_equity": item.is_equity,
            "is_fno": item.is_fno,
            "is_future": item.is_future,
            "is_option": item.is_option,
        }

    def _angel_trading_symbol(self, instrument: MarketInstrument) -> str:
        if instrument.exchange == "NSE" and not instrument.symbol.endswith("-EQ"):
            return f"{instrument.symbol}-EQ"
        return instrument.symbol

    def _normalize_symbol(self, value: str | None) -> str:
        return str(value or "").strip().upper().replace(" ", "")

    def _number(self, value: Any) -> float | None:
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

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


class SampleMarketDataProvider(MarketDataProvider):
    name = "sample"
    label = "Sample"

    def __init__(self, loader: DataLoaderService | None = None) -> None:
        self.loader = loader or DataLoaderService()

    def search_instruments(self, query: str, exchange: str | None = None, session=None, instrument_type: str | None = None) -> list[dict[str, Any]]:
        normalized = str(query or "").strip().upper()
        rows = []
        for symbol, details in ANGEL_SYMBOL_DETAILS.items():
            if exchange and details["exchange"] != exchange.strip().upper():
                continue
            if normalized in symbol or normalized in details["name"].upper() or normalized in details["token"]:
                rows.append(
                    {
                        "symbol": symbol,
                        "name": details["name"],
                        "exchange": details["exchange"],
                        "token": details["token"],
                        "instrument_type": "EQ",
                        "lot_size": 1,
                        "tick_size": 0.05,
                    }
                )
        return rows

    def get_quote(self, *, symbol: str | None = None, token: str | None = None, exchange: str = "NSE", session=None) -> dict[str, Any]:
        instrument = self._resolve(symbol, token, exchange)
        frame = self._sample_frame()
        latest_row = frame.iloc[-1]
        previous_row = frame.iloc[-2] if len(frame) > 1 else latest_row
        latest = round(float(latest_row["Close"]), 2)
        previous_close = round(float(previous_row["Close"]), 2)
        change = latest - previous_close
        high = round(float(latest_row["High"]), 2)
        low = round(float(latest_row["Low"]), 2)
        volume = round(float(latest_row["Volume"]), 2)
        return {
            "symbol": instrument["symbol"],
            "stock_name": instrument["name"],
            "exchange": instrument["exchange"],
            "symbol_token": instrument["token"],
            "latest_price": latest,
            "change": round(change, 2),
            "change_pct": round((change / previous_close) * 100, 2) if previous_close else None,
            "last_updated": datetime.now().isoformat(timespec="seconds"),
            "open": round(float(latest_row["Open"]), 2),
            "high": high,
            "low": low,
            "previous_close": previous_close,
            "volume": volume,
            "day_range": f"{low} - {high}",
            "week_52_high": round(float(frame["High"].max()), 2),
            "week_52_low": round(float(frame["Low"].min()), 2),
            "vwap": self._vwap(frame),
            "value_traded": round(volume * latest, 2),
            "available": True,
        }

    def get_quotes_bulk(self, instruments: list[dict[str, str]], session=None) -> list[dict[str, Any]]:
        return [
            self.get_quote(
                symbol=item.get("symbol"),
                token=item.get("token") or item.get("symbol_token"),
                exchange=item.get("exchange") or "NSE",
            )
            for item in instruments
        ]

    def get_candles(
        self,
        *,
        symbol: str | None = None,
        token: str | None = None,
        exchange: str = "NSE",
        interval: str,
        from_date: datetime,
        to_date: datetime,
        session=None,
    ) -> pd.DataFrame:
        frame = self._sample_frame()
        frame = frame[(frame["Date"] >= pd.Timestamp(from_date)) & (frame["Date"] <= pd.Timestamp(to_date))]
        return frame if not frame.empty else self._sample_frame()

    def get_indices(self) -> list[dict[str, Any]]:
        return [
            {"name": "NIFTY 50", "exchange": "NSE", "latest_price": 22419.95, "change": 138.2, "change_pct": 0.62, "available": True},
            {"name": "SENSEX", "exchange": "BSE", "latest_price": 73912.18, "change": 353.8, "change_pct": 0.48, "available": True},
            {"name": "BANK NIFTY", "exchange": "NSE", "latest_price": 48082.35, "change": -101.4, "change_pct": -0.21, "available": True},
        ]

    def get_market_status(self) -> dict[str, Any]:
        return {
            "exchange": "NSE/BSE",
            "is_open": False,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "source": self.name,
            "data_source": self.label,
            "message": "Sample market status is not live.",
        }

    def _resolve(self, symbol: str | None, token: str | None, exchange: str) -> dict[str, str]:
        normalized = str(symbol or "").strip().upper().replace(" ", "")
        if normalized in ANGEL_SYMBOL_DETAILS:
            details = ANGEL_SYMBOL_DETAILS[normalized]
            return {"symbol": normalized, "name": details["name"], "exchange": details["exchange"], "token": details["token"]}
        if token:
            return {"symbol": normalized or f"TOKEN_{token}", "name": normalized or f"Token {token}", "exchange": exchange.upper(), "token": token}
        fallback_symbol = normalized or "SAMPLE"
        return {"symbol": fallback_symbol, "name": fallback_symbol, "exchange": exchange.upper(), "token": token or "0"}

    def _sample_frame(self) -> pd.DataFrame:
        frame = self.loader.load_sample()
        frame = frame.copy()
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        for column in ("Open", "High", "Low", "Close", "Volume"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame.dropna(subset=["Date", "Open", "High", "Low", "Close", "Volume"])

    def _vwap(self, frame: pd.DataFrame) -> float | None:
        typical_price = (frame["High"].astype(float) + frame["Low"].astype(float) + frame["Close"].astype(float)) / 3
        volume = frame["Volume"].astype(float)
        total_volume = volume.sum()
        if total_volume == 0:
            return None
        return round(float((typical_price * volume).sum() / total_volume), 2)
