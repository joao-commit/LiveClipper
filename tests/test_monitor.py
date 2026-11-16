"""Teste de integração do monitor de captura (sem event loop externo)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.capture.monitor import CaptureMonitor
from app.config import Settings


def test_monitor_scan_once_registers_files(
    client: TestClient,
    settings: Settings,
    make_source,
    watch_dir: Path,
    write_recording,
) -> None:
    assert make_source().status_code == 201
    write_recording(watch_dir, "monitor.mkv", age_seconds=60)

    monitor = CaptureMonitor(client.app.state.session_factory, settings)

    async def run_scan():
        return await monitor.scan_once()

    report = asyncio.run(run_scan())

    assert report is not None
    assert report.registered_total == 1
    status = monitor.status()
    assert status.last_scan_at is not None
    assert status.last_success_at is not None
    assert status.last_error is None
    assert client.get("/api/v1/recordings").json()["total"] == 1
