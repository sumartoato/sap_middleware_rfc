"""Upserts rows fetched from SAP into MariaDB and/or PostgreSQL."""
from __future__ import annotations

import logging

from sqlalchemy import Table
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from sap_middleware.db.base import get_engine, init_schema
from sap_middleware.db.models import CompanyCode, Customer, Material
from sap_middleware.sap_connector import SAPConnector

logger = logging.getLogger(__name__)

TARGETS = ("mariadb", "postgres")


def _upsert(target: str, table: Table, rows: list[dict], key_columns: list[str]) -> int:
    if not rows:
        return 0
    engine = get_engine(target)
    if target == "mariadb":
        stmt = mysql_insert(table).values(rows)
        update_cols = {c.name: stmt.inserted[c.name] for c in table.columns if c.name not in key_columns}
        stmt = stmt.on_duplicate_key_update(**update_cols)
    elif target == "postgres":
        stmt = pg_insert(table).values(rows)
        update_cols = {c.name: stmt.excluded[c.name] for c in table.columns if c.name not in key_columns}
        stmt = stmt.on_conflict_do_update(index_elements=key_columns, set_=update_cols)
    else:
        raise ValueError(f"Unknown sync target: {target}")

    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("Upserted %d rows into %s.%s", len(rows), target, table.name)
    return len(rows)


def sync_customers(connector: SAPConnector, targets: list[str], max_rows: int = 100) -> int:
    rows = connector.get_customers(max_rows=max_rows)
    normalized = [{k.lower(): v for k, v in r.items()} for r in rows]
    count = 0
    for target in targets:
        init_schema(target)
        count = _upsert(target, Customer.__table__, normalized, key_columns=["kunnr"])
    return count


def sync_materials(connector: SAPConnector, targets: list[str], max_rows: int = 100) -> int:
    rows = connector.get_materials(max_rows=max_rows)
    normalized = [{k.lower(): v for k, v in r.items()} for r in rows]
    count = 0
    for target in targets:
        init_schema(target)
        count = _upsert(target, Material.__table__, normalized, key_columns=["matnr"])
    return count


def sync_company_codes(connector: SAPConnector, targets: list[str]) -> int:
    rows = connector.get_company_codes()
    normalized = [{k.lower(): v for k, v in r.items()} for r in rows]
    count = 0
    for target in targets:
        init_schema(target)
        count = _upsert(target, CompanyCode.__table__, normalized, key_columns=["bukrs"])
    return count


def sync_all(connector: SAPConnector, targets: list[str], max_rows: int = 100) -> dict[str, int]:
    return {
        "customers": sync_customers(connector, targets, max_rows),
        "materials": sync_materials(connector, targets, max_rows),
        "company_codes": sync_company_codes(connector, targets),
    }
