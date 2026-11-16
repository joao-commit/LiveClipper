"""Testes unitários das extensões de arquivos."""

from __future__ import annotations

import pytest

from app.sources.extensions import normalize_extensions


def test_normalize_extensions() -> None:
    assert normalize_extensions(["MKV", ".mp4", "mov", "mkv"]) == [
        ".mkv",
        ".mov",
        ".mp4",
    ]


@pytest.mark.parametrize("values", [[], ["   "], ["../mkv"], ["a/b"]])
def test_normalize_extensions_rejects_invalid(values: list[str]) -> None:
    with pytest.raises(ValueError):
        normalize_extensions(values)
