"""Endpoint de health check com verificação do banco e do monitor."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import get_session, get_settings
from app.api.schemas import HealthResponse
from app.capture.monitor import CaptureMonitorStatus
from app.capture.schemas import CaptureMonitorStatusRead
from app.config import Settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        database_status: Literal["ok", "error"] = "ok"
    except SQLAlchemyError:
        database_status = "error"

    monitor = getattr(request.app.state, "capture_monitor", None)
    if monitor is not None:
        monitor_status = monitor.status()
    else:
        monitor_status = CaptureMonitorStatus(
            running=False,
            poll_interval_seconds=settings.capture_poll_interval_seconds,
            last_scan_at=None,
            last_success_at=None,
            last_error=None,
        )

    overall: Literal["ok", "degraded"] = (
        "ok" if database_status == "ok" else "degraded"
    )
    if overall == "degraded":
        response.status_code = 503

    return HealthResponse(
        status=overall,
        database=database_status,
        version=__version__,
        environment=settings.environment,
        capture_monitor=CaptureMonitorStatusRead.from_status(monitor_status),
    )
