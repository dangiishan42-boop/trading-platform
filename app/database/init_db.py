from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel

from app.config.paths import DATA_DIR, LOG_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, SAMPLE_DATA_DIR
from app.database.session import engine
from app.database.seed_data import seed_builtin_strategies
from app.models.strategy_model import SavedStrategy
from app.models.strategy_config_model import SavedStrategyConfiguration
from app.models.algo_strategy_model import SavedAlgoStrategy
from app.models.backtest_model import BacktestRun
from app.models.dataset_model import UploadedDataset
from app.models.result_model import BacktestResultRecord


def _sqlite_database_path() -> Path | None:
    if engine.url.get_backend_name() != "sqlite":
        return None
    database_name = engine.url.database
    if not database_name or database_name == ":memory:":
        return None
    return Path(database_name)


def _ensure_backtest_run_history_columns() -> None:
    if engine.url.get_backend_name() != "sqlite":
        return
    
    with engine.begin() as connection:
        table_exists = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='backtestrun'")
        ).scalar()
        if not table_exists:
            return

        existing_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info('backtestrun')")).fetchall()
        }
        column_definitions = {
            "slippage_pct": "REAL NOT NULL DEFAULT 0.0",
            "total_return_pct": "REAL NOT NULL DEFAULT 0.0",
            "win_rate_pct": "REAL NOT NULL DEFAULT 0.0",
            "max_drawdown_pct": "REAL NOT NULL DEFAULT 0.0",
        }

        for column_name, definition in column_definitions.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE backtestrun ADD COLUMN {column_name} {definition}"))


def initialize_database() -> None:
    for directory in (DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, SAMPLE_DATA_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    sqlite_path = _sqlite_database_path()
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    SQLModel.metadata.create_all(engine)
    _ensure_backtest_run_history_columns()
    seed_builtin_strategies()
