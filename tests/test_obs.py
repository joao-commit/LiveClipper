"""Testes do diagnóstico de OBS."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_obs_status_reports_file_capture(client: TestClient) -> None:
    response = client.get("/api/v1/obs/status")

    assert response.status_code == 200
    body = response.json()
    assert body["file_capture_supported"] is True
    assert body["recordings_directory_exists"] is True
    assert body["recordings_directory"].endswith("obs-recordings")
    assert body["websocket_url"] == "ws://127.0.0.1:4455"


def test_obs_status_does_not_expose_password(client: TestClient) -> None:
    response = client.get("/api/v1/obs/status")

    assert "password" not in response.text.lower()
