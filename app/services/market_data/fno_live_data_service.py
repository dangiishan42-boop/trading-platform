from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlmodel import Session, func, select

from app.config.settings import get_settings
from app.core.logger import get_logger
from app.models.instrument_master_model import FnoUnderlying, InstrumentMaster
from app.models.market_data_model import FnoQuoteCache
from app.services.data.angel_smartapi_service import AngelSmartApiService
from app.services.data.instrument_master_service import InstrumentMasterService

logger = get_logger(__name__)

EMPTY_FNO_MESSAGE = "F&O instrument master not synced. Run instrument sync first."
CACHE_STALE_AFTER_SECONDS = 300


@dataclass
class ResolvedFnoInstrument:
    symbol: str
    name: str
    exchange: str
    token: str
    trading_symbol: str


class FnoLiveDataService:
    def __init__(
        self,
        angel: AngelSmartApiService | None = None,
        instruments: InstrumentMasterService | None = None,
    ) -> None:
        self.angel = angel or AngelSmartApiService()
        self.instruments = instruments or InstrumentMasterService()
        self.settings = get_settings()
        self._last_status: dict[str, Any] = {
            "total_fno_symbols": 0,
            "refreshed_count": 0,
            "failed_count": 0,
            "cached_count": 0,
            "last_refresh_time": None,
            "failures_sample": [],
            "provider_status": "Not refreshed",
        }

    def refresh(
        self,
        session: Session,
        *,
        batch_size: int | None = None,
        batch_delay_seconds: float | None = None,
        batch_timeout_seconds: float | None = None,
        retry_count: int | None = None,
    ) -> dict[str, Any]:
        batch_size = batch_size or self.settings.fno_live_batch_size
        batch_delay_seconds = self.settings.fno_live_batch_delay_seconds if batch_delay_seconds is None else batch_delay_seconds
        batch_timeout_seconds = self.settings.fno_live_batch_timeout_seconds if batch_timeout_seconds is None else batch_timeout_seconds
        retry_count = self.settings.fno_live_retry_count if retry_count is None else retry_count

        universe_payload = self.instruments.fno_underlyings(session, limit=5000)
        if universe_payload["source"] != "Angel Instrument Master" or not universe_payload["items"]:
            status = self._status(
                total=0,
                refreshed=0,
                failed=0,
                failures=[{"symbol": None, "message": EMPTY_FNO_MESSAGE}],
                provider_status=EMPTY_FNO_MESSAGE,
                session=session,
            )
            self._last_status = status
            return status

        if not self.angel.has_credentials():
            status = self._status(
                total=universe_payload["total"],
                refreshed=0,
                failed=universe_payload["total"],
                failures=[{"symbol": None, "message": "Angel One credentials not configured"}],
                provider_status="Angel One credentials not configured",
                session=session,
            )
            self._last_status = status
            return status

        resolved, failures = self._resolve_underlyings(session, universe_payload["items"])
        refreshed_count = 0
        rate_limited = False
        now = datetime.utcnow()

        for index in range(0, len(resolved), batch_size):
            batch = resolved[index : index + batch_size]
            batch_started = time.monotonic()
            batch_success = False
            last_error: Exception | None = None
            for attempt in range(retry_count + 1):
                try:
                    response = self.angel.fetch_ltp_batch([item.__dict__ for item in batch])
                    refreshed_count += self._store_batch(session, batch, response, now)
                    batch_success = True
                    break
                except Exception as exc:
                    last_error = exc
                    if self._is_rate_limited(exc):
                        rate_limited = True
                        break
                    if attempt < retry_count:
                        time.sleep(min(1.0, batch_delay_seconds))
            if not batch_success:
                for item in batch:
                    failures.append({"symbol": item.symbol, "message": str(last_error or "Angel One quote fetch failed")})
                    self._mark_failure(session, item.symbol, str(last_error or "Angel One quote fetch failed"))
                session.commit()
            if rate_limited:
                break
            if time.monotonic() - batch_started > batch_timeout_seconds:
                logger.warning("F&O live quote batch exceeded timeout", extra={"event_name": "fno_live_batch_timeout", "event_fields": {"batch_size": len(batch)}})
            if index + batch_size < len(resolved) and batch_delay_seconds > 0:
                time.sleep(batch_delay_seconds)

        provider_status = "Rate limited by Angel One; preserved existing cache" if rate_limited else "OK"
        status = self._status(
            total=universe_payload["total"],
            refreshed=refreshed_count,
            failed=len(failures),
            failures=failures,
            provider_status=provider_status,
            session=session,
        )
        self._last_status = status
        return status

    def status(self, session: Session) -> dict[str, Any]:
        total_payload = self.instruments.fno_underlyings(session, limit=1)
        total = total_payload["total"] if total_payload["source"] == "Angel Instrument Master" else 0
        cached_count = self._cached_count(session)
        latest = session.exec(select(func.max(FnoQuoteCache.last_updated))).one()
        provider_status = self._last_status.get("provider_status") or "OK"
        if total_payload["source"] != "Angel Instrument Master":
            provider_status = EMPTY_FNO_MESSAGE
        return {
            **self._last_status,
            "total_fno_symbols": total,
            "cached_count": cached_count,
            "last_refresh_time": latest.isoformat(timespec="seconds") if latest else self._last_status.get("last_refresh_time"),
            "provider_status": provider_status,
        }

    def cached_quotes(
        self,
        session: Session,
        *,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        sort_by: str = "symbol",
        sort_direction: str = "asc",
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), 500)
        offset = max(offset, 0)
        statement = select(FnoQuoteCache)
        if search:
            pattern = f"%{search.strip().upper()}%"
            statement = statement.where(or_(FnoQuoteCache.symbol.ilike(pattern), FnoQuoteCache.name.ilike(pattern)))
        total = session.exec(select(func.count()).select_from(statement.subquery())).one()
        sort_columns = {
            "symbol": FnoQuoteCache.symbol,
            "ltp": FnoQuoteCache.ltp,
            "percent_change": FnoQuoteCache.percent_change,
            "point_change": FnoQuoteCache.point_change,
            "volume": FnoQuoteCache.volume,
            "last_updated": FnoQuoteCache.last_updated,
        }
        sort_column = sort_columns.get(sort_by, FnoQuoteCache.symbol)
        if sort_direction.lower() == "desc":
            sort_column = sort_column.desc()
        rows = list(session.exec(statement.order_by(sort_column).offset(offset).limit(limit)))
        return {
            "items": [self._cache_row(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
            "source": "Cached",
            "message": None if rows else "No cached F&O live quotes available. Run refresh first.",
        }

    def cached_snapshot(self, session: Session, limit: int = 5000) -> list[dict[str, Any]]:
        return self.cached_quotes(session, limit=limit, offset=0, sort_by="symbol")["items"]

    def _resolve_underlyings(self, session: Session, underlyings: list[FnoUnderlying]) -> tuple[list[ResolvedFnoInstrument], list[dict[str, str]]]:
        resolved: list[ResolvedFnoInstrument] = []
        failures: list[dict[str, str]] = []
        for item in underlyings:
            token = item.equity_token or item.nearest_future_token
            if not token:
                failures.append({"symbol": item.symbol, "message": "Token missing"})
                self._mark_failure(session, item.symbol, "Token missing")
                continue
            exchange = "NSE" if item.equity_token else "NFO"
            instrument = self._instrument_by_token(session, exchange, token)
            trading_symbol = self._trading_symbol(item.symbol, exchange, instrument)
            resolved.append(
                ResolvedFnoInstrument(
                    symbol=item.symbol,
                    name=item.name,
                    exchange=exchange,
                    token=token,
                    trading_symbol=trading_symbol,
                )
            )
        session.commit()
        return resolved, failures

    def _store_batch(self, session: Session, batch: list[ResolvedFnoInstrument], response: dict[str, Any], now: datetime) -> int:
        fetched = self._fetched_rows(response)
        by_token = {str(row.get("symbolToken") or row.get("symboltoken") or row.get("token") or ""): row for row in fetched}
        refreshed = 0
        for item in batch:
            row = by_token.get(item.token)
            if not row:
                self._mark_failure(session, item.symbol, "Angel One returned no quote for symbol")
                continue
            quote = self._quote_values(row)
            cache = session.exec(select(FnoQuoteCache).where(FnoQuoteCache.symbol == item.symbol)).first()
            if cache is None:
                cache = FnoQuoteCache(symbol=item.symbol)
                session.add(cache)
            cache.name = item.name
            cache.exchange = item.exchange
            cache.token = item.token
            cache.ltp = quote["ltp"]
            cache.open = quote["open"]
            cache.high = quote["high"]
            cache.low = quote["low"]
            cache.previous_close = quote["previous_close"]
            cache.point_change = quote["point_change"]
            cache.percent_change = quote["percent_change"]
            cache.volume = quote["volume"]
            cache.last_updated = now
            cache.source = "Live: Angel One"
            cache.failure_message = None
            refreshed += 1
        session.commit()
        return refreshed

    def _mark_failure(self, session: Session, symbol: str, message: str) -> None:
        cache = session.exec(select(FnoQuoteCache).where(FnoQuoteCache.symbol == symbol)).first()
        if cache is not None:
            cache.source = "Cached"
            cache.failure_message = message[:500]

    def _status(
        self,
        *,
        total: int,
        refreshed: int,
        failed: int,
        failures: list[dict[str, Any]],
        provider_status: str,
        session: Session,
    ) -> dict[str, Any]:
        latest = session.exec(select(func.max(FnoQuoteCache.last_updated))).one()
        return {
            "total_fno_symbols": total,
            "refreshed_count": refreshed,
            "failed_count": failed,
            "cached_count": self._cached_count(session),
            "last_refresh_time": latest.isoformat(timespec="seconds") if latest else None,
            "failures_sample": failures[:10],
            "provider_status": provider_status,
        }

    def _cached_count(self, session: Session) -> int:
        return session.exec(select(func.count()).select_from(FnoQuoteCache)).one()

    def _instrument_by_token(self, session: Session, exchange: str, token: str) -> InstrumentMaster | None:
        return session.exec(select(InstrumentMaster).where(InstrumentMaster.exchange == exchange).where(InstrumentMaster.token == token).limit(1)).first()

    def _trading_symbol(self, symbol: str, exchange: str, instrument: InstrumentMaster | None) -> str:
        if instrument and instrument.trading_symbol:
            return instrument.trading_symbol
        if instrument and instrument.symbol:
            return instrument.symbol if exchange != "NSE" else f"{instrument.symbol}-EQ"
        return f"{symbol}-EQ" if exchange == "NSE" else symbol

    def _fetched_rows(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        data = response.get("data") or {}
        if isinstance(data, dict):
            fetched = data.get("fetched")
            if isinstance(fetched, list):
                return [row for row in fetched if isinstance(row, dict)]
            if any(key in data for key in ("ltp", "lastPrice", "symbolToken")):
                return [data]
        return []

    def _quote_values(self, row: dict[str, Any]) -> dict[str, float | None]:
        ltp = self._number(row.get("ltp"), row.get("lastPrice"), row.get("last_price"))
        previous_close = self._number(row.get("close"), row.get("previousClose"), row.get("previous_close"))
        point_change = self._number(row.get("netChange"), row.get("point_change"))
        if point_change is None and ltp is not None and previous_close is not None:
            point_change = round(ltp - previous_close, 2)
        percent_change = self._number(row.get("percentChange"), row.get("perChange"), row.get("percent_change"))
        if percent_change is None and point_change is not None and previous_close:
            percent_change = round((point_change / previous_close) * 100, 2)
        return {
            "ltp": ltp,
            "open": self._number(row.get("open")),
            "high": self._number(row.get("high")),
            "low": self._number(row.get("low")),
            "previous_close": previous_close,
            "point_change": point_change,
            "percent_change": percent_change,
            "volume": self._number(row.get("tradeVolume"), row.get("volume"), row.get("totalTradedVolume")),
        }

    def _cache_row(self, row: FnoQuoteCache) -> dict[str, Any]:
        stale = row.last_updated < datetime.utcnow() - timedelta(seconds=CACHE_STALE_AFTER_SECONDS)
        source = "Cached/Stale" if stale else ("Cached" if row.source != "Live: Angel One" else row.source)
        return {
            "symbol": row.symbol,
            "name": row.name or row.symbol,
            "exchange": row.exchange,
            "token": row.token,
            "symbol_token": row.token,
            "ltp": row.ltp,
            "latest_price": row.ltp,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "previous_close": row.previous_close,
            "point_change": row.point_change,
            "change": row.point_change,
            "percent_change": row.percent_change,
            "change_pct": row.percent_change,
            "volume": row.volume,
            "last_updated": row.last_updated.isoformat(timespec="seconds"),
            "source": source,
            "data_source": source,
            "data_source_badge": source,
            "is_cached": source != "Live: Angel One",
            "is_stale": stale,
            "available": row.ltp is not None,
            "message": row.failure_message,
        }

    def _is_rate_limited(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "rate" in message and ("limit" in message or "exceed" in message or "429" in message)

    def _number(self, *values: Any) -> float | None:
        for value in values:
            try:
                if value in (None, ""):
                    continue
                return round(float(value), 2)
            except (TypeError, ValueError):
                continue
        return None


_FNO_LIVE_SERVICE: FnoLiveDataService | None = None


def get_fno_live_data_service() -> FnoLiveDataService:
    global _FNO_LIVE_SERVICE
    if _FNO_LIVE_SERVICE is None:
        _FNO_LIVE_SERVICE = FnoLiveDataService()
    return _FNO_LIVE_SERVICE
