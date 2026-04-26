from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy import delete, or_
from sqlmodel import Session, select

from app.config.constants import ANGEL_SYMBOL_DETAILS
from app.core.exceptions import DataValidationError, InvalidRequestError
from app.models.instrument_master_model import FnoUnderlying, InstrumentMaster


DEFAULT_ANGEL_SCRIP_MASTER_URL = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
)


class InstrumentMasterService:
    EXCHANGES = {"NSE", "BSE", "NFO"}
    EQUITY_TYPES = {"", "EQ", "EQUITY"}
    FUTURE_TYPES = {"FUTSTK", "FUTIDX", "FUT"}
    OPTION_TYPES = {"OPTSTK", "OPTIDX", "OPT"}

    def fetch_master_payload(self, source_url: str = DEFAULT_ANGEL_SCRIP_MASTER_URL) -> list[dict[str, Any]]:
        try:
            with urlopen(source_url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise InvalidRequestError(f"Instrument sync failed: unable to fetch or parse master JSON ({exc})") from exc

        if not isinstance(payload, list):
            raise DataValidationError("Instrument sync failed: master JSON must be a list")
        return payload

    def sync(self, session: Session, source_url: str = DEFAULT_ANGEL_SCRIP_MASTER_URL) -> int:
        records = self.parse_records(self.fetch_master_payload(source_url))
        session.exec(delete(InstrumentMaster))
        session.exec(delete(FnoUnderlying))
        if records:
            session.add_all(records)
        session.flush()
        underlyings = self.derive_fno_underlyings(records)
        if underlyings:
            session.add_all(underlyings)
        session.commit()
        return len(records)

    def parse_records(self, payload: list[dict[str, Any]]) -> list[InstrumentMaster]:
        records: list[InstrumentMaster] = []
        seen: set[tuple[str, str]] = set()
        now = datetime.utcnow()

        for raw in payload:
            record = self._parse_record(raw, now)
            if record is None:
                continue
            key = (record.exchange, record.token)
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

        return records

    def search(self, session: Session, q: str, exchange: str | None = None, limit: int = 20, instrument_type: str | None = None) -> list[InstrumentMaster]:
        normalized_q = q.strip()
        if not normalized_q:
            return []

        statement = select(InstrumentMaster)
        if exchange:
            statement = statement.where(InstrumentMaster.exchange == exchange.strip().upper())
        if instrument_type:
            normalized_type = instrument_type.strip().lower()
            if normalized_type in {"fno", "fo"}:
                statement = statement.where(InstrumentMaster.is_fno == True)  # noqa: E712
            elif normalized_type in {"equity", "eq"}:
                statement = statement.where(InstrumentMaster.is_equity == True)  # noqa: E712
            elif normalized_type in {"future", "futures"}:
                statement = statement.where(InstrumentMaster.is_future == True)  # noqa: E712
            elif normalized_type in {"option", "options"}:
                statement = statement.where(InstrumentMaster.is_option == True)  # noqa: E712

        pattern = f"%{normalized_q.upper()}%"
        statement = (
            statement.where(
                or_(
                    InstrumentMaster.symbol.ilike(pattern),
                    InstrumentMaster.name.ilike(pattern),
                    InstrumentMaster.token.ilike(pattern),
                    InstrumentMaster.trading_symbol.ilike(pattern),
                    InstrumentMaster.underlying.ilike(pattern),
                )
            )
            .order_by(InstrumentMaster.exchange, InstrumentMaster.symbol)
            .limit(limit)
        )
        return list(session.exec(statement))

    def fno_underlyings(self, session: Session, q: str | None = None, limit: int = 500) -> list[FnoUnderlying]:
        statement = select(FnoUnderlying)
        if q:
            pattern = f"%{q.strip().upper()}%"
            statement = statement.where(or_(FnoUnderlying.symbol.ilike(pattern), FnoUnderlying.name.ilike(pattern)))
        statement = statement.order_by(FnoUnderlying.symbol).limit(limit)
        rows = list(session.exec(statement))
        if rows:
            return rows
        return self._fallback_fno_underlyings()

    def fno_contracts(self, session: Session, symbol: str) -> dict[str, list[InstrumentMaster]]:
        normalized = self._normalize_symbol(symbol)
        statement = (
            select(InstrumentMaster)
            .where(InstrumentMaster.exchange == "NFO")
            .where(InstrumentMaster.underlying == normalized)
            .order_by(InstrumentMaster.expiry, InstrumentMaster.strike, InstrumentMaster.option_type)
        )
        rows = list(session.exec(statement))
        return {
            "futures": [row for row in rows if row.is_future],
            "options": [row for row in rows if row.is_option],
        }

    def fno_expiries(self, session: Session, symbol: str) -> list[str]:
        contracts = self.fno_contracts(session, symbol)
        expiries = {row.expiry for rows in contracts.values() for row in rows if row.expiry}
        return sorted(expiries)

    def derive_fno_underlyings(self, records: list[InstrumentMaster]) -> list[FnoUnderlying]:
        equity_by_symbol = {row.symbol: row for row in records if row.is_equity and row.exchange == "NSE"}
        grouped: dict[str, list[InstrumentMaster]] = {}
        for row in records:
            if row.exchange == "NFO" and row.is_fno and row.underlying and row.instrument_type in {"FUTSTK", "OPTSTK"}:
                grouped.setdefault(row.underlying, []).append(row)
        underlyings: list[FnoUnderlying] = []
        now = datetime.utcnow()
        for symbol, rows in grouped.items():
            futures = [row for row in rows if row.is_future]
            options = [row for row in rows if row.is_option]
            expiries = sorted({row.expiry for row in rows if row.expiry})
            nearest_future = sorted(futures, key=lambda row: row.expiry or "")[0] if futures else None
            equity = equity_by_symbol.get(symbol)
            lot_size = (nearest_future or rows[0]).lot_size
            underlyings.append(
                FnoUnderlying(
                    symbol=symbol,
                    name=(equity.name if equity else rows[0].name or symbol),
                    exchange="NSE",
                    equity_token=equity.token if equity else None,
                    nearest_future_token=nearest_future.token if nearest_future else None,
                    active_expiries=",".join(expiries),
                    has_futures=bool(futures),
                    has_options=bool(options),
                    lot_size=lot_size,
                    updated_at=now,
                )
            )
        return sorted(underlyings, key=lambda row: row.symbol)

    def get_by_token(self, session: Session, token: str) -> InstrumentMaster | None:
        return session.exec(select(InstrumentMaster).where(InstrumentMaster.token == token).limit(1)).first()

    def resolve(
        self,
        session: Session | None,
        *,
        query: str | None,
        exchange: str = "NSE",
        token: str | None = None,
    ) -> InstrumentMaster | None:
        if session is not None and token:
            found = self.get_by_token(session, token)
            if found:
                return found

        normalized_query = self._normalize_symbol(query)
        if session is not None and normalized_query:
            statement = select(InstrumentMaster).where(InstrumentMaster.symbol == normalized_query)
            if exchange:
                statement = statement.where(InstrumentMaster.exchange == exchange.strip().upper())
            found = session.exec(statement.limit(1)).first()
            if found:
                return found

        if normalized_query in ANGEL_SYMBOL_DETAILS:
            details = ANGEL_SYMBOL_DETAILS[normalized_query]
            return InstrumentMaster(
                exchange=details["exchange"],
                symbol=normalized_query,
                name=details["name"],
                token=details["token"],
                instrument_type="EQ",
                lot_size=1,
                tick_size=None,
                is_equity=True,
            )
        return None

    def _parse_record(self, raw: dict[str, Any], updated_at: datetime) -> InstrumentMaster | None:
        exchange = str(raw.get("exch_seg") or raw.get("exchange") or "").strip().upper()
        if exchange not in self.EXCHANGES:
            return None

        instrument_type = str(raw.get("instrumenttype") or raw.get("instrument_type") or "").strip().upper()
        is_equity = exchange in {"NSE", "BSE"} and instrument_type in self.EQUITY_TYPES
        is_future = exchange == "NFO" and instrument_type in self.FUTURE_TYPES
        is_option = exchange == "NFO" and instrument_type in self.OPTION_TYPES
        is_fno = is_future or is_option
        if not is_equity and not is_fno:
            return None

        token = str(raw.get("token") or "").strip()
        raw_symbol = str(raw.get("symbol") or "").strip().upper()
        name = str(raw.get("name") or raw_symbol).strip()
        if not token or not raw_symbol:
            return None

        symbol = self._normalize_symbol(raw_symbol)
        if exchange == "NSE" and raw_symbol.endswith("-EQ"):
            symbol = symbol.removesuffix("-EQ")
        underlying = self._underlying(raw, symbol, name, instrument_type, exchange)
        option_type = self._option_type(raw_symbol, instrument_type)

        return InstrumentMaster(
            exchange=exchange,
            symbol=underlying if is_fno and underlying else symbol,
            name=name or symbol,
            token=token,
            trading_symbol=raw_symbol,
            instrument_type=instrument_type or "EQ",
            expiry=self._expiry(raw.get("expiry")),
            strike=self._strike(raw.get("strike")),
            option_type=option_type,
            lot_size=self._int_or_none(raw.get("lotsize") or raw.get("lot_size")),
            tick_size=self._float_or_none(raw.get("tick_size") or raw.get("ticksize")),
            underlying=underlying,
            is_equity=is_equity,
            is_fno=is_fno,
            is_future=is_future,
            is_option=is_option,
            updated_at=updated_at,
        )

    def _fallback_fno_underlyings(self) -> list[FnoUnderlying]:
        now = datetime.utcnow()
        return [
            FnoUnderlying(
                symbol=symbol,
                name=details["name"],
                exchange=details["exchange"],
                equity_token=details["token"],
                active_expiries="",
                has_futures=False,
                has_options=False,
                lot_size=1,
                updated_at=now,
            )
            for symbol, details in ANGEL_SYMBOL_DETAILS.items()
        ]

    def _normalize_symbol(self, value: str | None) -> str:
        return str(value or "").strip().upper().replace(" ", "")

    def _underlying(self, raw: dict[str, Any], symbol: str, name: str, instrument_type: str, exchange: str) -> str | None:
        if exchange != "NFO":
            return None
        explicit = raw.get("underlying") or raw.get("underlying_symbol")
        if explicit:
            return self._normalize_symbol(str(explicit))
        if name and name.upper() not in {"FUT", "OPT"}:
            return self._normalize_symbol(name)
        cleaned = symbol
        for suffix in ("CE", "PE", "FUT"):
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)]
        while cleaned and cleaned[-1].isdigit():
            cleaned = cleaned[:-1]
        month_codes = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
        month_pattern = "|".join(month_codes)
        match = re.match(rf"^([A-Z]+?)(?:\d{{1,2}})?(?:{month_pattern}).*", cleaned)
        if match:
            return match.group(1)
        for code in month_codes:
            index = cleaned.find(code)
            if index > 0:
                return cleaned[:index]
        return cleaned or None

    def _option_type(self, symbol: str, instrument_type: str) -> str | None:
        if "OPT" not in instrument_type:
            return None
        if symbol.endswith("CE"):
            return "CE"
        if symbol.endswith("PE"):
            return "PE"
        return None

    def _expiry(self, value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    def _strike(self, value: Any) -> float | None:
        number = self._float_or_none(value)
        if number is None:
            return None
        return number / 100 if number > 100000 else number

    def _int_or_none(self, value: Any) -> int | None:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _float_or_none(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
