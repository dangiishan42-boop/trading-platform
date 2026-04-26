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
