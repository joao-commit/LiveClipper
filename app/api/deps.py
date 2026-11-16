"""Dependências compartilhadas pelas rotas."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.capture.monitor import CaptureMonitor
from app.config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_capture_monitor(request: Request) -> CaptureMonitor | None:
    return getattr(request.app.state, "capture_monitor", None)
