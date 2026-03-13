#!/usr/bin/env python3
"""Test script — run the Genie Space creation pipeline locally.

Usage:
    PYTHONPATH=src DATABRICKS_TOKEN=<token> DATABRICKS_PROFILE=vm python scripts/run_pipeline.py
"""

import json
import logging
import os
import sys

from genieapp.backend.pipeline.run import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# --- Config ---
CATALOG = "yd_launchpad_final_classic_catalog"
WAREHOUSE_ID = "551addcb4415adb7"
DATABRICKS_HOST = "7474655921234161"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

# --- Test company ---
COMPANY_NAME = "NovaTech Logistics"
COMPANY_DESCRIPTION = """NovaTech Logistics is a mid-size freight and logistics company operating across
North America and Europe. They manage a fleet of 2,000+ trucks and work with 500+ warehouses.
Their core data includes shipment tracking, warehouse inventory, fleet maintenance, driver performance,
and customer contracts. They care about on-time delivery rates, fuel costs, route optimization,
and warehouse utilization."""


def main() -> None:
    """Run the pipeline with a test company."""
    print(f"\n{'='*60}")
    print(f"Running pipeline for: {COMPANY_NAME}")
    print(f"{'='*60}\n")

    result = run_pipeline(
        company_description=COMPANY_DESCRIPTION,
        company_name=COMPANY_NAME,
        catalog=CATALOG,
        warehouse_id=WAREHOUSE_ID,
        databricks_host=DATABRICKS_HOST,
        databricks_token=DATABRICKS_TOKEN,
    )

    print(f"\n{'='*60}")
    print("RESULT:")
    print(json.dumps(result, indent=2))
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
