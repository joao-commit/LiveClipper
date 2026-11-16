"""Schemas de saúde e diagnóstico do processo."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.capture.schemas import CaptureMonitorStatusRead


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]
    version: str
    environment: str
    capture_monitor: CaptureMonitorStatusRead
