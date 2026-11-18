"""Fonte de gravações locais produzidas pelo OBS Studio."""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from app.sources.base import RecordingCandidate, SourceAdapter, SourceUnavailableError


class LocalObsDirectorySource(SourceAdapter):
    """Lê arquivos finalizados ou em escrita em um diretório do OBS.

    A decisão sobre o arquivo estar estável (gravação encerrada) é do serviço
    de captura, não do adaptador.
    """

    def __init__(
        self,
        *,
        source_id: int,
        name: str,
        directory: Path,
        extensions: Iterable[str],
    ) -> None:
        self.source_id = source_id
        self.name = name
        # Resolve uma vez para comparar a contenção dos arquivos encontrados.
        self.directory = directory.expanduser().resolve()
        self.extensions = frozenset(extension.lower() for extension in extensions)

    def availability_error(self) -> str | None:
        if not self.directory.exists():
            return f"diretório não encontrado: {self.directory}"
        if not self.directory.is_dir():
            return f"o caminho não é um diretório: {self.directory}"
        if not os.access(self.directory, os.R_OK):
            return f"diretório sem permissão de leitura: {self.directory}"
        return None

    def scan(self) -> Iterable[RecordingCandidate]:
        error = self.availability_error()
        if error is not None:
            raise SourceUnavailableError(error)

        try:
            entries = sorted(self.directory.iterdir(), key=lambda entry: entry.name.casefold())
        except OSError as exc:
            raise SourceUnavailableError(
                f"falha ao listar o diretório {self.directory}: {exc}"
            ) from exc

        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                if entry.is_symlink() or not entry.is_file():
                    continue
            except OSError:
                continue
            if entry.suffix.lower() not in self.extensions:
                continue
            if not os.access(entry, os.R_OK):
                continue

            try:
                stat = entry.stat()
                resolved = entry.resolve()
            except OSError:
                continue

            # Garante que o arquivo pertence ao diretório autorizado, mesmo
            # diante de links simbólicos ou alterações durante a varredura.
            if not resolved.is_relative_to(self.directory):
                continue

            yield RecordingCandidate(
                path=resolved,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            )
