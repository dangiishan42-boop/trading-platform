from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_saves_dataset_metadata_and_lists_recent_uploads():
    sample_path = Path("data/samples/sample_ohlcv.csv")
    response = client.post(
        "/api/v1/data/upload",
        files={
            "file": (
                sample_path.name,
                sample_path.read_bytes(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["original_file_name"] == sample_path.name
    assert payload["file_name"]
    assert payload["preview"]["total_rows"] > 0
    assert payload["preview"]["min_date"]
    assert payload["preview"]["max_date"]

    datasets_response = client.get("/api/v1/data/uploads?limit=10")

    assert datasets_response.status_code == 200

    datasets_payload = datasets_response.json()

    assert isinstance(datasets_payload, list)
    assert datasets_payload
    assert len(datasets_payload) <= 10

    matching_entry = next(
        (entry for entry in datasets_payload if entry["stored_file_name"] == payload["file_name"]),
        None,
    )

    assert matching_entry is not None
    assert matching_entry["original_file_name"] == sample_path.name
    assert matching_entry["stored_file_name"] == payload["file_name"]
    assert matching_entry["row_count"] == payload["preview"]["total_rows"]
    assert matching_entry["min_date"]
    assert matching_entry["max_date"]
    assert matching_entry["uploaded_at"]


def test_upload_rejects_binary_or_non_csv_content():
    response = client.post(
        "/api/v1/data/upload",
        files={
            "file": (
                "suspicious.csv",
                b"\x00\x01\x02not-a-valid-csv",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert "Unsupported upload content type" in response.json()["detail"]
