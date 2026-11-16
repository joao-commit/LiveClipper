"""Configuração central do LiveClipper.

Todas as variáveis podem ser definidas por ambiente com o prefixo
``LIVECLIPPER_`` ou em um arquivo ``.env`` na raiz do projeto.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação, carregada uma vez por processo."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LIVECLIPPER_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LiveClipper"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    data_dir: Path = Path("data")
    output_dir: Path = Path("output")
    database_url: str = "sqlite:///./data/liveclipper.db"

    # OBS: na Fase 1 a captura é feita lendo arquivos gravados pelo OBS.
    obs_recordings_dir: Path | None = None
    obs_websocket_url: str = "ws://127.0.0.1:4455"
    obs_websocket_password: str | None = None

    recording_extensions: str = ".mkv,.mp4,.mov,.flv,.ts"
    capture_poll_interval_seconds: float = Field(default=5.0, gt=0)
    capture_settle_seconds: float = Field(default=20.0, ge=0)
    capture_auto_start: bool = True

    @field_validator("api_prefix")
    @classmethod
    def _normalize_api_prefix(cls, value: str) -> str:
        stripped = value.strip().strip("/")
        return f"/{stripped}" if stripped else ""

    @field_validator("obs_recordings_dir", "obs_websocket_password", mode="before")
    @classmethod
    def _empty_optional_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("recording_extensions")
    @classmethod
    def _validate_recording_extensions(cls, value: str) -> str:
        if not _parse_extensions(value):
            raise ValueError("recording_extensions deve conter ao menos uma extensão")
        return value

    @property
    def extension_set(self) -> frozenset[str]:
        """Extensões normalizadas, minúsculas e com ponto inicial."""

        return frozenset(_parse_extensions(self.recording_extensions))

    def ensure_directories(self) -> None:
        """Cria os diretórios operacionais que não dependem do OBS."""

        self.data_dir.expanduser().mkdir(parents=True, exist_ok=True)
        self.output_dir.expanduser().mkdir(parents=True, exist_ok=True)
        if self.obs_recordings_dir is not None:
            self.obs_recordings_dir.expanduser().mkdir(parents=True, exist_ok=True)


def _parse_extensions(raw: str) -> set[str]:
    extensions: set[str] = set()
    for part in raw.split(","):
        extension = part.strip().lower()
        if not extension:
            continue
        if not extension.startswith("."):
            extension = f".{extension}"
        if "/" in extension or "\\" in extension:
            continue
        extensions.add(extension)
    return extensions


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a configuração do processo (memoizada)."""

    return Settings()
