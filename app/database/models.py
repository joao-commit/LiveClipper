"""Modelos ORM do LiveClipper."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UTCDateTime, utc_now


class RecordingStatus(StrEnum):
    """Ciclo de vida de uma gravação ingerida."""

    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    IGNORED = "ignored"


def _default_file_extensions() -> list[str]:
    return [".mkv", ".mp4", ".mov", ".flv", ".ts"]


class CaptureSource(TimestampMixin, Base):
    """Fonte de captura autorizada.

    A autorização é um pré-requisito de negócio: o operador deve manter a
    evidência (contrato, e-mail, termo) referenciada em
    ``authorization_reference``. O sistema não substitui essa autorização.
    """

    __tablename__ = "capture_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(80), default="youtube", nullable=False)
    creator_name: Mapped[str] = mapped_column(String(160), nullable=False)

    authorization_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    authorization_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorized_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )

    watch_directory: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_extensions: Mapped[list[str]] = mapped_column(
        JSON, default=_default_file_extensions, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    recordings: Mapped[list[Recording]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - representação de depuração
        return f"CaptureSource(id={self.id!r}, name={self.name!r}, enabled={self.enabled!r})"


class Recording(TimestampMixin, Base):
    """Arquivo de gravação descoberto na pasta de uma fonte autorizada."""

    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("capture_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    path: Mapped[str] = mapped_column(String(2048), unique=True, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    modified_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    status: Mapped[RecordingStatus] = mapped_column(
        Enum(
            RecordingStatus,
            name="recording_status",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=RecordingStatus.READY,
        nullable=False,
    )
    discovered_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )
    ready_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[CaptureSource] = relationship(back_populates="recordings")

    def __repr__(self) -> str:  # pragma: no cover - representação de depuração
        return f"Recording(id={self.id!r}, filename={self.filename!r}, status={self.status!r})"
