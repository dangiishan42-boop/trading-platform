from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.config.constants import ANGEL_SYMBOL_TO_TOKEN, OHLCV_COLUMNS
from app.core.exceptions import DataValidationError, InvalidRequestError
from app.schemas.data_schema import (
    AngelDataFetchRequest,
    HistoricalDataRequest,
    HistoricalDataResponse,
    HistoricalDataRow,
)
from app.services.data.angel_smartapi_service import AngelSmartApiService
from app.services.data.data_resampler_service import DataResamplerService
from app.services.data.instrument_master_service import InstrumentMasterService


@dataclass(frozen=True)
class HistoricalIntervalConfig:
    angel_interval: str
    resample_rule: str | None = None


class HistoricalDataService:
    INTERVAL_CONFIG: dict[str, HistoricalIntervalConfig] = {
        "5M": HistoricalIntervalConfig(angel_interval="FIVE_MINUTE"),
        "15M": HistoricalIntervalConfig(angel_interval="FIFTEEN_MINUTE"),
        "30M": HistoricalIntervalConfig(angel_interval="THIRTY_MINUTE"),
        "1H": HistoricalIntervalConfig(angel_interval="ONE_HOUR"),
        "3H": HistoricalIntervalConfig(angel_interval="ONE_HOUR", resample_rule="3h"),
        "4H": HistoricalIntervalConfig(angel_interval="ONE_HOUR", resample_rule="4h"),
        "1D": HistoricalIntervalConfig(angel_interval="ONE_DAY"),
    }

    def __init__(
        self,
        angel_service: AngelSmartApiService | None = None,
        resampler: DataResamplerService | None = None,
        instruments: InstrumentMasterService | None = None,
    ) -> None:
        self.angel_service = angel_service or AngelSmartApiService()
        self.resampler = resampler or DataResamplerService()
        self.instruments = instruments or InstrumentMasterService()

    def fetch(self, request: HistoricalDataRequest, session=None) -> HistoricalDataResponse:
        symbol = self._normalize_symbol(request.symbol)
        instrument = self.instruments.resolve(
            session,
            query=symbol,
            exchange=request.exchange,
            token=request.symbol_token,
        )
        symbol_token = instrument.token if instrument is not None else self._resolve_symbol_token(symbol, request.symbol_token)
        response_symbol = instrument.symbol if instrument is not None else (symbol or symbol_token)
        interval_config = self.INTERVAL_CONFIG[request.interval]

        frame = self.angel_service.fetch_frame(
            AngelDataFetchRequest(
                exchange=request.exchange,
                symbol_token=symbol_token,
                interval=interval_config.angel_interval,
                fromdate=request.fromdate,
                todate=request.todate,
            )
        )
        prepared_frame = self._prepare_frame(frame)

        if interval_config.resample_rule:
            prepared_frame = self.resampler.resample(prepared_frame, interval_config.resample_rule)

        prepared_frame = prepared_frame.sort_values("Date").reset_index(drop=True)
        if prepared_frame.empty:
            raise DataValidationError("No historical data available for the requested range")

        rows = self._serialize_rows(prepared_frame)
        return HistoricalDataResponse(
            exchange=request.exchange,
            symbol=response_symbol,
            symbol_token=symbol_token,
            interval=request.interval,
            row_count=len(rows),
            rows=rows,
        )

    def _normalize_symbol(self, symbol: str | None) -> str:
        return "".join(str(symbol or "").strip().upper().split())

    def _resolve_symbol_token(self, symbol: str, symbol_token: str | None) -> str:
        if symbol_token:
            return symbol_token

        mapped_token = ANGEL_SYMBOL_TO_TOKEN.get(symbol)
        if mapped_token:
            return mapped_token

        raise InvalidRequestError(
            "No symbol token was provided and the selected symbol is not available in the local Angel symbol map"
        )

    def _prepare_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        normalized_frame = frame.copy()
        if normalized_frame.empty:
            raise DataValidationError("No historical data was returned for the requested range")

        normalized_frame["Date"] = pd.to_datetime(normalized_frame["Date"], errors="coerce")
        if getattr(normalized_frame["Date"].dt, "tz", None) is not None:
            normalized_frame["Date"] = normalized_frame["Date"].dt.tz_localize(None)

        for column in OHLCV_COLUMNS:
            normalized_frame[column] = pd.to_numeric(normalized_frame[column], errors="coerce")

        normalized_frame = normalized_frame.dropna(subset=["Date", *OHLCV_COLUMNS]).reset_index(drop=True)
        if normalized_frame.empty:
            raise DataValidationError("Historical data could not be parsed into OHLCV rows")

        return normalized_frame

    def _serialize_rows(self, frame: pd.DataFrame) -> list[HistoricalDataRow]:
        working_frame = frame.copy()
        working_frame["change"] = working_frame["Close"].diff()
        previous_close = working_frame["Close"].shift(1)
        working_frame["change_pct"] = (working_frame["change"] / previous_close) * 100

        rows: list[HistoricalDataRow] = []
        for row in working_frame.itertuples(index=False):
            rows.append(
                HistoricalDataRow(
                    datetime=row.Date.isoformat(),
                    open=round(float(row.Open), 4),
                    high=round(float(row.High), 4),
                    low=round(float(row.Low), 4),
                    close=round(float(row.Close), 4),
                    volume=round(float(row.Volume), 4),
                    change=round(float(row.change), 4) if pd.notna(row.change) else None,
                    change_pct=round(float(row.change_pct), 4) if pd.notna(row.change_pct) else None,
                )
            )
        return rows
