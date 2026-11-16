"""Testes de cadastro e consulta de fontes autorizadas."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response


def _payload(watch_dir: Path, **overrides) -> dict:
    payload = {
        "name": "canal-autorizado",
        "platform": "youtube",
        "creator_name": "Criador Autorizado",
        "authorization_reference": "contrato-2026-001",
        "authorization_notes": "Permissão de captura e reutilização confirmada.",
        "authorization_confirmed": True,
        "watch_directory": str(watch_dir),
        "enabled": True,
    }
    payload.update(overrides)
    return payload


def test_create_source(client: TestClient, watch_dir: Path) -> None:
    response = client.post("/api/v1/sources", json=_payload(watch_dir))

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "canal-autorizado"
    assert body["watch_directory"] == str(watch_dir.resolve())
    assert body["file_extensions"] == [".flv", ".mkv", ".mov", ".mp4", ".ts"]
    assert body["authorization_reference"] == "contrato-2026-001"
    assert body["authorized_at"]


def test_source_uses_global_obs_directory_when_omitted(
    client: TestClient,
) -> None:
    payload = _payload(Path("."))
    payload.pop("watch_directory")

    response = client.post("/api/v1/sources", json=payload)

    assert response.status_code == 201
    assert response.json()["watch_directory"].endswith("obs-recordings")


def test_source_requires_explicit_authorization(
    client: TestClient, watch_dir: Path
) -> None:
    false_response: Response = client.post(
        "/api/v1/sources", json=_payload(watch_dir, authorization_confirmed=False)
    )
    assert false_response.status_code == 422

    missing_payload = _payload(watch_dir)
    missing_payload.pop("authorization_confirmed")
    missing_response: Response = client.post("/api/v1/sources", json=missing_payload)
    assert missing_response.status_code == 422

    empty_reference = client.post(
        "/api/v1/sources", json=_payload(watch_dir, authorization_reference="   ")
    )
    assert empty_reference.status_code == 422


def test_source_rejects_invalid_directory(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/sources", json=_payload(tmp_path / "does-not-exist")
    )

    assert response.status_code == 422
    assert "não encontrado" in response.json()["detail"]


def test_source_rejects_duplicate_name(
    client: TestClient, watch_dir: Path
) -> None:
    first = client.post("/api/v1/sources", json=_payload(watch_dir))
    assert first.status_code == 201

    second = client.post("/api/v1/sources", json=_payload(watch_dir))
    assert second.status_code == 409


def test_list_and_get_sources(client: TestClient, watch_dir: Path) -> None:
    created = client.post("/api/v1/sources", json=_payload(watch_dir)).json()

    listing = client.get("/api/v1/sources")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [created["id"]]

    detail = client.get(f"/api/v1/sources/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]

    missing = client.get("/api/v1/sources/999")
    assert missing.status_code == 404


def test_source_custom_extensions_are_normalized(
    client: TestClient, watch_dir: Path
) -> None:
    response = client.post(
        "/api/v1/sources",
        json=_payload(watch_dir, file_extensions=["MKV", ".mp4", "mkv"]),
    )

    assert response.status_code == 201
    assert response.json()["file_extensions"] == [".mkv", ".mp4"]


def test_source_rejects_invalid_extension(
    client: TestClient, watch_dir: Path
) -> None:
    response = client.post(
        "/api/v1/sources", json=_payload(watch_dir, file_extensions=["../mkv"])
    )

    assert response.status_code == 422
