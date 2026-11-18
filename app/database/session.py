"""Criação do engine e das sessões SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_database_engine(database_url: str) -> Engine:
    """Cria um engine adequado ao banco configurado.

    Para SQLite, desabilita a checagem de thread (a API usa sessões em
    requisições e o monitor roda em uma thread separada) e habilita chaves
    estrangeiras e espera por locks.
    """

    options: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url or database_url.rstrip("/") == "sqlite:":
            options["poolclass"] = StaticPool

    engine = create_engine(database_url, **options)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
            finally:
                cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def init_db(engine: Engine) -> None:
    """Cria as tabelas iniciais.

    O schema atual usa ``create_all`` por ser um banco novo. Quando o schema
    evoluir, a migração deverá ser feita com Alembic em uma fase própria.
    """

    from app.database import models  # noqa: F401  (registra os modelos no metadata)
    from app.database.base import Base

    Base.metadata.create_all(engine)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
