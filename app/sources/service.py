"""Regras de cadastro e consulta de fontes autorizadas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.base import utc_now
from app.database.models import CaptureSource
from app.database.repositories import SourceRepository
from app.sources.extensions import normalize_extensions
from app.sources.schemas import SourceCreate


class SourceError(Exception):
    """Erro de negócio relacionado a fontes de captura."""


class SourceNameConflict(SourceError):
    pass


class SourceDirectoryNotConfigured(SourceError):
    pass


class SourceDirectoryInvalid(SourceError):
    pass


class SourceValidationError(SourceError):
    pass


def register_source(
    session: Session,
    payload: SourceCreate,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> CaptureSource:
    """Persiste uma fonte após validar autorização e diretório de leitura."""

    repository = SourceRepository(session)
    if repository.get_by_name(payload.name) is not None:
        raise SourceNameConflict(f"já existe uma fonte chamada {payload.name!r}")

    configured_directory = payload.watch_directory or settings.obs_recordings_dir
    if configured_directory is None:
        raise SourceDirectoryNotConfigured(
            "watch_directory não informado e LIVECLIPPER_OBS_RECORDINGS_DIR não configurado"
        )

    directory = _resolve_directory(configured_directory)
    try:
        file_extensions = normalize_extensions(
            payload.file_extensions or settings.extension_set
        )
    except ValueError as exc:
        raise SourceValidationError(str(exc)) from exc

    source = CaptureSource(
        name=payload.name,
        platform=payload.platform,
        creator_name=payload.creator_name,
        authorization_reference=payload.authorization_reference,
        authorization_notes=payload.authorization_notes,
        authorized_at=now or utc_now(),
        watch_directory=str(directory),
        file_extensions=file_extensions,
        enabled=payload.enabled,
    )

    try:
        repository.add(source)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise SourceNameConflict(f"já existe uma fonte chamada {payload.name!r}") from exc

    session.refresh(source)
    return source


def list_sources(session: Session, *, enabled_only: bool = False) -> list[CaptureSource]:
    return SourceRepository(session).list(enabled_only=enabled_only)


def get_source(session: Session, source_id: int) -> CaptureSource | None:
    return SourceRepository(session).get(source_id)


def _resolve_directory(directory: Path) -> Path:
    try:
        resolved = directory.expanduser().resolve()
    except OSError as exc:
        raise SourceDirectoryInvalid(
            f"não foi possível resolver o diretório {directory}: {exc}"
        ) from exc

    if not resolved.exists():
        raise SourceDirectoryInvalid(f"diretório não encontrado: {resolved}")
    if not resolved.is_dir():
        raise SourceDirectoryInvalid(f"o caminho não é um diretório: {resolved}")
    return resolved
