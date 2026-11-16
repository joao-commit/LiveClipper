"""Consultas de persistência reutilizadas pela API e pelo monitor."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import CaptureSource, Recording, RecordingStatus


class SourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, source_id: int) -> CaptureSource | None:
        return self.session.get(CaptureSource, source_id)

    def get_by_name(self, name: str) -> CaptureSource | None:
        return self.session.scalar(select(CaptureSource).where(CaptureSource.name == name))

    def list(self, *, enabled_only: bool = False) -> list[CaptureSource]:
        statement = select(CaptureSource).order_by(CaptureSource.name)
        if enabled_only:
            statement = statement.where(CaptureSource.enabled.is_(True))
        return list(self.session.scalars(statement))

    def add(self, source: CaptureSource) -> CaptureSource:
        self.session.add(source)
        self.session.flush()
        return source


class RecordingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, recording_id: int) -> Recording | None:
        return self.session.get(Recording, recording_id)

    def get_by_path(self, path: str) -> Recording | None:
        return self.session.scalar(select(Recording).where(Recording.path == path))

    def add(self, recording: Recording) -> Recording:
        self.session.add(recording)
        self.session.flush()
        return recording

    def list(
        self,
        *,
        limit: int,
        offset: int,
        status: RecordingStatus | None = None,
        source_id: int | None = None,
    ) -> tuple[list[Recording], int]:
        filters = []
        if status is not None:
            filters.append(Recording.status == status)
        if source_id is not None:
            filters.append(Recording.source_id == source_id)

        total = self.session.scalar(
            select(func.count()).select_from(Recording).where(*filters)
        ) or 0
        statement = (
            select(Recording)
            .where(*filters)
            .order_by(Recording.discovered_at.desc(), Recording.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement)), total
