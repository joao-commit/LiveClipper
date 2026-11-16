"""Agregação dos routers versionados da API."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import capture, obs, recordings, sources


def build_api_router(prefix: str) -> APIRouter:
    router = APIRouter(prefix=prefix)
    router.include_router(sources.router)
    router.include_router(recordings.router)
    router.include_router(capture.router)
    router.include_router(obs.router)
    return router
