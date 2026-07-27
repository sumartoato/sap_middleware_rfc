#!/usr/bin/env python3
"""CLI entrypoint for the SAP RFC middleware.

Examples:
    python main.py test-connection
    python main.py sync --object customers --target both
    python main.py sync --object all --target mariadb
"""
from __future__ import annotations

import argparse
import logging
import sys

from sap_middleware.sap_connector import SAPConnectionError, SAPConnector
from sap_middleware.sync.sync_service import (
    TARGETS,
    sync_all,
    sync_company_codes,
    sync_customers,
    sync_materials,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sap_middleware.cli")


def _resolve_targets(target: str) -> list[str]:
    return list(TARGETS) if target == "both" else [target]


def cmd_test_connection(args: argparse.Namespace) -> int:
    try:
        with SAPConnector() as sap:
            ok = sap.ping()
    except SAPConnectionError as exc:
        logger.error("Connection failed: %s", exc)
        return 1
    logger.info("SAP connection OK (mock=%s): %s", sap.mock, ok)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    targets = _resolve_targets(args.target)
    try:
        with SAPConnector() as sap:
            if args.object == "customers":
                n = sync_customers(sap, targets, max_rows=args.max_rows)
                logger.info("Synced %d customers to %s", n, targets)
            elif args.object == "materials":
                n = sync_materials(sap, targets, max_rows=args.max_rows)
                logger.info("Synced %d materials to %s", n, targets)
            elif args.object == "company-codes":
                n = sync_company_codes(sap, targets)
                logger.info("Synced %d company codes to %s", n, targets)
            else:
                result = sync_all(sap, targets, max_rows=args.max_rows)
                logger.info("Synced to %s: %s", targets, result)
    except SAPConnectionError as exc:
        logger.error("Sync aborted: %s", exc)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SAP RFC middleware CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("test-connection", help="Check RFC connectivity to SAP").set_defaults(func=cmd_test_connection)

    p_sync = sub.add_parser("sync", help="Fetch data from SAP and sync it to a database")
    p_sync.add_argument(
        "--object",
        choices=["customers", "materials", "company-codes", "all"],
        default="all",
        help="Which SAP data set to sync",
    )
    p_sync.add_argument(
        "--target",
        choices=[*TARGETS, "both"],
        default="both",
        help="Where to write the data",
    )
    p_sync.add_argument("--max-rows", type=int, default=100, help="Max rows to read per table")
    p_sync.set_defaults(func=cmd_sync)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
