import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from app.config.settings import get_settings

_configured = False


def _serialize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in fields.items():
        if value is None or isinstance(value, (bool, int, float, str)):
            serialized[key] = value
        else:
            serialized[key] = str(value)
    return serialized


class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event_name = getattr(record, "event_name", record.getMessage())
        event_fields = _serialize_fields(getattr(record, "event_fields", {}))
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "event": event_name,
            "message": record.getMessage(),
        }
        if event_fields:
            payload["fields"] = event_fields
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class ConsoleLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} | {record.levelname} | {record.name} | {record.getMessage()}"
        event_fields = _serialize_fields(getattr(record, "event_fields", {}))
        if event_fields:
            rendered = " | ".join(f"{key}={value}" for key, value in event_fields.items())
            return f"{base} | {rendered}"
        return base


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, settings.log_level))

    formatter: logging.Formatter
    if settings.json_logs:
        formatter = StructuredLogFormatter()
    else:
        formatter = ConsoleLogFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        settings.log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(StructuredLogFormatter())
    root_logger.addHandler(file_handler)

    logging.captureWarnings(True)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event_name: str, **fields: Any) -> None:
    logger.log(level, event_name, extra={"event_name": event_name, "event_fields": fields})
