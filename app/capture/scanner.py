"""Varredura de arquivos de gravação e registro no banco.

A Fase 1 não copia nem baixa conteúdo: apenas lê arquivos que o OBS já gravou
em diretórios de fontes cadastradas e autorizadas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.base import utc_now
from app.database.models import CaptureSource, Recording, RecordingStatus
from app.database.repositories import RecordingRepository, SourceRepository
from app.sources.base import SourceUnavailableError
from app.sources.factory import build_source_adapter

logger = logging.getLogger(__name__)


class SourceNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class SourceScanReport:
    """Resultado da varredura de uma fonte."""

    source_id: int
    source_name: str
    scanned_files: int = 0
    registered_recording_ids: list[int] = field(default_factory=list)
    duplicates: int = 0
    unstable: int = 0
    ignored: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ScanReport:
    """Resultado agregado de uma varredura."""

    sources: list[SourceScanReport]

    @property
    def registered_total(self) -> int:
        return sum(len(source.registered_recording_ids) for source in self.sources)


def scan_sources(
    session: Session,
    settings: Settings,
    *,
    source_id: int | None = None,
    now: datetime | None = None,
) -> ScanReport:
    """Varre todas as fontes habilitadas, ou apenas uma fonte específica."""

    effective_now = now or utc_now()
    repository = SourceRepository(session)

    if source_id is not None:
        source = repository.get(source_id)
        if source is None:
            raise SourceNotFound(f"fonte {source_id} não encontrada")
        sources = [source]
    else:
        sources = repository.list(enabled_only=True)

    reports: list[SourceScanReport] = []
    for source in sources:
        try:
            reports.append(
                scan_source(session, source, settings, now=effective_now)
            )
        except Exception as exc:  # pragma: no cover - proteção do loop do monitor
            session.rollback()
            logger.exception("Falha inesperada ao varrer a fonte %s", source.name)
            reports.append(
                SourceScanReport(
                    source_id=source.id,
                    source_name=source.name,
                    error=f"falha inesperada: {exc}",
                )
            )

    return ScanReport(sources=reports)


def scan_source(
    session: Session,
    source: CaptureSource,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> SourceScanReport:
    """Varre uma fonte e registra arquivos que já estão estáveis."""

    effective_now = now or utc_now()

    if not source.enabled:
        return SourceScanReport(
            source_id=source.id,
            source_name=source.name,
            error="fonte desabilitada",
        )
    if not source.authorization_reference or source.authorized_at is None:
        return SourceScanReport(
            source_id=source.id,
            source_name=source.name,
            error="autorização de captura não confirmada para a fonte",
        )

    adapter = build_source_adapter(source)
    availability_error = adapter.availability_error()
    if availability_error is not None:
        return SourceScanReport(
            source_id=source.id,
            source_name=source.name,
            error=availability_error,
        )

    try:
        candidates = list(adapter.scan())
    except SourceUnavailableError as exc:
        return SourceScanReport(
            source_id=source.id,
            source_name=source.name,
            error=str(exc),
        )

    recording_repository = RecordingRepository(session)
    settle_cutoff = effective_now - timedelta(seconds=settings.capture_settle_seconds)
    scanned_files = 0
    registered_ids: list[int] = []
    duplicates = 0
    unstable = 0
    ignored = 0

    for candidate in candidates:
        scanned_files += 1

        if candidate.size_bytes <= 0:
            ignored += 1
            continue
        if candidate.modified_at > settle_cutoff:
            unstable += 1
            continue

        path = str(candidate.path)
        if recording_repository.get_by_path(path) is not None:
            duplicates += 1
            continue

        recording = Recording(
            source_id=source.id,
            path=path,
            filename=candidate.path.name,
            size_bytes=candidate.size_bytes,
            modified_at=candidate.modified_at,
            status=RecordingStatus.READY,
            discovered_at=effective_now,
            ready_at=effective_now,
        )

        try:
            with session.begin_nested():
                session.add(recording)
                session.flush()
            registered_ids.append(recording.id)
        except IntegrityError:
            # Corrida com outra varredura: a restrição única de path protege.
            duplicates += 1

    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Falha ao persistir gravações da fonte %s", source.name)
        return SourceScanReport(
            source_id=source.id,
            source_name=source.name,
            scanned_files=scanned_files,
            duplicates=duplicates,
            unstable=unstable,
            ignored=ignored,
            error=f"falha ao persistir gravações: {exc}",
        )

    return SourceScanReport(
        source_id=source.id,
        source_name=source.name,
        scanned_files=scanned_files,
        registered_recording_ids=registered_ids,
        duplicates=duplicates,
        unstable=unstable,
        ignored=ignored,
    )
