from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlmodel import Session, func, select

from app.config.constants import MARKET_WATCH_SECTOR_MAP
from app.models.instrument_master_model import FnoUnderlying, InstrumentMaster
from app.models.market_data_model import FnoQuoteCache


FUNDAMENTALS_WARNING = "Fundamental fields require fundamentals data source."
INSTRUMENT_SYNC_WARNING = "Instrument master not synced. Run instrument sync first."
QUOTE_REFRESH_WARNING = "F&O live quotes use the cached quote snapshot. Run refresh to update."
CACHE_STALE_AFTER_SECONDS = 300


class StocksService:
    SORT_FIELDS = {"symbol", "percent_change", "volume", "market_cap", "pe", "eps"}

    def list_stocks(
        self,
        session: Session,
        *,
        universe: str = "fno",
        exchange: str = "ALL",
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "symbol",
        sort_direction: str = "asc",
    ) -> dict[str, Any]:
        universe = (universe or "fno").strip().lower()
        exchange = (exchange or "ALL").strip().upper()
        limit = min(max(int(limit), 1), 250)
        offset = max(int(offset), 0)
        sort_by = sort_by if sort_by in self.SORT_FIELDS else "symbol"
        sort_direction = "desc" if sort_direction.lower() == "desc" else "asc"

        quote_rows = self._quote_map(session)
        fno_symbols = self._fno_symbol_set(session)
        warnings = [FUNDAMENTALS_WARNING]

        if universe == "fno":
            rows, source, message = self._fno_rows(session, quote_rows, search)
            if message:
                warnings.append(message)
            if source == "Angel Instrument Master":
                warnings.append(QUOTE_REFRESH_WARNING)
        elif universe in {"all", "nse", "bse"}:
            rows, source, message = self._equity_rows(session, quote_rows, fno_symbols, universe, exchange, search)
            if message:
                warnings.append(message)
        elif universe in {"nifty50", "nifty_50", "nifty 50"}:
            rows = []
            source = "Unavailable"
            warnings.append("Nifty 50 stock universe is not available from the instrument master yet.")
        else:
            rows, source, message = self._equity_rows(session, quote_rows, fno_symbols, "all", exchange, search)
            if message:
                warnings.append(message)

        if exchange in {"NSE", "BSE"} and universe == "fno":
            rows = [row for row in rows if row["exchange"] == exchange]

        rows = self._sort(rows, sort_by, sort_direction)
        total = len(rows)
        page = rows[offset : offset + limit]
        latest = self._latest_updated(page)

        return {
            "rows": page,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data_source": source,
            "last_updated": latest,
            "warnings": list(dict.fromkeys(warnings)),
        }

    def _equity_rows(
        self,
        session: Session,
        quote_rows: dict[str, FnoQuoteCache],
        fno_symbols: set[str],
        universe: str,
        exchange: str,
        search: str | None,
    ) -> tuple[list[dict[str, Any]], str, str | None]:
        statement = select(InstrumentMaster).where(InstrumentMaster.is_equity == True)  # noqa: E712
        if universe in {"nse", "bse"}:
            statement = statement.where(InstrumentMaster.exchange == universe.upper())
        elif exchange in {"NSE", "BSE"}:
            statement = statement.where(InstrumentMaster.exchange == exchange)
        else:
            statement = statement.where(InstrumentMaster.exchange.in_(["NSE", "BSE"]))
        if search:
            pattern = f"%{search.strip().upper()}%"
            statement = statement.where(
                or_(
                    InstrumentMaster.symbol.ilike(pattern),
                    InstrumentMaster.name.ilike(pattern),
                    InstrumentMaster.exchange.ilike(pattern),
                    InstrumentMaster.token.ilike(pattern),
                    InstrumentMaster.trading_symbol.ilike(pattern),
                )
            )
        instruments = list(session.exec(statement))
        if not instruments:
            total_equities = session.exec(
                select(func.count()).select_from(InstrumentMaster).where(InstrumentMaster.is_equity == True)  # noqa: E712
            ).one()
            message = INSTRUMENT_SYNC_WARNING if not total_equities else None
            return [], "Angel Instrument Master" if total_equities else "Unavailable", message
        return [self._row_from_instrument(row, quote_rows.get(row.symbol), row.symbol in fno_symbols) for row in instruments], "Angel Instrument Master", None

    def _fno_rows(
        self,
        session: Session,
        quote_rows: dict[str, FnoQuoteCache],
        search: str | None,
    ) -> tuple[list[dict[str, Any]], str, str | None]:
        statement = select(FnoUnderlying)
        if search:
            pattern = f"%{search.strip().upper()}%"
            statement = statement.where(
                or_(
                    FnoUnderlying.symbol.ilike(pattern),
                    FnoUnderlying.name.ilike(pattern),
                    FnoUnderlying.exchange.ilike(pattern),
                    FnoUnderlying.equity_token.ilike(pattern),
                    FnoUnderlying.nearest_future_token.ilike(pattern),
                )
            )
        underlyings = list(session.exec(statement))
        if not underlyings:
            real_fno_count = session.exec(
                select(func.count())
                .select_from(InstrumentMaster)
                .where(InstrumentMaster.exchange == "NFO")
                .where(InstrumentMaster.is_fno == True)  # noqa: E712
            ).one()
            message = INSTRUMENT_SYNC_WARNING if not real_fno_count else "No F&O underlyings were derived from the synced instrument master."
            return [], "Unavailable", message
        return [self._row_from_underlying(row, quote_rows.get(row.symbol)) for row in underlyings], "Angel Instrument Master", None

    def _quote_map(self, session: Session) -> dict[str, FnoQuoteCache]:
        return {row.symbol: row for row in session.exec(select(FnoQuoteCache))}

    def _fno_symbol_set(self, session: Session) -> set[str]:
        return {symbol for symbol in session.exec(select(FnoUnderlying.symbol))}

    def _row_from_instrument(self, row: InstrumentMaster, quote: FnoQuoteCache | None, is_fno: bool) -> dict[str, Any]:
        return self._stock_row(
            symbol=row.symbol,
            name=row.name,
            exchange=row.exchange,
            token=row.token,
            is_fno=is_fno,
            quote=quote,
            fallback_source="Angel Instrument Master",
            fallback_updated=row.updated_at,
        )

    def _row_from_underlying(self, row: FnoUnderlying, quote: FnoQuoteCache | None) -> dict[str, Any]:
        return self._stock_row(
            symbol=row.symbol,
            name=row.name,
            exchange=row.exchange,
            token=row.equity_token or row.nearest_future_token,
            is_fno=True,
            quote=quote,
            fallback_source="Angel Instrument Master",
            fallback_updated=row.updated_at,
        )

    def _stock_row(
        self,
        *,
        symbol: str,
        name: str,
        exchange: str,
        token: str | None,
        is_fno: bool,
        quote: FnoQuoteCache | None,
        fallback_source: str,
        fallback_updated: datetime,
    ) -> dict[str, Any]:
        source = self._quote_source(quote) if quote else fallback_source
        last_updated = quote.last_updated if quote else fallback_updated
        return {
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            "token": token,
            "is_fno": is_fno,
            "open": quote.open if quote else None,
            "high": quote.high if quote else None,
            "low": quote.low if quote else None,
            "ltp": quote.ltp if quote else None,
            "previous_close": quote.previous_close if quote else None,
            "volume": quote.volume if quote else None,
            "point_change": quote.point_change if quote else None,
            "percent_change": quote.percent_change if quote else None,
            "market_cap": None,
            "pe": None,
            "eps": None,
            "sector": MARKET_WATCH_SECTOR_MAP.get(symbol),
            "source": source,
            "last_updated": last_updated.isoformat(timespec="seconds") if last_updated else None,
        }

    def _quote_source(self, quote: FnoQuoteCache) -> str:
        if quote.last_updated < datetime.utcnow() - timedelta(seconds=CACHE_STALE_AFTER_SECONDS):
            return "Stale"
        return "Live: Angel One" if quote.source == "Live: Angel One" else "Cached"

    def _sort(self, rows: list[dict[str, Any]], sort_by: str, sort_direction: str) -> list[dict[str, Any]]:
        reverse = sort_direction == "desc"

        def key(row: dict[str, Any]) -> tuple[int, Any]:
            value = row.get(sort_by)
            if value is None:
                return (1, "")
            return (0, value)

        present = [row for row in rows if row.get(sort_by) is not None]
        missing = [row for row in rows if row.get(sort_by) is None]
        return sorted(present, key=key, reverse=reverse) + sorted(missing, key=lambda row: row["symbol"])

    def _latest_updated(self, rows: list[dict[str, Any]]) -> str | None:
        values = [row["last_updated"] for row in rows if row.get("last_updated")]
        return max(values) if values else None
