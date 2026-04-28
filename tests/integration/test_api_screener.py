from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_screener_capabilities_returns_filter_categories():
    response = client.get("/api/v1/screener/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert "Overview" in payload["categories"]
    assert "Technical Indicators" in payload["categories"]
    assert "Market Cap" in payload["metrics"]["Price"]
    assert "Greater Than" in payload["conditions"]


def test_screener_run_returns_results_and_summary():
    response = client.post(
        "/api/v1/screener/run",
        json={
            "universe": "Indian Equities",
            "exchange": "NSE",
            "filters": [
                {
                    "category": "Overview",
                    "metric": "Market Cap (₹ Cr)",
                    "condition": "Greater Than",
                    "value": 5000,
                    "logical": "AND",
                }
            ],
            "sort_by": "Market Cap",
            "sort_direction": "desc",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["results"], list)
    assert payload["summary"]["status"] == "Completed"
    assert "matches" in payload["summary"]
    assert "data_source_note" in payload
    assert "filters" in payload["distributions"]


def test_screener_api_returns_price_volume_metrics():
    response = client.post(
        "/api/v1/screener/run",
        json={"universe": "Indian Equities", "exchange": "NSE", "filters": [], "sort_by": "Market Cap", "sort_direction": "desc"},
    )

    assert response.status_code == 200
    row = response.json()["results"][0]
    for key in [
        "ltp",
        "percent_change",
        "point_change",
        "volume",
        "avg_volume_20d",
        "relative_volume",
        "volume_spike",
        "high_52w",
        "low_52w",
        "distance_from_52w_high_pct",
        "distance_from_52w_low_pct",
        "gap_up_pct",
        "gap_down_pct",
        "day_range_pct",
        "turnover",
        "data_source",
    ]:
        assert key in row


def test_screener_api_returns_technical_metrics():
    response = client.post(
        "/api/v1/screener/run",
        json={"universe": "Indian Equities", "exchange": "NSE", "filters": [], "sort_by": "Market Cap", "sort_direction": "desc"},
    )

    assert response.status_code == 200
    row = response.json()["results"][0]
    for key in [
        "ema_20",
        "ema_50",
        "ema_200",
        "sma_20",
        "sma_50",
        "sma_200",
        "rsi_14",
        "rsi_status",
        "macd_line",
        "macd_signal",
        "macd_histogram",
        "macd_bullish",
        "macd_bearish",
        "breakout_20d",
        "breakdown_20d",
        "breakout_52w",
        "breakdown_52w",
        "volume_confirmed_breakout",
        "trend_score",
        "technical_rating",
        "data_source",
    ]:
        assert key in row


def test_screener_api_returns_candlestick_pattern_fields():
    response = client.post(
        "/api/v1/screener/run",
        json={"universe": "Indian Equities", "exchange": "NSE", "filters": [], "sort_by": "Market Cap", "sort_direction": "desc"},
    )

    assert response.status_code == 200
    row = response.json()["results"][0]
    for key in [
        "doji",
        "hammer",
        "shooting_star",
        "bullish_engulfing",
        "bearish_engulfing",
        "inside_bar",
        "outside_bar",
        "bullish_marubozu",
        "bearish_marubozu",
        "gap_up",
        "gap_down",
        "strong_bullish_candle",
        "strong_bearish_candle",
        "detected_patterns",
        "candlestick_bias",
        "pattern_status",
    ]:
        assert key in row


def test_screener_formula_validate_endpoint_works():
    response = client.post("/api/v1/screener/formula/validate", json={"expression": "RSI14 < 30 AND Hammer == true"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["referenced_metrics"] == ["Hammer", "RSI14"]


def test_screener_run_filters_rows_by_formula():
    response = client.post(
        "/api/v1/screener/run",
        json={
            "universe": "Indian Equities",
            "exchange": "NSE",
            "filters": [],
            "custom_formula_enabled": True,
            "custom_formula_name": "Positive move",
            "custom_formula_expression": "PercentChange > -999",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["formula_validation"]["valid"] is True
    assert payload["formula_matched_count"] == len(payload["results"])
    assert payload["results"]
    assert all(row["formula_match"] is True for row in payload["results"])


def test_screener_preset_formula_works():
    capabilities = client.get("/api/v1/screener/capabilities").json()
    preset = next(item for item in capabilities["formula_presets"] if item["name"] == "Volume Burst")

    response = client.post("/api/v1/screener/formula/validate", json={"expression": preset["expression"]})

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_saved_screen_preserves_formula_fields():
    payload = {
        "name": "Formula Screen Test",
        "config": {
            "filters": [],
            "custom_formula_enabled": True,
            "custom_formula_name": "Bullish formula",
            "custom_formula_expression": 'CandlestickBias == "Bullish"',
        },
    }

    response = client.post("/api/v1/screener/saved", json=payload)

    assert response.status_code == 200
    saved = response.json()
    assert saved["config"]["custom_formula_enabled"] is True
    assert saved["config"]["custom_formula_name"] == "Bullish formula"
    assert saved["config"]["custom_formula_expression"] == 'CandlestickBias == "Bullish"'


def test_screener_api_returns_composite_score():
    response = client.post(
        "/api/v1/screener/run",
        json={"universe": "Indian Equities", "exchange": "NSE", "filters": [], "sort_by": "Composite Score", "sort_direction": "desc"},
    )

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert "composite_score" in row


def test_screener_accepts_fno_stocks_universe():
    response = client.post(
        "/api/v1/screener/run",
        json={
            "universe": "F&O Stocks",
            "exchange": "NSE",
            "filters": [],
            "sort_by": "Market Cap",
            "sort_direction": "desc",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["universe"] == "F&O Stocks"
    assert "F&O universe is synced from Angel instrument master" in payload["data_source_note"]
