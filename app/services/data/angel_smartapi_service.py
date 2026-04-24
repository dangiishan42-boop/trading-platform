from dataclasses import dataclass

import pandas as pd

from app.config.settings import get_settings
from app.core.exceptions import DataValidationError, InvalidRequestError
from app.schemas.data_schema import AngelDataFetchRequest, DataUploadResponse
from app.services.data.data_loader_service import DataLoaderService


@dataclass(frozen=True)
class AngelCredentials:
    api_key: str
    client_id: str
    mpin: str
    totp_secret: str


class AngelSmartApiService:
    CANDLE_COLUMNS = ("Date", "Open", "High", "Low", "Close", "Volume")
    ANGEL_DATETIME_FORMAT = "%Y-%m-%d %H:%M"

    def __init__(self, loader: DataLoaderService | None = None) -> None:
        self.settings = get_settings()
        self.loader = loader or DataLoaderService()

    def fetch_dataset(self, request: AngelDataFetchRequest) -> DataUploadResponse:
        frame = self.fetch_frame(request)
        original_file_name = self._build_original_file_name(request)
        return self.loader.save_dataframe_upload(
            original_file_name,
            frame,
            message="Angel One data fetched successfully",
        )

    def has_credentials(self) -> bool:
        return all(
            [
                self.settings.angel_api_key,
                self.settings.angel_client_id,
                self.settings.angel_mpin,
                self.settings.angel_totp_secret,
            ]
        )

    def fetch_ltp(self, *, exchange: str, symbol: str, symbol_token: str) -> dict:
        credentials = self._get_credentials()
        client = self._build_client(credentials.api_key)
        try:
            self._authenticate(client, credentials)
            response = self._fetch_ltp(client, exchange, symbol, symbol_token)
        finally:
            self._terminate_session(client, credentials.client_id)
        return response

    def fetch_frame(self, request: AngelDataFetchRequest) -> pd.DataFrame:
        credentials = self._get_credentials()
        client = self._build_client(credentials.api_key)
        try:
            self._authenticate(client, credentials)
            response = self._fetch_candles(client, request)
            frame = self._normalize_candles(response)
        finally:
            self._terminate_session(client, credentials.client_id)
        return frame

    def _get_credentials(self) -> AngelCredentials:
        missing = [
            env_name
            for env_name, value in [
                ("ANGEL_API_KEY", self.settings.angel_api_key),
                ("ANGEL_CLIENT_ID", self.settings.angel_client_id),
                ("ANGEL_MPIN", self.settings.angel_mpin),
                ("ANGEL_TOTP_SECRET", self.settings.angel_totp_secret),
            ]
            if not value
        ]
        if missing:
            raise InvalidRequestError(
                "Angel One credentials are not configured. Missing: "
                + ", ".join(missing)
            )

        return AngelCredentials(
            api_key=self.settings.angel_api_key or "",
            client_id=self.settings.angel_client_id or "",
            mpin=self.settings.angel_mpin or "",
            totp_secret=self.settings.angel_totp_secret or "",
        )

    def _build_client(self, api_key: str):
        try:
            from SmartApi import SmartConnect
        except ImportError as exc:
            raise InvalidRequestError(
                "Angel One SmartAPI support requires the smartapi-python package to be installed"
            ) from exc

        return SmartConnect(api_key=api_key)

    def _generate_totp(self, totp_secret: str) -> str:
        try:
            import pyotp
        except ImportError as exc:
            raise InvalidRequestError(
                "Angel One SmartAPI support requires the pyotp package to be installed"
            ) from exc

        try:
            return pyotp.TOTP(totp_secret).now()
        except Exception as exc:
            raise InvalidRequestError("Angel One TOTP secret is invalid") from exc

    def _authenticate(self, client, credentials: AngelCredentials) -> None:
        try:
            response = client.generateSession(
                credentials.client_id,
                credentials.mpin,
                self._generate_totp(credentials.totp_secret),
            )
        except Exception as exc:
            raise InvalidRequestError(f"Angel One authentication failed: {exc}") from exc

        if isinstance(response, dict) and response.get("status") is False:
            message = response.get("message") or "Unknown authentication error"
            raise InvalidRequestError(f"Angel One authentication failed: {message}")

    def _fetch_candles(self, client, request: AngelDataFetchRequest) -> dict:
        params = {
            "exchange": request.exchange,
            "symboltoken": request.symbol_token,
            "interval": request.interval,
            "fromdate": request.fromdate.strftime(self.ANGEL_DATETIME_FORMAT),
            "todate": request.todate.strftime(self.ANGEL_DATETIME_FORMAT),
        }
        try:
            response = client.getCandleData(params)
        except Exception as exc:
            raise InvalidRequestError(f"Angel One candle fetch failed: {exc}") from exc

        if not isinstance(response, dict):
            raise DataValidationError("Angel One candle response was not in the expected format")
        if response.get("status") is False:
            message = response.get("message") or "Angel One candle fetch failed"
            raise InvalidRequestError(message)
        return response

    def _fetch_ltp(self, client, exchange: str, symbol: str, symbol_token: str) -> dict:
        try:
            response = client.ltpData(exchange, symbol, symbol_token)
        except Exception as exc:
            raise InvalidRequestError(f"Angel One quote fetch failed: {exc}") from exc

        if not isinstance(response, dict):
            raise DataValidationError("Angel One quote response was not in the expected format")
        if response.get("status") is False:
            message = response.get("message") or "Angel One quote fetch failed"
            raise InvalidRequestError(message)
        return response

    def _normalize_candles(self, response: dict) -> pd.DataFrame:
        rows = response.get("data")
        if not rows:
            raise DataValidationError("Angel One returned no candle data for the requested range")
        if not isinstance(rows, list):
            raise DataValidationError("Angel One candle response did not include candle rows")

        normalized_rows: list[dict[str, object]] = []
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, (list, tuple)) or len(row) < len(self.CANDLE_COLUMNS):
                raise DataValidationError(f"Angel One candle row {index} is malformed")

            normalized_rows.append(
                {
                    "Date": row[0],
                    "Open": row[1],
                    "High": row[2],
                    "Low": row[3],
                    "Close": row[4],
                    "Volume": row[5],
                }
            )

        return pd.DataFrame(normalized_rows, columns=list(self.CANDLE_COLUMNS))

    def _build_original_file_name(self, request: AngelDataFetchRequest) -> str:
        from_stamp = request.fromdate.strftime("%Y%m%d%H%M")
        to_stamp = request.todate.strftime("%Y%m%d%H%M")
        return (
            f"angel_{request.exchange}_{request.symbol_token}_{request.interval}_"
            f"{from_stamp}_{to_stamp}.csv"
        )

    def _terminate_session(self, client, client_id: str) -> None:
        if not hasattr(client, "terminateSession"):
            return

        try:
            client.terminateSession(client_id)
        except Exception:
            return
