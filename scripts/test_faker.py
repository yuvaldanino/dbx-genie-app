#!/usr/bin/env python3
"""Quick test — LLM designs schema, Faker generates data. No Databricks calls."""

import json
import logging
import os
import sys

sys.path.insert(0, "src")

from genieapp.backend.pipeline.schema_designer import design_schema
from genieapp.backend.pipeline.data_generator import generate_all_tables

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

COMPANY = """NovaTech Logistics is a mid-size freight and logistics company operating across
North America and Europe. They manage a fleet of 2,000+ trucks and work with 500+ warehouses.
Their core data includes shipment tracking, warehouse inventory, fleet maintenance, driver performance,
and customer contracts. They care about on-time delivery rates, fuel costs, route optimization,
and warehouse utilization."""

print("=== Step 1: LLM Schema Design ===\n")
schema = design_schema(
    COMPANY,
    databricks_host="7474655921234161",
    databricks_token=os.environ.get("DATABRICKS_TOKEN", ""),
)
print(json.dumps(schema, indent=2))

print("\n=== Step 2: Faker Data Generation ===\n")
data = generate_all_tables(schema)

for table_name, rows in data.items():
    print(f"\n--- {table_name} ({len(rows)} rows) ---")
    print(f"Columns: {list(rows[0].keys())}")
    print("Sample rows:")
    for row in rows[:3]:
        print(f"  {row}")
