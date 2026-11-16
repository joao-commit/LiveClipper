"""Execução manual e diagnóstico do monitor de captura."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_capture_monitor, get_session, get_settings
from app.capture.monitor import CaptureMonitor, CaptureMonitorStatus
from app.capture.scanner import SourceNotFound, scan_sources
from app.capture.schemas import CaptureMonitorStatusRead, ScanReportRead
from app.config import Settings

router = APIRouter(prefix="/capture", tags=["capture"])


@router.post("/scan", response_model=ScanReportRead)
def scan_now(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    source_id: int | None = Query(default=None, ge=1),
) -> ScanReportRead:
    try:
        report = scan_sources(session, settings, source_id=source_id)
    except SourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return ScanReportRead.from_report(report)


@router.get("/status", response_model=CaptureMonitorStatusRead)
def capture_status(
    settings: Annotated[Settings, Depends(get_settings)],
    monitor: Annotated[CaptureMonitor | None, Depends(get_capture_monitor)],
) -> CaptureMonitorStatusRead:
    if monitor is None:
        status_snapshot = CaptureMonitorStatus(
            running=False,
            poll_interval_seconds=settings.capture_poll_interval_seconds,
            last_scan_at=None,
            last_success_at=None,
            last_error=None,
        )
    else:
        status_snapshot = monitor.status()
    return CaptureMonitorStatusRead.from_status(status_snapshot)
