"""Testes do registro de adaptadores de origem do vídeo."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.database.models import CaptureSource
from app.sources.base import RecordingCandidate, SourceAdapter
from app.sources.factory import (
    DEFAULT_SOURCE_ADAPTER,
    UnknownSourceAdapter,
    available_source_adapters,
    build_source_adapter,
    register_source_adapter,
)
from app.sources.local import LocalObsDirectorySource


class _StubAdapter(SourceAdapter):
    def __init__(self, source: CaptureSource) -> None:
        self.source_id = source.id
        self.name = source.name

    def availability_error(self) -> str | None:
        return None

    def scan(self) -> list[RecordingCandidate]:  # pragma: no cover - contrato mínimo
        return []


def _source() -> CaptureSource:
    return CaptureSource(
        id=1,
        name="fonte-de-teste",
        watch_directory="/tmp/obs",
        file_extensions=[".mkv"],
    )


def test_default_adapter_is_local_obs_directory() -> None:
    adapter = build_source_adapter(_source())

    assert isinstance(adapter, LocalObsDirectorySource)
    assert DEFAULT_SOURCE_ADAPTER in available_source_adapters()


def test_registered_adapter_can_replace_the_origin() -> None:
    register_source_adapter("stub-for-test", _StubAdapter)

    adapter = build_source_adapter(_source(), "stub-for-test")

    assert isinstance(adapter, _StubAdapter)
    assert adapter.source_id == 1
    assert "stub-for-test" in available_source_adapters()


def test_unknown_adapter_is_rejected() -> None:
    with pytest.raises(UnknownSourceAdapter, match="desconhecido"):
        build_source_adapter(_source(), "nao-existe")


def test_duplicate_registration_requires_explicit_replace() -> None:
    register_source_adapter("duplicate-for-test", _StubAdapter)

    with pytest.raises(ValueError, match="já registrado"):
        register_source_adapter("duplicate-for-test", _StubAdapter)

    register_source_adapter("duplicate-for-test", _StubAdapter, replace=True)


def test_source_adapter_setting_is_normalized() -> None:
    settings = Settings(_env_file=None, source_adapter="  OBS_DIRECTORY  ")

    assert settings.source_adapter == "obs_directory"


def test_scan_reports_unknown_configured_adapter(
    client,
    settings: Settings,
    make_source,
    watch_dir,
    write_recording,
) -> None:
    assert make_source().status_code == 201
    write_recording(watch_dir, "stream.mkv", age_seconds=60)
    settings.source_adapter = "nao-existe"

    response = client.post("/api/v1/capture/scan")

    assert response.status_code == 200
    report = response.json()["sources"][0]
    assert "adaptador de fonte desconhecido" in report["error"]
    assert report["registered_total"] == 0
