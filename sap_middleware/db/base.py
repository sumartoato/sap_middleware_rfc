"""Engine/session helpers for the two supported sync targets: MariaDB and PostgreSQL."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from sap_middleware.config import DBConfig
from sap_middleware.db.models import Base

_engines: dict[str, Engine] = {}


def get_engine(target: str) -> Engine:
    """target: 'mariadb' or 'postgres'."""
    if target not in _engines:
        url = DBConfig.MARIADB_URL if target == "mariadb" else DBConfig.POSTGRES_URL
        _engines[target] = create_engine(url, pool_pre_ping=True)
    return _engines[target]


def init_schema(target: str) -> None:
    Base.metadata.create_all(get_engine(target))


def get_session(target: str) -> Session:
    return sessionmaker(bind=get_engine(target))()
