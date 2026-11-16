"""Contrato comum para fontes de gravação."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class SourceUnavailableError(RuntimeError):
    """A fonte não está acessível no momento da leitura."""


@dataclass(frozen=True, slots=True)
class RecordingCandidate:
    """Arquivo candidato encontrado em uma fonte, ainda não persistido."""

    path: Path
    size_bytes: int
    modified_at: datetime


class SourceAdapter(ABC):
    """Leitura dos artefatos produzidos por uma fonte autorizada."""

    source_id: int
    name: str

    @abstractmethod
    def availability_error(self) -> str | None:
        """Retorna uma mensagem se a fonte não puder ser lida, ou ``None``."""

    @abstractmethod
    def scan(self) -> Iterable[RecordingCandidate]:
        """Lista candidatos. Não deve bloquear nem baixar conteúdo externo."""
