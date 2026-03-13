"""Faker-based data generator — takes an LLM-designed schema and produces DataFrames."""

from __future__ import annotations

import logging
from typing import Any

from faker import Faker

logger = logging.getLogger(__name__)

fake = Faker()
Faker.seed(42)


# SQL type mapping for each Faker provider
PROVIDER_SQL_TYPES: dict[str, str] = {
    "sequential_id": "INT",
    "name": "STRING",
    "first_name": "STRING",
    "last_name": "STRING",
    "email": "STRING",
    "phone_number": "STRING",
    "job": "STRING",
    "company": "STRING",
    "catch_phrase": "STRING",
    "bs": "STRING",
    "address": "STRING",
    "city": "STRING",
    "state": "STRING",
    "country": "STRING",
    "zipcode": "STRING",
    "latitude": "DOUBLE",
    "longitude": "DOUBLE",
    "date_between": "DATE",
    "date_this_year": "DATE",
    "random_int": "INT",
    "pyfloat": "DOUBLE",
    "random_element": "STRING",
    "boolean": "BOOLEAN",
    "text": "STRING",
    "sentence": "STRING",
    "uuid4": "STRING",
    "url": "STRING",
    "currency_code": "STRING",
    "fk": "INT",
}


def _generate_value(
    provider: str,
    args: dict[str, Any],
    row_index: int,
    generated_tables: dict[str, list[dict]],
) -> Any:
    """Generate a single value for a column using the specified Faker provider.

    Args:
        provider: Faker provider name.
        args: Provider arguments.
        row_index: Current row index (0-based), used for sequential_id.
        generated_tables: Already-generated table data for FK lookups.

    Returns:
        Generated value.
    """
    if provider == "sequential_id":
        return row_index + 1

    if provider == "fk":
        ref = args.get("references", "")
        if "." in ref:
            ref_table, ref_col = ref.split(".", 1)
        else:
            ref_table, ref_col = ref, f"{ref}_id" if ref else "id"

        ref_data = generated_tables.get(ref_table, [])
        if ref_data:
            row = fake.random_element(ref_data)
            return row.get(ref_col, 1)
        return fake.random_int(min=1, max=100)

    if provider == "random_element":
        elements = args.get("elements", ["A", "B", "C"])
        return fake.random_element(elements)

    if provider == "random_int":
        return fake.random_int(
            min=args.get("min", 1),
            max=args.get("max", 100),
        )

    if provider == "pyfloat":
        return round(
            fake.pyfloat(
                min_value=args.get("min_value", 0),
                max_value=args.get("max_value", 1000),
                right_digits=args.get("right_digits", 2),
            ),
            args.get("right_digits", 2),
        )

    if provider == "date_between":
        return fake.date_between(
            start_date=args.get("start_date", "-2y"),
            end_date=args.get("end_date", "today"),
        )

    if provider == "boolean":
        return fake.boolean(
            chance_of_getting_true=args.get("chance_of_getting_true", 50),
        )

    if provider == "text":
        return fake.text(max_nb_chars=args.get("max_nb_chars", 200))

    # Direct Faker provider call (name, email, city, etc.)
    faker_fn = getattr(fake, provider, None)
    if faker_fn and callable(faker_fn):
        return faker_fn()

    logger.warning("Unknown provider '%s', falling back to sentence", provider)
    return fake.sentence()


def get_sql_type(provider: str) -> str:
    """Get the SQL type for a Faker provider.

    Args:
        provider: Faker provider name.

    Returns:
        SQL type string (INT, STRING, DOUBLE, DATE, BOOLEAN).
    """
    return PROVIDER_SQL_TYPES.get(provider, "STRING")


def generate_table_data(
    table_schema: dict[str, Any],
    generated_tables: dict[str, list[dict]],
) -> list[dict]:
    """Generate fake data for a single table.

    Args:
        table_schema: Table definition from the LLM schema.
        generated_tables: Already-generated tables for FK references.

    Returns:
        List of row dicts.
    """
    table_name = table_schema["name"]
    row_count = table_schema.get("row_count", 1000)
    columns = table_schema["columns"]

    logger.info("Generating %d rows for table '%s'...", row_count, table_name)

    rows: list[dict] = []
    for i in range(row_count):
        row = {}
        for col in columns:
            col_name = col["name"]
            provider = col["faker"]
            args = col.get("args", {})
            row[col_name] = _generate_value(provider, args, i, generated_tables)
        rows.append(row)

    logger.info("Generated %d rows for '%s'", len(rows), table_name)
    return rows


def generate_all_tables(
    schema: dict[str, Any],
) -> dict[str, list[dict]]:
    """Generate data for all tables in the schema, respecting FK ordering.

    Args:
        schema: Full schema dict with "tables" list.

    Returns:
        Dict mapping table_name → list of row dicts.
    """
    generated: dict[str, list[dict]] = {}

    for table_def in schema["tables"]:
        table_name = table_def["name"]
        rows = generate_table_data(table_def, generated)
        generated[table_name] = rows

    return generated
