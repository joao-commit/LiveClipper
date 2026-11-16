"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        database_url=f"sqlite:///{tmp_path / 'liveclipper-test.db'}",
        obs_recordings_dir=tmp_path / "obs-recordings",
        capture_auto_start=False,
        capture_poll_interval_seconds=0.1,
        capture_settle_seconds=15,
    )


@pytest.fixture
def client(settings: Settings):
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def watch_dir(settings: Settings) -> Path:
    directory = settings.obs_recordings_dir
    assert directory is not None
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@pytest.fixture
def make_source(client: TestClient, watch_dir: Path):
    def _make_source(**overrides: Any):
        payload: dict[str, Any] = {
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
        return client.post("/api/v1/sources", json=payload)

    return _make_source


@pytest.fixture
def write_recording():
    def _write_recording(
        directory: Path,
        name: str = "stream.mkv",
        *,
        age_seconds: float = 60,
        content: bytes = b"fake-video-data",
    ) -> Path:
        path = directory / name
        path.write_bytes(content)
        timestamp = time.time() - age_seconds
        os.utime(path, (timestamp, timestamp))
        return path

    return _write_recording
