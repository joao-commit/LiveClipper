"""Contratos HTTP da captura e das gravações."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.capture.monitor import CaptureMonitorStatus
from app.capture.scanner import ScanReport, SourceScanReport
from app.database.models import RecordingStatus


class RecordingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    path: str
    filename: str
    size_bytes: int
    modified_at: datetime
    status: RecordingStatus
    discovered_at: datetime
    ready_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class RecordingPage(BaseModel):
    items: list[RecordingRead]
    total: int
    limit: int
    offset: int


class SourceScanReportRead(BaseModel):
    source_id: int
    source_name: str
    scanned_files: int
    registered_recording_ids: list[int]
    registered_total: int
    duplicates: int
    unstable: int
    ignored: int
    error: str | None

    @classmethod
    def from_report(cls, report: SourceScanReport) -> SourceScanReportRead:
        return cls(
            source_id=report.source_id,
            source_name=report.source_name,
            scanned_files=report.scanned_files,
            registered_recording_ids=list(report.registered_recording_ids),
            registered_total=len(report.registered_recording_ids),
            duplicates=report.duplicates,
            unstable=report.unstable,
            ignored=report.ignored,
            error=report.error,
        )


class ScanReportRead(BaseModel):
    registered_total: int
    sources: list[SourceScanReportRead]

    @classmethod
    def from_report(cls, report: ScanReport) -> ScanReportRead:
        return cls(
            registered_total=report.registered_total,
            sources=[SourceScanReportRead.from_report(item) for item in report.sources],
        )


class CaptureMonitorStatusRead(BaseModel):
    running: bool
    poll_interval_seconds: float
    last_scan_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None

    @classmethod
    def from_status(cls, status: CaptureMonitorStatus) -> CaptureMonitorStatusRead:
        return cls(
            running=status.running,
            poll_interval_seconds=status.poll_interval_seconds,
            last_scan_at=status.last_scan_at,
            last_success_at=status.last_success_at,
            last_error=status.last_error,
        )
