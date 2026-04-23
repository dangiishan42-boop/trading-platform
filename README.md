# Trading Backtesting Platform

A FastAPI trading research platform with data upload, strategy selection, realistic backtesting, dashboard reporting, history, exports, and deployment-ready runtime settings.

## Features
- CSV OHLCV upload, preview, and saved dataset reuse
- Strategy registry plus saved strategy configurations
- Backtests with brokerage, slippage, sizing, stop loss, and take profit
- Dashboard metrics, charts, trade list, history, comparison, and CSV export
- SQLite persistence for MVP usage
- Environment-based runtime config for development and production
- Structured logging for backtest runs

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
python run.py
```

Open:
- Dashboard: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## Configuration

Development defaults live in `.env.example`.
Production-oriented defaults live in `.env.production.example`.

Important environment variables:
- `APP_ENV`: `development`, `testing`, or `production`
- `DEBUG`: enables FastAPI debug behavior and auto-reload in `run.py`
- `DATABASE_URL`: SQLAlchemy connection string
- `HOST`: bind host for the server
- `PORT`: bind port for the server
- `WEB_CONCURRENCY`: worker count when debug mode is off
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`
- `JSON_LOGS`: enables structured JSON logs on stdout
- `CORS_ALLOWED_ORIGINS`: comma-separated allowed origins
- `TRUSTED_HOSTS`: comma-separated allowed hostnames
- `MAX_UPLOAD_SIZE_MB`: maximum upload size for CSV files
- `SECRET_KEY`: must be changed for production

## Production Deployment

### 1. Prepare environment

```bash
copy .env.production.example .env.production
```

Set these before starting:
- `APP_ENV=production`
- `DEBUG=false`
- `SECRET_KEY` to a long random value
- `DATABASE_URL` to your production database path or server
- `CORS_ALLOWED_ORIGINS` to your real frontend origin
- `TRUSTED_HOSTS` to your real domain names

### 2. Install runtime dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the app

```bash
set SETTINGS_ENV_FILE=.env.production
set APP_ENV=production
set DEBUG=false
set SECRET_KEY=replace-with-a-random-secret
python run.py
```

For Linux/macOS shells:

```bash
export SETTINGS_ENV_FILE=.env.production
export APP_ENV=production
export DEBUG=false
export SECRET_KEY=replace-with-a-random-secret
python run.py
```

## Docker

Build:

```bash
docker build -t trading-platform .
```

Run:

```bash
docker run --rm -p 8000:8000 ^
  -e APP_ENV=production ^
  -e DEBUG=false ^
  -e SECRET_KEY=replace-with-a-random-secret ^
  -e CORS_ALLOWED_ORIGINS=https://your-domain.example ^
  -e TRUSTED_HOSTS=your-domain.example,localhost,127.0.0.1 ^
  trading-platform
```

If you keep a separate production env file locally, you can also use:

```bash
docker run --rm -p 8000:8000 --env-file .env.production trading-platform
```

## Logging

The app now writes:
- human-readable console logs in development
- JSON logs in production when `JSON_LOGS=true`
- rotating structured log files in `logs/app.log`

Backtest runs emit structured events for:
- `backtest_run_started`
- `backtest_run_completed`
- `backtest_run_failed`

## Security Notes

Current hardening includes:
- stricter backtest request validation for symbol, timeframe, source, and strategy slug fields
- trusted-host and configurable CORS middleware
- upload extension, MIME type, file size, and binary-content checks
- production startup guard that rejects `SECRET_KEY=change-me`

## Suggested Next Production Upgrades
- move from SQLite to PostgreSQL
- add authentication and authorization
- add reverse proxy and TLS termination
- add background job workers for heavy backtests
- add persistent object storage for uploaded datasets
