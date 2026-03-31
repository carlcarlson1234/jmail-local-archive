#!/usr/bin/env python3
"""Discover asset URLs from structured datasets and catalog them in the database."""

import os
import json
import duckdb
import psycopg2
import psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DATA_ROOT = Path(os.getenv("RAW_DATA_ROOT", "./data/raw/jmail"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jmail:jmail_local@localhost:5432/jmail")
JMAIL_SITE_URL = os.getenv("JMAIL_SITE_URL", "https://jmail.world")

# URL fields to look for in each dataset
URL_FIELDS = [
    "image_url", "thumbnail_url", "pdf_url", "attachment_url",
    "url", "file_url", "download_url", "media_url",
    "photo_url", "avatar_url", "icon_url",
]


def discover_from_parquet(duck, parquet_path, dataset_name, entity_type):
    """Extract URL fields from a parquet file."""
    if not parquet_path.exists():
        return []

    cols = [row[0] for row in duck.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").fetchall()]
    url_cols = [c for c in cols if c in URL_FIELDS or c.endswith("_url")]

    if not url_cols:
        print(f"  No URL columns found in {parquet_path.name}")
        return []

    id_col = "id" if "id" in cols else ("doc_id" if "doc_id" in cols else None)

    print(f"  Found URL columns in {parquet_path.name}: {url_cols}")

    assets = []
    select = ", ".join([id_col] + url_cols) if id_col else ", ".join(url_cols)
    rows = duck.execute(f"SELECT {select} FROM '{parquet_path}'").fetchall()

    for row in rows:
        idx = 0
        entity_id = str(row[idx]) if id_col else None
        if id_col:
            idx = 1

        for i, col in enumerate(url_cols):
            url = row[idx + i]
            if url and isinstance(url, str) and url.startswith("http"):
                assets.append({
                    "asset_url": url,
                    "source_dataset": dataset_name,
                    "source_entity_type": entity_type,
                    "source_entity_id": entity_id,
                })

    return assets


def discover_from_json_fields(pg_cur):
    """Discover asset URLs from JSON fields in already-loaded data (attachments, etc)."""
    assets = []

    # Email attachments
    print("  Scanning email attachments...")
    pg_cur.execute("""
        SELECT e.id, elem->>'url' as url, elem->>'filename' as filename
        FROM emails e,
             jsonb_array_elements(
                 CASE WHEN e.attachments IS NOT NULL AND jsonb_typeof(e.attachments) = 'array'
                      THEN e.attachments ELSE '[]'::jsonb END
             ) AS elem
        WHERE elem->>'url' IS NOT NULL AND elem->>'url' LIKE 'http%'
    """)
    for row in pg_cur.fetchall():
        assets.append({
            "asset_url": row[1],
            "source_dataset": "emails",
            "source_entity_type": "email_attachment",
            "source_entity_id": row[0],
        })

    # iMessage attachments
    print("  Scanning iMessage attachments...")
    pg_cur.execute("""
        SELECT m.id, elem->>'url' as url
        FROM imessage_messages m,
             jsonb_array_elements(
                 CASE WHEN m.attachments IS NOT NULL AND jsonb_typeof(m.attachments) = 'array'
                      THEN m.attachments ELSE '[]'::jsonb END
             ) AS elem
        WHERE elem->>'url' IS NOT NULL AND elem->>'url' LIKE 'http%'
    """)
    for row in pg_cur.fetchall():
        assets.append({
            "asset_url": row[1],
            "source_dataset": "imessage_messages",
            "source_entity_type": "message_attachment",
            "source_entity_id": row[0],
        })

    return assets


def main():
    print("=" * 60)
    print("Jmail Asset Discovery")
    print("=" * 60)

    duck = duckdb.connect()
    pg = psycopg2.connect(DATABASE_URL)
    cur = pg.cursor()

    all_assets = []

    # Discover from parquet files
    print("\n[1] Scanning parquet files for URL fields...")
    datasets = [
        ("photos.parquet", "photos", "photo"),
        ("documents.parquet", "documents", "document"),
        ("people.parquet", "people", "person"),
        ("emails-slim.parquet", "emails-slim", "email"),
    ]

    for filename, ds_name, entity_type in datasets:
        pf = RAW_DATA_ROOT / filename
        assets = discover_from_parquet(duck, pf, ds_name, entity_type)
        all_assets.extend(assets)
        print(f"    {filename}: {len(assets)} URLs found")

    # Discover from JSON fields in DB
    print("\n[2] Scanning JSON fields in database...")
    json_assets = discover_from_json_fields(cur)
    all_assets.extend(json_assets)
    print(f"    Found {len(json_assets)} URLs from JSON fields")

    # Deduplicate
    seen = set()
    unique_assets = []
    for asset in all_assets:
        if asset["asset_url"] not in seen:
            seen.add(asset["asset_url"])
            unique_assets.append(asset)

    print(f"\n[3] Total unique asset URLs: {len(unique_assets)}")

    # Insert into asset_registry
    print("\n[4] Cataloging in database...")
    inserted = 0
    for asset in unique_assets:
        try:
            cur.execute("""
                INSERT INTO asset_registry (asset_url, source_dataset, source_entity_type, source_entity_id, status)
                VALUES (%s, %s, %s, %s, 'discovered')
                ON CONFLICT (asset_url) DO NOTHING
            """, (asset["asset_url"], asset["source_dataset"], asset["source_entity_type"], asset["source_entity_id"]))
            inserted += 1
        except Exception as e:
            pass

    pg.commit()

    # Summary
    cur.execute("SELECT source_entity_type, count(*) FROM asset_registry GROUP BY source_entity_type ORDER BY count(*) DESC")
    type_counts = cur.fetchall()

    cur.execute("SELECT status, count(*) FROM asset_registry GROUP BY status")
    status_counts = cur.fetchall()

    print(f"\n  Inserted {inserted} new asset records")
    print("\n  Asset types:")
    for entity_type, count in type_counts:
        print(f"    {entity_type}: {count:,}")
    print("\n  Status:")
    for status, count in status_counts:
        print(f"    {status}: {count:,}")

    duck.close()
    cur.close()
    pg.close()

    print("\n✓ Asset discovery complete!")


if __name__ == "__main__":
    main()
