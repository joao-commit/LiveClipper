"""Diagnóstico da integração com o OBS Studio."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.config import Settings
from app.obs.schemas import ObsStatusRead
from app.obs.status import probe_obs_status

router = APIRouter(prefix="/obs", tags=["obs"])


@router.get("/status", response_model=ObsStatusRead)
def read_obs_status(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ObsStatusRead:
    status_snapshot = probe_obs_status(settings)
    return ObsStatusRead(
        recordings_directory=status_snapshot.recordings_directory,
        recordings_directory_exists=status_snapshot.recordings_directory_exists,
        websocket_url=status_snapshot.websocket_url,
        file_capture_supported=status_snapshot.file_capture_supported,
        message=status_snapshot.message,
    )
