"""Testes de descoberta e ingestão de gravações do OBS."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _source_id(make_source, **overrides) -> int:
    response = make_source(**overrides)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_scan_registers_only_stable_supported_files(
    client: TestClient,
    make_source,
    watch_dir: Path,
    write_recording,
) -> None:
    source_id = _source_id(make_source)
    stable = write_recording(watch_dir, "stream-001.mkv", age_seconds=60)
    write_recording(watch_dir, "still-recording.mkv", age_seconds=0)
    write_recording(watch_dir, "empty.mkv", age_seconds=60, content=b"")
    write_recording(watch_dir, "notes.txt", age_seconds=60)

    response = client.post("/api/v1/capture/scan")

    assert response.status_code == 200
    body = response.json()
    assert body["registered_total"] == 1
    assert len(body["sources"]) == 1
    source_report = body["sources"][0]
    assert source_report["source_id"] == source_id
    assert source_report["scanned_files"] == 3
    assert source_report["registered_total"] == 1
    assert source_report["unstable"] == 1
    assert source_report["ignored"] == 1
    assert source_report["duplicates"] == 0
    assert source_report["error"] is None

    recordings = client.get("/api/v1/recordings")
    assert recordings.status_code == 200
    page = recordings.json()
    assert page["total"] == 1
    assert page["items"][0]["filename"] == stable.name
    assert page["items"][0]["path"] == str(stable.resolve())
    assert page["items"][0]["source_id"] == source_id
    assert page["items"][0]["status"] == "ready"
    assert page["items"][0]["ready_at"] is not None


def test_scan_is_idempotent(
    client: TestClient,
    make_source,
    watch_dir: Path,
    write_recording,
) -> None:
    _source_id(make_source)
    write_recording(watch_dir, "stream-001.mkv", age_seconds=60)

    first = client.post("/api/v1/capture/scan").json()
    second = client.post("/api/v1/capture/scan").json()

    assert first["registered_total"] == 1
    assert second["registered_total"] == 0
    assert second["sources"][0]["duplicates"] == 1
    assert client.get("/api/v1/recordings").json()["total"] == 1


def test_scan_specific_source_and_filters(
    client: TestClient,
    make_source,
    watch_dir: Path,
    write_recording,
) -> None:
    first_source = _source_id(make_source)
    second_watch = watch_dir.parent / "second-obs"
    second_watch.mkdir()
    second_source = _source_id(
        make_source, name="segundo-canal", watch_directory=str(second_watch)
    )

    write_recording(watch_dir, "first.mkv", age_seconds=60)
    write_recording(second_watch, "second.mp4", age_seconds=60)

    response = client.post(
        "/api/v1/capture/scan", params={"source_id": first_source}
    )

    assert response.status_code == 200
    assert [item["source_id"] for item in response.json()["sources"]] == [first_source]

    all_recordings = client.get("/api/v1/recordings").json()
    assert all_recordings["total"] == 1

    filtered = client.get(
        "/api/v1/recordings", params={"source_id": second_source}
    ).json()
    assert filtered["total"] == 0

    ready = client.get("/api/v1/recordings", params={"status": "ready"}).json()
    assert ready["total"] == 1

    ignored = client.get("/api/v1/recordings", params={"status": "ignored"}).json()
    assert ignored["total"] == 0


def test_scan_unknown_source_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/capture/scan", params={"source_id": 999})

    assert response.status_code == 404


def test_scan_disabled_source_reports_error(
    client: TestClient, make_source, watch_dir: Path
) -> None:
    source_id = _source_id(make_source, enabled=False)

    response = client.post(
        "/api/v1/capture/scan", params={"source_id": source_id}
    )

    assert response.status_code == 200
    report = response.json()["sources"][0]
    assert report["error"] == "fonte desabilitada"
    assert report["registered_total"] == 0

    global_scan = client.post("/api/v1/capture/scan").json()
    assert global_scan["sources"] == []
    assert global_scan["registered_total"] == 0


def test_scan_empty_configuration(client: TestClient) -> None:
    response = client.post("/api/v1/capture/scan")

    assert response.status_code == 200
    assert response.json() == {"registered_total": 0, "sources": []}


def test_get_recording_and_validation(
    client: TestClient,
    make_source,
    watch_dir: Path,
    write_recording,
) -> None:
    _source_id(make_source)
    write_recording(watch_dir, "stream-001.mkv", age_seconds=60)
    client.post("/api/v1/capture/scan")
    recording = client.get("/api/v1/recordings").json()["items"][0]

    detail = client.get(f"/api/v1/recordings/{recording['id']}")
    assert detail.status_code == 200
    assert detail.json()["filename"] == "stream-001.mkv"

    missing = client.get("/api/v1/recordings/999")
    assert missing.status_code == 404

    invalid_status = client.get(
        "/api/v1/recordings", params={"status": "not-a-status"}
    )
    assert invalid_status.status_code == 422

    invalid_limit = client.get("/api/v1/recordings", params={"limit": 0})
    assert invalid_limit.status_code == 422
