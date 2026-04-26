from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_news_capabilities_returns_sections_and_categories():
    response = client.get("/api/v1/news/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert "Market News" in payload["tabs"]
    assert "Economy" in payload["categories"]
    assert "top_news" in payload["sections"]


def test_news_feed_returns_top_news_and_featured_insights():
    response = client.post("/api/v1/news/feed", json={"query": "", "category": "All", "tab": "Market News"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["top_news"]
    assert payload["featured_insights"]
    assert payload["sector_news"]
    assert "News data is local/sample" in payload["data_source_note"]


def test_news_sentiment_returns_sentiment_structure():
    response = client.post("/api/v1/news/sentiment", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["sentiment"]["overall_score"] >= 0
    assert payload["sentiment"]["items"]


def test_news_flows_returns_fii_dii_structure():
    response = client.post("/api/v1/news/flows", json={})

    assert response.status_code == 200
    payload = response.json()
    labels = {row["label"] for row in payload["flows"]}
    assert "FII Cash" in labels
    assert "DII Cash" in labels


def test_news_earnings_returns_earnings_list():
    response = client.post("/api/v1/news/earnings", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["earnings"]
    assert {"Today", "Tomorrow", "This Week"} == set(payload["tabs"])
