from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_heatmap_capabilities_returns_options():
    response = client.get("/api/v1/heatmap/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert "Nifty 500" in payload["universes"]
    assert "Market Cap" in payload["size_by"]
    assert "% Change" in payload["color_by"]
    assert "1D" in payload["timeframes"]


def test_heatmap_run_returns_sectors_stocks_and_summary():
    response = client.post(
        "/api/v1/heatmap/run",
        json={
            "universe": "Nifty 500",
            "size_by": "Market Cap",
            "color_by": "% Change",
            "timeframe": "1D",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_stocks"] > 0
    assert len(payload["sectors"]) > 0
    assert len(payload["stocks"]) > 0
    assert "FINANCIAL SERVICES" in {sector["name"] for sector in payload["sectors"]}
    assert "gainers" in payload
    assert "losers" in payload
    assert "Heatmap data is based on local sample data" in payload["data_source_note"]
