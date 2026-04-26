from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.config.paths import DATA_DIR
from app.services.market_data.providers import AngelMarketDataProvider, MarketDataProvider, SampleMarketDataProvider


@dataclass
class QuoteCacheEntry:
    value: dict[str, Any]
    expires_at: datetime


class MarketDataEngine:
    QUOTE_TTL_SECONDS = 15

    def __init__(
        self,
        primary: MarketDataProvider | None = None,
        fallback: MarketDataProvider | None = None,
        candle_cache_dir: Path | None = None,
    ) -> None:
        self.primary = primary or AngelMarketDataProvider()
        self.fallback = fallback or SampleMarketDataProvider()
        self.quote_cache: dict[str, QuoteCacheEntry] = {}
        self.candle_cache_dir = candle_cache_dir or DATA_DIR / "cache" / "candles"
        self.candle_cache_dir.mkdir(parents=True, exist_ok=True)

    def search_instruments(self, query: str, exchange: str | None = None, session=None) -> dict[str, Any]:
        try:
            rows = self.primary.search_instruments(query, exchange, session=session)
            return {"items": rows, **self._source_meta(self.primary)}
        except Exception as exc:
            rows = self.fallback.search_instruments(query, exchange, session=session)
            return {"items": rows, **self._source_meta(self.fallback, message=str(exc))}

    def get_quote(self, *, symbol: str | None = None, token: str | None = None, exchange: str = "NSE", session=None) -> dict[str, Any]:
        key = self._quote_key(symbol, token, exchange)
        cached = self._fresh_quote(key)
        if cached is not None:
            return {**cached, **self._source_meta(self.primary, status="Cached", cached=True)}

        stale = self.quote_cache.get(key)
        try:
            quote = self.primary.get_quote(symbol=symbol, token=token, exchange=exchange, session=session)
            quote = {**quote, **self._source_meta(self.primary)}
            self.quote_cache[key] = QuoteCacheEntry(quote, datetime.now() + timedelta(seconds=self.QUOTE_TTL_SECONDS))
            return quote
        except Exception as exc:
            if stale is not None:
                return {**stale.value, **self._source_meta(self.primary, status="Cached", cached=True, message=f"Live fetch failed: {exc}")}
            fallback_quote = self.fallback.get_quote(symbol=symbol, token=token, exchange=exchange, session=session)
            return {**fallback_quote, **self._source_meta(self.fallback, message=f"Live fetch failed: {exc}")}

    def get_quotes_bulk(self, instruments: list[dict[str, str]], session=None) -> dict[str, Any]:
        return {"items": [self.get_quote(symbol=i.get("symbol"), token=i.get("token") or i.get("symbol_token"), exchange=i.get("exchange") or "NSE", session=session) for i in instruments]}

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
    ) -> dict[str, Any]:
        cache_path = self._candle_cache_path(symbol, token, exchange, interval, from_date, to_date)
        if cache_path.exists() and not self._primary_has_credentials():
            return {"frame": self._read_candle_cache(cache_path), **self._source_meta(self.primary, status="Cached", cached=True)}
        try:
            frame = self.primary.get_candles(
                symbol=symbol,
                token=token,
                exchange=exchange,
                interval=interval,
                from_date=from_date,
                to_date=to_date,
                session=session,
            )
            self._write_candle_cache(cache_path, frame)
            return {"frame": frame, **self._source_meta(self.primary)}
        except Exception as exc:
            cached = self._find_latest_candle_cache(symbol, token, exchange, interval)
            if cached is not None:
                return {"frame": self._read_candle_cache(cached), **self._source_meta(self.primary, status="Cached", cached=True, message=f"Live fetch failed: {exc}")}
            frame = self.fallback.get_candles(
                symbol=symbol,
                token=token,
                exchange=exchange,
                interval=interval,
                from_date=from_date,
                to_date=to_date,
                session=session,
            )
            return {"frame": frame, **self._source_meta(self.fallback, message=f"Live fetch failed: {exc}")}

    def get_indices(self) -> list[dict[str, Any]]:
        try:
            return [
                {
                    **row,
                    **self._source_meta(
                        self.primary,
                        status=None if row.get("available") else "Unavailable",
                        message=row.get("message") if not row.get("available") else None,
                    ),
                }
                for row in self.primary.get_indices()
            ]
        except Exception as exc:
            return [{**row, **self._source_meta(self.fallback, message=f"Live fetch failed: {exc}")} for row in self.fallback.get_indices()]

    def get_market_status(self) -> dict[str, Any]:
        try:
            return self.primary.get_market_status()
        except Exception as exc:
            return {**self.fallback.get_market_status(), "message": f"Live status failed: {exc}"}

    def _source_meta(self, provider: MarketDataProvider, *, status: str | None = None, cached: bool = False, message: str | None = None) -> dict[str, Any]:
        label = status or provider.label
        return {
            "source": provider.name,
            "data_source": label,
            "data_source_badge": label,
            "data_source_note": self._source_note(label, message),
            "is_cached": cached,
            "message": message,
        }

    def _source_note(self, label: str, message: str | None) -> str:
        if label == "Live: Angel One":
            return "Showing live Angel One market data where available."
        if label == "Cached":
            return "Showing cached market data because a fresh value was unavailable or recently fetched."
        if label == "Sample":
            return "Showing sample/local market data. Configure Angel One credentials for live data."
        if label == "Unavailable":
            return message or "Live market data is unavailable for this instrument."
        return message or "Market data provider returned an error."

    def _primary_has_credentials(self) -> bool:
        angel = getattr(self.primary, "angel", None)
        if angel is None or not hasattr(angel, "has_credentials"):
            return False
        try:
            from app.config.settings import get_settings

            angel.settings = get_settings()
            return bool(angel.has_credentials())
        except Exception:
            return False

    def _fresh_quote(self, key: str) -> dict[str, Any] | None:
        entry = self.quote_cache.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now():
            return None
        return entry.value

    def _quote_key(self, symbol: str | None, token: str | None, exchange: str) -> str:
        return "|".join([exchange.upper(), str(symbol or "").upper(), str(token or "")])

    def _candle_cache_path(self, symbol: str | None, token: str | None, exchange: str, interval: str, from_date: datetime, to_date: datetime) -> Path:
        key = "|".join([exchange.upper(), str(symbol or "").upper(), str(token or ""), interval, from_date.isoformat(), to_date.isoformat()])
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        readable = "_".join(part for part in [exchange.upper(), str(symbol or token or "UNKNOWN").upper(), interval] if part)
        return self.candle_cache_dir / f"{readable}_{digest}.csv"

    def _find_latest_candle_cache(self, symbol: str | None, token: str | None, exchange: str, interval: str) -> Path | None:
        readable = "_".join(part for part in [exchange.upper(), str(symbol or token or "UNKNOWN").upper(), interval] if part)
        matches = sorted(self.candle_cache_dir.glob(f"{readable}_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
        return matches[0] if matches else None

    def _read_candle_cache(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(path)

    def _write_candle_cache(self, path: Path, frame: pd.DataFrame) -> None:
        frame.to_csv(path, index=False)


_ENGINE: MarketDataEngine | None = None


def get_market_data_engine() -> MarketDataEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = MarketDataEngine()
    return _ENGINE
