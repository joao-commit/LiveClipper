"""Diagnóstico da configuração de OBS sem abrir conexão com o aplicativo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import Settings


@dataclass(frozen=True, slots=True)
class ObsStatus:
    recordings_directory: str | None
    recordings_directory_exists: bool
    websocket_url: str
    file_capture_supported: bool
    message: str


def probe_obs_status(settings: Settings) -> ObsStatus:
    """Inspeciona configuração e disponibilidade local do OBS.

    Não tenta conectar no WebSocket: a Fase 1 funciona apenas com arquivos.
    """

    directory: Path | None = settings.obs_recordings_dir
    directory_exists = bool(directory and directory.expanduser().is_dir())

    if directory is None:
        message = (
            "Nenhum diretório global do OBS configurado. Cadastre watch_directory "
            "por fonte autorizada."
        )
    elif not directory_exists:
        message = (
            f"O diretório configurado não existe: {directory.expanduser()}. "
            "Ajuste a saída de gravação do OBS."
        )
    else:
        message = (
            "Captura por arquivos do OBS habilitada. O WebSocket é opcional "
            "e ainda não é usado para controle."
        )

    return ObsStatus(
        recordings_directory=str(directory.expanduser()) if directory else None,
        recordings_directory_exists=directory_exists,
        websocket_url=settings.obs_websocket_url,
        file_capture_supported=True,
        message=message,
    )
