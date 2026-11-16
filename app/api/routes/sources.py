"""Cadastro e consulta de fontes de captura autorizadas."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_session, get_settings
from app.config import Settings
from app.sources.schemas import SourceCreate, SourceRead
from app.sources.service import (
    SourceDirectoryInvalid,
    SourceDirectoryNotConfigured,
    SourceNameConflict,
    SourceValidationError,
    get_source,
    list_sources,
    register_source,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreate,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SourceRead:
    try:
        source = register_source(session, payload, settings)
    except SourceNameConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (
        SourceDirectoryNotConfigured,
        SourceDirectoryInvalid,
        SourceValidationError,
    ) as exc:
        raise HTTPException(
            status_code=422, detail=str(exc)
        ) from exc

    return SourceRead.model_validate(source)


@router.get("", response_model=list[SourceRead])
def read_sources(
    session: Annotated[Session, Depends(get_session)],
    enabled_only: bool = False,
) -> list[SourceRead]:
    sources = list_sources(session, enabled_only=enabled_only)
    return [SourceRead.model_validate(source) for source in sources]


@router.get("/{source_id}", response_model=SourceRead)
def read_source(
    source_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> SourceRead:
    source = get_source(session, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="fonte não encontrada")
    return SourceRead.model_validate(source)
