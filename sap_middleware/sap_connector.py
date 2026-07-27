"""Thin wrapper around SAP NW RFC (pyrfc) with a mock mode for local development.

Real RFC calls require:
  1. SAP NW RFC SDK (C libraries) installed, downloaded from SAP Support Portal
     with a valid S-user (https://support.sap.com/en/product/connectors/nwrfcsdk.html).
  2. The `pyrfc` python package built against that SDK (not on PyPI as a plain
     wheel for every platform -- see README for install instructions).

If pyrfc is not installed, or SAP_MOCK_MODE=true, the connector falls back to
reading the sample JSON files in examples/ so the rest of the pipeline
(sync to MariaDB/PostgreSQL) can be exercised without a real SAP system.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sap_middleware.config import MOCK_MODE, SAPConfig

logger = logging.getLogger(__name__)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

try:
    from pyrfc import Connection as _RFCConnection  # type: ignore

    PYRFC_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on local SAP NW RFC SDK install
    _RFCConnection = None
    PYRFC_AVAILABLE = False


class SAPConnectionError(RuntimeError):
    pass


class SAPConnector:
    """Fetches data from an SAP system via RFC, or from local mock fixtures."""

    def __init__(self, mock: bool | None = None):
        self.mock = MOCK_MODE if mock is None else mock
        self._conn = None
        if not self.mock and not PYRFC_AVAILABLE:
            raise SAPConnectionError(
                "pyrfc is not installed. Install the SAP NW RFC SDK and pyrfc, "
                "or set SAP_MOCK_MODE=true to run against sample data."
            )

    def __enter__(self) -> "SAPConnector":
        if not self.mock:
            params = SAPConfig.as_connection_params()
            missing = [k for k in ("ashost", "user", "passwd") if not params.get(k)]
            if missing:
                raise SAPConnectionError(f"Missing SAP connection settings: {missing}")
            logger.info("Connecting to SAP ashost=%s sysnr=%s client=%s", params["ashost"], params["sysnr"], params["client"])
            self._conn = _RFCConnection(**params)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def ping(self) -> bool:
        if self.mock:
            return True
        result = self._conn.call("STFC_CONNECTION", REQUTEXT="ping")
        return bool(result.get("ECHOTEXT"))

    def call(self, function_name: str, **params) -> dict[str, Any]:
        if self.mock:
            raise SAPConnectionError(f"Cannot call RFC '{function_name}' in mock mode")
        return self._conn.call(function_name, **params)

    def read_table(
        self,
        table_name: str,
        fields: list[str],
        max_rows: int = 100,
        where_clause: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Generic table read via the standard RFC_READ_TABLE function module."""
        if self.mock:
            return self._load_mock(table_name)

        options = [{"TEXT": w} for w in (where_clause or [])]
        fields_param = [{"FIELDNAME": f.upper()} for f in fields]
        result = self.call(
            "RFC_READ_TABLE",
            QUERY_TABLE=table_name,
            DELIMITER="|",
            ROWCOUNT=max_rows,
            OPTIONS=options,
            FIELDS=fields_param,
        )
        returned_fields = [f["FIELDNAME"] for f in result["FIELDS"]]
        offsets = [(f["FIELDNAME"], int(f["OFFSET"]), int(f["LENGTH"])) for f in result["FIELDS"]]
        rows = []
        for line in result["DATA"]:
            raw = line["WA"]
            row = {}
            for fieldname, offset, length in offsets:
                row[fieldname] = raw[offset : offset + length].strip()
            rows.append(row)
        logger.info("Read %d rows from %s (fields=%s)", len(rows), table_name, returned_fields)
        return rows

    def get_customers(self, max_rows: int = 100) -> list[dict[str, str]]:
        return self.read_table(
            "KNA1",
            fields=["KUNNR", "NAME1", "LAND1", "ORT01", "PSTLZ", "STRAS"],
            max_rows=max_rows,
        )

    def get_materials(self, max_rows: int = 100) -> list[dict[str, str]]:
        return self.read_table(
            "MARA",
            fields=["MATNR", "MTART", "MATKL", "MEINS", "ERSDA"],
            max_rows=max_rows,
        )

    def get_company_codes(self) -> list[dict[str, str]]:
        if self.mock:
            return self._load_mock("company_codes")
        result = self.call("BAPI_COMPANYCODE_GETLIST")
        return [
            {
                "BUKRS": row["COMP_CODE"],
                "BUTXT": row["COMP_NAME"],
                "WAERS": row["CITY"],
            }
            for row in result.get("COMPANYCODE_LIST", [])
        ]

    @staticmethod
    def _load_mock(name: str) -> list[dict[str, str]]:
        mapping = {
            "KNA1": "sample_customers.json",
            "MARA": "sample_materials.json",
            "company_codes": "sample_company_codes.json",
        }
        filename = mapping.get(name)
        if not filename:
            raise SAPConnectionError(f"No mock fixture registered for '{name}'")
        path = EXAMPLES_DIR / filename
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
