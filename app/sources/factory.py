"""Construção do adaptador adequado para uma fonte persistida.

A origem do vídeo é abstraída por :class:`~app.sources.base.SourceAdapter`.
Novos adaptadores (por exemplo, um leitor via OBS WebSocket, armazenamento em
nuvem ou um diretório remoto) podem ser registrados sem alterar o scanner ou
o monitor de captura.

A Fase 1 registra apenas o adaptador de diretório local alimentado pelo OBS.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.database.models import CaptureSource
from app.sources.base import SourceAdapter
from app.sources.local import LocalObsDirectorySource

#: Nome usado quando a configuração não informa um adaptador.
DEFAULT_SOURCE_ADAPTER = "obs_directory"

SourceAdapterBuilder = Callable[[CaptureSource], SourceAdapter]

_REGISTRY: dict[str, SourceAdapterBuilder] = {}


class UnknownSourceAdapter(LookupError):
    """O adaptador solicitado não foi registrado no processo."""


def register_source_adapter(
    name: str,
    builder: SourceAdapterBuilder,
    *,
    replace: bool = False,
) -> None:
    """Registra uma implementação de ``SourceAdapter`` pelo nome.

    ``replace=True`` permite que testes ou integrações substituam um adaptador
    já registrado de forma deliberada.
    """

    key = _normalize_name(name)
    if key in _REGISTRY and not replace:
        raise ValueError(f"adaptador de fonte já registrado: {key!r}")
    _REGISTRY[key] = builder


def available_source_adapters() -> tuple[str, ...]:
    """Nomes registrados, em ordem estável (útil para diagnóstico)."""

    return tuple(sorted(_REGISTRY))


def build_source_adapter(
    source: CaptureSource,
    adapter_name: str | None = None,
) -> SourceAdapter:
    """Cria o adaptador da fonte.

    ``adapter_name`` vem de ``LIVECLIPPER_SOURCE_ADAPTER``. Quando omitido, usa
    o adaptador local do OBS. Uma fase futura poderá persistir o tipo por fonte
    sem quebrar este contrato.
    """

    key = _normalize_name(adapter_name or DEFAULT_SOURCE_ADAPTER)
    builder = _REGISTRY.get(key)
    if builder is None:
        registered = ", ".join(available_source_adapters()) or "nenhum"
        raise UnknownSourceAdapter(
            f"adaptador de fonte desconhecido: {key!r} "
            f"(registrados: {registered})"
        )
    return builder(source)


def _normalize_name(name: str) -> str:
    key = name.strip().lower()
    if not key:
        raise ValueError("o nome do adaptador de fonte não pode ser vazio")
    return key


def _build_local_obs_directory(source: CaptureSource) -> SourceAdapter:
    return LocalObsDirectorySource(
        source_id=source.id,
        name=source.name,
        directory=Path(source.watch_directory),
        extensions=source.file_extensions,
    )


register_source_adapter(DEFAULT_SOURCE_ADAPTER, _build_local_obs_directory)
