"""Contratos de entrada e saída das fontes de captura."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceCreate(BaseModel):
    """Cadastro de uma fonte autorizada.

    ``authorization_confirmed`` precisa ser ``true`` de forma explícita. O
    sistema registra a referência da autorização, mas não valida a existência
    jurídica do documento.
    """

    name: str = Field(min_length=1, max_length=160)
    platform: str = Field(default="youtube", min_length=1, max_length=80)
    creator_name: str = Field(min_length=1, max_length=160)
    authorization_reference: str = Field(min_length=3, max_length=255)
    authorization_notes: str | None = Field(default=None, max_length=2000)
    authorization_confirmed: bool
    watch_directory: Path | None = None
    file_extensions: list[str] | None = None
    enabled: bool = True

    @field_validator("name", "platform", "creator_name", "authorization_reference")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campo obrigatório não pode ser vazio")
        return stripped

    @field_validator("authorization_notes")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _require_authorization(self) -> SourceCreate:
        if not self.authorization_confirmed:
            raise ValueError(
                "authorization_confirmed deve ser true: capture apenas conteúdo "
                "com autorização de captura e reutilização"
            )
        return self


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: str
    creator_name: str
    authorization_reference: str
    authorization_notes: str | None
    authorized_at: datetime
    watch_directory: str
    file_extensions: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
