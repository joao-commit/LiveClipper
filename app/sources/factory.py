"""Construção do adaptador adequado para uma fonte persistida."""

from __future__ import annotations

from pathlib import Path

from app.database.models import CaptureSource
from app.sources.base import SourceAdapter
from app.sources.local import LocalObsDirectorySource


def build_source_adapter(source: CaptureSource) -> SourceAdapter:
    """Cria o adaptador da fonte.

    A Fase 1 suporta exclusivamente arquivos locais gravados pelo OBS.
    """

    return LocalObsDirectorySource(
        source_id=source.id,
        name=source.name,
        directory=Path(source.watch_directory),
        extensions=source.file_extensions,
    )
