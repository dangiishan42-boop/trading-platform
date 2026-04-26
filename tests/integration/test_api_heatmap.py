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


def test_heatmap_sectors_returns_stable_slugs():
    response = client.get("/api/v1/heatmap/sectors")

    assert response.status_code == 200
    payload = response.json()
    slugs = {row["slug"] for row in payload}
    assert "financial-services" in slugs
    assert "information-technology" in slugs


def test_heatmap_sector_api_returns_only_requested_sector_stocks():
    response = client.post(
        "/api/v1/heatmap/sector/financial-services",
        json={"size_by": "Market Cap", "color_by": "% Change", "timeframe": "1D", "universe": "Nifty 500"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sector"]["slug"] == "financial-services"
    assert payload["stocks"]
    assert {stock["sector"] for stock in payload["stocks"]} == {"FINANCIAL SERVICES"}
    assert payload["largest"][0]["market_cap_cr"] >= payload["largest"][-1]["market_cap_cr"]
    assert any(industry["slug"] == "private-banks" for industry in payload["industries"])


def test_heatmap_industry_api_returns_only_requested_industry_stocks():
    response = client.post(
        "/api/v1/heatmap/sector/financial-services/industry/private-banks",
        json={"size_by": "Market Cap", "color_by": "% Change", "timeframe": "1D", "universe": "Nifty 500"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sector"]["slug"] == "financial-services"
    assert payload["industry"]["slug"] == "private-banks"
    assert payload["stocks"]
    assert {stock["industry_slug"] for stock in payload["stocks"]} == {"private-banks"}


def test_heatmap_invalid_industry_api_returns_404():
    response = client.post(
        "/api/v1/heatmap/sector/financial-services/industry/not-an-industry",
        json={"size_by": "Market Cap", "color_by": "% Change", "timeframe": "1D", "universe": "Nifty 500"},
    )

    assert response.status_code == 404


def test_heatmap_rotation_api_returns_quadrant_data():
    response = client.post("/api/v1/heatmap/rotation", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["bubbles"]
    assert {"Leading", "Improving", "Weakening", "Lagging"} & {row["quadrant"] for row in payload["bubbles"]}
    assert "model_note" in payload["summary"]


def test_heatmap_breadth_api_returns_summary_and_sector_table():
    response = client.post("/api/v1/heatmap/breadth", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] > 0
    assert payload["summary"]["advance_decline_ratio"] >= 0
    assert payload["sector_table"]


def test_heatmap_insights_api_returns_rule_based_insights():
    response = client.post("/api/v1/heatmap/insights", json={})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["insights"]) == 5
    assert {row["severity"] for row in payload["insights"]} <= {"Info", "Bullish", "Bearish", "Warning"}


def test_heatmap_invalid_sector_api_returns_404():
    response = client.post(
        "/api/v1/heatmap/sector/not-a-sector",
        json={"size_by": "Market Cap", "color_by": "% Change", "timeframe": "1D", "universe": "Nifty 500"},
    )

    assert response.status_code == 404
