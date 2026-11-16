"""Consulta das gravações ingeridas."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.capture.schemas import RecordingPage, RecordingRead
from app.database.models import RecordingStatus
from app.database.repositories import RecordingRepository

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("", response_model=RecordingPage)
def read_recordings(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: RecordingStatus | None = Query(default=None, alias="status"),
    source_id: int | None = Query(default=None, ge=1),
) -> RecordingPage:
    items, total = RecordingRepository(session).list(
        limit=limit,
        offset=offset,
        status=status_filter,
        source_id=source_id,
    )
    return RecordingPage(
        items=[RecordingRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{recording_id}", response_model=RecordingRead)
def read_recording(
    recording_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RecordingRead:
    recording = RecordingRepository(session).get(recording_id)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="gravação não encontrada"
        )
    return RecordingRead.model_validate(recording)
