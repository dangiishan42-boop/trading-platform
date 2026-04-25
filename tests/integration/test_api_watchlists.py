from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _unique_name(prefix: str = "Test Watchlist") -> str:
    return f"{prefix} {uuid4().hex[:8]}"


def _create_watchlist(name: str | None = None) -> dict:
    response = client.post("/api/v1/watchlists", json={"name": name or _unique_name()})
    assert response.status_code == 201
    return response.json()


def _delete_watchlist(watchlist_id: int) -> None:
    client.delete(f"/api/v1/watchlists/{watchlist_id}")


def test_create_watchlist():
    watchlist = _create_watchlist()
    try:
        assert watchlist["id"] is not None
        assert watchlist["name"].startswith("Test Watchlist")
        assert watchlist["items"] == []
    finally:
        _delete_watchlist(watchlist["id"])


def test_list_watchlists_includes_created_watchlist():
    watchlist = _create_watchlist()
    try:
        response = client.get("/api/v1/watchlists")

        assert response.status_code == 200
        payload = response.json()
        assert any(item["id"] == watchlist["id"] for item in payload)
    finally:
        _delete_watchlist(watchlist["id"])


def test_add_watchlist_item():
    watchlist = _create_watchlist()
    try:
        response = client.post(
            f"/api/v1/watchlists/{watchlist['id']}/items",
            json={
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "token": "2885",
                "display_name": "Reliance Industries",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["symbol"] == "RELIANCE"
        assert payload["exchange"] == "NSE"
        assert payload["token"] == "2885"
    finally:
        _delete_watchlist(watchlist["id"])


def test_prevent_duplicate_watchlist_item():
    watchlist = _create_watchlist()
    item_payload = {
        "symbol": "TCS",
        "exchange": "NSE",
        "token": "11536",
        "display_name": "Tata Consultancy Services",
    }
    try:
        first_response = client.post(f"/api/v1/watchlists/{watchlist['id']}/items", json=item_payload)
        duplicate_response = client.post(f"/api/v1/watchlists/{watchlist['id']}/items", json=item_payload)

        assert first_response.status_code == 201
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == "Symbol already exists in this watchlist"
    finally:
        _delete_watchlist(watchlist["id"])


def test_remove_watchlist_item():
    watchlist = _create_watchlist()
    try:
        add_response = client.post(
            f"/api/v1/watchlists/{watchlist['id']}/items",
            json={"symbol": "INFY", "exchange": "NSE", "token": "1594", "display_name": "Infosys"},
        )
        item_id = add_response.json()["id"]

        remove_response = client.delete(f"/api/v1/watchlists/{watchlist['id']}/items/{item_id}")
        list_response = client.get("/api/v1/watchlists")

        refreshed = next(item for item in list_response.json() if item["id"] == watchlist["id"])
        assert remove_response.status_code == 204
        assert refreshed["items"] == []
    finally:
        _delete_watchlist(watchlist["id"])


def test_delete_watchlist():
    watchlist = _create_watchlist()

    delete_response = client.delete(f"/api/v1/watchlists/{watchlist['id']}")
    list_response = client.get("/api/v1/watchlists")

    assert delete_response.status_code == 204
    assert all(item["name"] != watchlist["name"] for item in list_response.json())
