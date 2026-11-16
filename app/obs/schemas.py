"""Contrato de resposta do diagnóstico de OBS."""

from __future__ import annotations

from pydantic import BaseModel


class ObsStatusRead(BaseModel):
    recordings_directory: str | None
    recordings_directory_exists: bool
    websocket_url: str
    file_capture_supported: bool
    message: str
