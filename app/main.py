"""Ponto de entrada da API e do processo de captura."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.router import build_api_router
from app.api.routes.health import router as health_router
from app.capture.monitor import CaptureMonitor
from app.config import Settings, get_settings
from app.database.session import (
    create_database_engine,
    create_session_factory,
    init_db,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação com configuração injetável (facilita testes)."""

    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(
            level=getattr(logging, app_settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        app_settings.ensure_directories()

        engine = create_database_engine(app_settings.database_url)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.capture_monitor = None

        try:
            init_db(engine)
            monitor: CaptureMonitor | None = None
            if app_settings.capture_auto_start:
                monitor = CaptureMonitor(app.state.session_factory, app_settings)
                app.state.capture_monitor = monitor
                await monitor.start()

            logger.info(
                "LiveClipper %s iniciado (ambiente=%s, banco=%s)",
                __version__,
                app_settings.environment,
                app_settings.database_url,
            )
            yield
        finally:
            monitor = getattr(app.state, "capture_monitor", None)
            if monitor is not None:
                await monitor.stop()
            engine.dispose()
            logger.info("LiveClipper encerrado")

    application = FastAPI(
        title=app_settings.app_name,
        version=__version__,
        description=(
            "Detecção de momentos interessantes em transmissões ao vivo "
            "autorizadas. A fundação atual ingere gravações locais produzidas "
            "pelo OBS Studio; a análise de áudio será adicionada na fase de "
            "detecção."
        ),
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.include_router(health_router)
    application.include_router(build_api_router(app_settings.api_prefix))

    @application.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "name": app_settings.app_name,
            "version": __version__,
            "phase": "1 - fundação OBS (revisão de escopo 2.0)",
            "docs": "/docs",
            "health": "/health",
        }

    return application


app = create_app()
