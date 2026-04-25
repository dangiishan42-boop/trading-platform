from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy import delete, or_
from sqlmodel import Session, select

from app.config.constants import ANGEL_SYMBOL_DETAILS
from app.core.exceptions import DataValidationError, InvalidRequestError
from app.models.instrument_master_model import InstrumentMaster


DEFAULT_ANGEL_SCRIP_MASTER_URL = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
)


class InstrumentMasterService:
    EXCHANGES = {"NSE", "BSE"}
    EQUITY_TYPES = {"", "EQ", "EQUITY"}

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
        if records:
            session.add_all(records)
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

    def search(self, session: Session, q: str, exchange: str | None = None, limit: int = 20) -> list[InstrumentMaster]:
        normalized_q = q.strip()
        if not normalized_q:
            return []

        statement = select(InstrumentMaster)
        if exchange:
            statement = statement.where(InstrumentMaster.exchange == exchange.strip().upper())

        pattern = f"%{normalized_q.upper()}%"
        statement = (
            statement.where(
                or_(
                    InstrumentMaster.symbol.ilike(pattern),
                    InstrumentMaster.name.ilike(pattern),
                    InstrumentMaster.token.ilike(pattern),
                )
            )
            .order_by(InstrumentMaster.exchange, InstrumentMaster.symbol)
            .limit(limit)
        )
        return list(session.exec(statement))

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
            )
        return None

    def _parse_record(self, raw: dict[str, Any], updated_at: datetime) -> InstrumentMaster | None:
        exchange = str(raw.get("exch_seg") or raw.get("exchange") or "").strip().upper()
        if exchange not in self.EXCHANGES:
            return None

        instrument_type = str(raw.get("instrumenttype") or raw.get("instrument_type") or "").strip().upper()
        if instrument_type not in self.EQUITY_TYPES:
            return None

        token = str(raw.get("token") or "").strip()
        raw_symbol = str(raw.get("symbol") or "").strip().upper()
        name = str(raw.get("name") or raw_symbol).strip()
        if not token or not raw_symbol:
            return None

        symbol = self._normalize_symbol(raw_symbol)
        if exchange == "NSE" and raw_symbol.endswith("-EQ"):
            symbol = symbol.removesuffix("-EQ")

        return InstrumentMaster(
            exchange=exchange,
            symbol=symbol,
            name=name or symbol,
            token=token,
            instrument_type=instrument_type or "EQ",
            lot_size=self._int_or_none(raw.get("lotsize") or raw.get("lot_size")),
            tick_size=self._float_or_none(raw.get("tick_size") or raw.get("ticksize")),
            updated_at=updated_at,
        )

    def _normalize_symbol(self, value: str | None) -> str:
        return str(value or "").strip().upper().replace(" ", "")

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
