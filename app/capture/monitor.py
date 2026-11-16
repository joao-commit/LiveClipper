"""Monitor assíncrono que varre as fontes de captura periodicamente."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from app.capture.scanner import ScanReport, scan_sources
from app.config import Settings
from app.database.base import utc_now

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CaptureMonitorStatus:
    running: bool
    poll_interval_seconds: float
    last_scan_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None


class CaptureMonitor:
    """Executa ``scan_sources`` em intervalos regulares dentro do processo.

    A varredura de arquivos é síncrona e roda em uma thread separada para não
    bloquear o event loop da API.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
        *,
        poll_interval_seconds: float | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._poll_interval = poll_interval_seconds or settings.capture_poll_interval_seconds
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._last_scan_at: datetime | None = None
        self._last_success_at: datetime | None = None
        self._last_error: str | None = None
        self._last_report: ScanReport | None = None

    @property
    def last_report(self) -> ScanReport | None:
        return self._last_report

    def status(self) -> CaptureMonitorStatus:
        return CaptureMonitorStatus(
            running=self._task is not None and not self._task.done(),
            poll_interval_seconds=self._poll_interval,
            last_scan_at=self._last_scan_at,
            last_success_at=self._last_success_at,
            last_error=self._last_error,
        )

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="liveclipper-capture-monitor")
        logger.info(
            "Monitor de captura iniciado (intervalo=%.1fs, settle=%.1fs)",
            self._poll_interval,
            self._settings.capture_settle_seconds,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        task = self._task
        if task is None:
            return
        if not task.done():
            try:
                await task
            except asyncio.CancelledError:  # pragma: no cover - encerramento forçado
                pass
        self._task = None
        logger.info("Monitor de captura encerrado")

    async def scan_once(self) -> ScanReport | None:
        """Executa uma varredura imediata, respeitando a exclusão mútua."""

        async with self._lock:
            self._last_scan_at = utc_now()
            try:
                report = await asyncio.to_thread(self._scan)
            except Exception as exc:
                self._last_error = str(exc)
                logger.exception("Falha na varredura periódica de captura")
                return None

            self._last_report = report
            self._last_success_at = utc_now()
            self._last_error = _summarize_errors(report)
            return report

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self.scan_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self._poll_interval
                )
            except TimeoutError:
                continue

    def _scan(self) -> ScanReport:
        with self._session_factory() as session:
            return scan_sources(session, self._settings)


def _summarize_errors(report: ScanReport) -> str | None:
    errors = [
        f"{source.source_name}: {source.error}"
        for source in report.sources
        if source.error
    ]
    return "; ".join(errors) if errors else None
