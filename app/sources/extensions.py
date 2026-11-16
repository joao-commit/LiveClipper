"""Normalização de extensões de arquivos de gravação."""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_EXTENSIONS: tuple[str, ...] = (".mkv", ".mp4", ".mov", ".flv", ".ts")


def normalize_extensions(values: Iterable[str]) -> list[str]:
    """Normaliza extensões para minúsculas, com ponto e sem duplicatas."""

    normalized: set[str] = set()
    for value in values:
        extension = value.strip().lower()
        if not extension:
            continue
        if not extension.startswith("."):
            extension = f".{extension}"
        if extension in {".", ".."} or "/" in extension or "\\" in extension:
            raise ValueError(f"extensão inválida: {value!r}")
        normalized.add(extension)

    if not normalized:
        raise ValueError("informe ao menos uma extensão de gravação")

    return sorted(normalized)
