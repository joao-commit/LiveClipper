"""Testes dos requisitos de segurança e autorização da Fase 1."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.database.models import CaptureSource
from app.sources.local import LocalObsDirectorySource

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ROUTE_TERMS = ("publish", "upload", "youtube", "oauth")
FORBIDDEN_RUNTIME_DEPENDENCIES = (
    "youtube",
    "google-api",
    "google-auth",
    "oauth",
    "boto3",
    "tweepy",
)


def test_websocket_password_is_not_exposed_in_settings() -> None:
    settings = Settings(_env_file=None, obs_websocket_password="senha-super-secreta")

    assert isinstance(settings.obs_websocket_password, SecretStr)
    assert settings.obs_websocket_password.get_secret_value() == "senha-super-secreta"
    assert "senha-super-secreta" not in repr(settings)
    assert "senha-super-secreta" not in str(settings)


def test_empty_websocket_password_is_none() -> None:
    settings = Settings(_env_file=None, obs_websocket_password="   ")

    assert settings.obs_websocket_password is None


def test_obs_status_never_returns_configured_password(client, settings) -> None:
    settings.obs_websocket_password = SecretStr("segredo-do-obs")

    response = client.get("/api/v1/obs/status")

    assert response.status_code == 200
    assert "segredo-do-obs" not in response.text
    assert "password" not in response.text.lower()


def test_env_example_has_no_filled_secrets() -> None:
    secret_markers = ("PASSWORD", "SECRET", "TOKEN", "API_KEY")

    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if any(marker in key.upper() for marker in secret_markers):
            assert value.strip() == "", f"segredo preenchido em .env.example: {key}"


def test_gitignore_covers_environment_media_and_secrets() -> None:
    patterns = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for expected in (
        ".env",
        "data/*",
        "output/*",
        "*.db",
        "*.mkv",
        "*.mp4",
        "*.pem",
        "*.key",
    ):
        assert expected in patterns


def test_no_publishing_routes_are_exposed(client) -> None:
    paths = client.app.openapi()["paths"]

    for path in paths:
        assert not any(term in path.lower() for term in FORBIDDEN_ROUTE_TERMS), path


def test_no_publishing_dependencies_at_runtime() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = " ".join(project["project"]["dependencies"]).lower()

    for forbidden in FORBIDDEN_RUNTIME_DEPENDENCIES:
        assert forbidden not in dependencies


def test_scan_refuses_source_without_authorization_in_database(
    client,
    make_source,
    watch_dir,
    write_recording,
) -> None:
    created = make_source()
    assert created.status_code == 201
    write_recording(watch_dir, "autorizado.mkv", age_seconds=60)

    with client.app.state.session_factory() as session:
        source = session.get(CaptureSource, created.json()["id"])
        assert source is not None
        source.authorization_reference = "   "
        session.commit()

    response = client.post("/api/v1/capture/scan")

    assert response.status_code == 200
    report = response.json()["sources"][0]
    assert report["error"] == "autorização de captura não confirmada para a fonte"
    assert report["registered_total"] == 0
    assert client.get("/api/v1/recordings").json()["total"] == 0


def test_local_source_ignores_symlinks_outside_the_authorized_directory(
    tmp_path: Path,
) -> None:
    watch_dir = tmp_path / "autorizado"
    watch_dir.mkdir()
    outside_dir = tmp_path / "privado"
    outside_dir.mkdir()

    allowed = watch_dir / "permitido.mkv"
    allowed.write_bytes(b"conteudo-autorizado")
    outside = outside_dir / "privado.mkv"
    outside.write_bytes(b"conteudo-nao-autorizado")

    link = watch_dir / "atalho.mkv"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks não disponíveis neste ambiente")

    adapter = LocalObsDirectorySource(
        source_id=1,
        name="teste",
        directory=watch_dir,
        extensions=[".mkv"],
    )

    candidates = list(adapter.scan())

    assert [candidate.path.name for candidate in candidates] == ["permitido.mkv"]
    assert all(
        candidate.path.is_relative_to(watch_dir.resolve()) for candidate in candidates
    )
