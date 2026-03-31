#!/usr/bin/env python3
"""Inspect parquet schemas using DuckDB. Outputs column info and sample rows."""

import os
import json
import duckdb
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DATA_ROOT = Path(os.getenv("RAW_DATA_ROOT", "./data/raw/jmail"))
LOGS_ROOT = Path(os.getenv("LOGS_ROOT", "./data/logs"))


def main():
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = LOGS_ROOT / "schema_inspection.json"

    parquet_files = sorted(RAW_DATA_ROOT.rglob("*.parquet"))

    if not parquet_files:
        print("No parquet files found. Run download_manifest_and_files.py first.")
        return

    print(f"Found {len(parquet_files)} parquet files")
    print("=" * 60)

    schemas = {}

    con = duckdb.connect()

    for pf in parquet_files:
        rel_path = str(pf.relative_to(RAW_DATA_ROOT))
        print(f"\n--- {rel_path} ---")

        try:
            # Get schema
            result = con.execute(f"DESCRIBE SELECT * FROM '{pf}'").fetchall()
            columns = [{"name": row[0], "type": row[1]} for row in result]

            # Get row count
            count = con.execute(f"SELECT count(*) FROM '{pf}'").fetchone()[0]

            # Get sample rows
            sample = con.execute(f"SELECT * FROM '{pf}' LIMIT 3").fetchall()
            col_names = [c["name"] for c in columns]
            sample_dicts = []
            for row in sample:
                d = {}
                for i, val in enumerate(row):
                    d[col_names[i]] = str(val) if val is not None else None
                sample_dicts.append(d)

            print(f"  Rows: {count:,}")
            print(f"  Columns: {len(columns)}")
            for col in columns:
                print(f"    - {col['name']}: {col['type']}")

            schemas[rel_path] = {
                "row_count": count,
                "columns": columns,
                "sample": sample_dicts,
            }

        except Exception as e:
            print(f"  ERROR: {e}")
            schemas[rel_path] = {"error": str(e)}

    con.close()

    with open(output_path, "w") as f:
        json.dump(schemas, f, indent=2, default=str)

    print(f"\n\nSchema inspection saved to: {output_path}")


if __name__ == "__main__":
    main()
