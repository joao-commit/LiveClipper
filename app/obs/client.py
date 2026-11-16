"""Contrato para um futuro cliente OBS WebSocket (protocolo v5)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class ObsClientUnavailable(RuntimeError):
    """Cliente OBS WebSocket não instalado ou não configurado."""


@runtime_checkable
class ObsClient(Protocol):
    """Operações que o LiveClipper poderá usar do OBS em fases futuras."""

    async def get_version(self) -> dict[str, Any]:
        ...

    async def get_record_status(self) -> dict[str, Any]:
        ...

    async def get_record_directory(self) -> str:
        ...
