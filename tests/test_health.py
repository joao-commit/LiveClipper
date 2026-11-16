"""Testes do health check e da raiz."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_identifies_phase(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "LiveClipper"
    assert body["phase"].startswith("1")


def test_health_checks_database_and_monitor(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["environment"] == "test"
    assert body["capture_monitor"]["running"] is False
    assert body["capture_monitor"]["poll_interval_seconds"] == 0.1


def test_capture_status_without_background_monitor(client: TestClient) -> None:
    response = client.get("/api/v1/capture/status")

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is False
    assert body["last_scan_at"] is None
    assert body["last_error"] is None
