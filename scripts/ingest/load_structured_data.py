#!/usr/bin/env python3
"""Load structured parquet data into PostgreSQL using DuckDB for reading."""

import os
import sys
import json
import time
import duckdb
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAW_DATA_ROOT = Path(os.getenv("RAW_DATA_ROOT", "./data/raw/jmail"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jmail:jmail_local@localhost:5432/jmail")
LOGS_ROOT = Path(os.getenv("LOGS_ROOT", "./data/logs"))
BATCH_SIZE = 5000

# ─── Schema Creation SQL ─────────────────────────────────────────────

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE IF NOT EXISTS dataset_manifest (
    id SERIAL PRIMARY KEY,
    run_id TEXT,
    generated_at TIMESTAMPTZ,
    raw_json JSONB,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mirrored_files (
    id SERIAL PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    format TEXT NOT NULL,
    url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    expected_size BIGINT,
    actual_size BIGINT,
    expected_sha256 TEXT,
    actual_sha256 TEXT,
    status TEXT DEFAULT 'pending',
    downloaded_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    UNIQUE(dataset_name, format)
);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',
    tables_loaded JSONB,
    row_counts JSONB,
    errors JSONB
);

CREATE TABLE IF NOT EXISTS asset_registry (
    id SERIAL PRIMARY KEY,
    asset_url TEXT NOT NULL UNIQUE,
    referring_url TEXT,
    source_dataset TEXT,
    source_entity_type TEXT,
    source_entity_id TEXT,
    local_path TEXT,
    content_type TEXT,
    size_bytes BIGINT,
    sha256 TEXT,
    http_status INT,
    status TEXT DEFAULT 'discovered',
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    downloaded_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS download_audit (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    http_status INT,
    content_type TEXT,
    size_bytes BIGINT,
    duration_ms INT,
    error TEXT,
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    doc_id TEXT,
    subject TEXT,
    sender TEXT,
    sender_name TEXT,
    recipients JSONB,
    cc JSONB,
    bcc JSONB,
    date TIMESTAMPTZ,
    body TEXT,
    body_html TEXT,
    thread_id TEXT,
    in_reply_to TEXT,
    labels JSONB,
    attachments JSONB,
    starred BOOLEAN,
    star_count INT,
    release_batch TEXT,
    source TEXT,
    raw_json JSONB,
    search_vector TSVECTOR,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_recipients (
    id SERIAL PRIMARY KEY,
    email_id TEXT NOT NULL,
    recipient_type TEXT NOT NULL,
    email TEXT,
    name TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    doc_id TEXT,
    title TEXT,
    filename TEXT,
    file_type TEXT,
    page_count INT,
    volume TEXT,
    bates_start TEXT,
    bates_end TEXT,
    release_batch TEXT,
    source TEXT,
    pdf_url TEXT,
    thumbnail_url TEXT,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_fulltext (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    shard_name TEXT,
    page_number INT,
    text TEXT,
    raw_json JSONB,
    search_vector TSVECTOR,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS photos (
    id TEXT PRIMARY KEY,
    filename TEXT,
    title TEXT,
    description TEXT,
    date_taken TIMESTAMPTZ,
    width INT,
    height INT,
    image_url TEXT,
    thumbnail_url TEXT,
    volume TEXT,
    release_batch TEXT,
    source TEXT,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY,
    name TEXT,
    slug TEXT,
    aliases JSONB,
    description TEXT,
    image_url TEXT,
    email_addresses JSONB,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS photo_faces (
    id SERIAL PRIMARY KEY,
    photo_id TEXT,
    person_id TEXT,
    confidence TEXT,
    bounding_box JSONB,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS imessage_conversations (
    id TEXT PRIMARY KEY,
    slug TEXT,
    title TEXT,
    participants JSONB,
    message_count INT,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS imessage_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    conversation_slug TEXT,
    sender TEXT,
    body TEXT,
    date TIMESTAMPTZ,
    attachments JSONB,
    raw_json JSONB,
    search_vector TSVECTOR,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS star_counts (
    id SERIAL PRIMARY KEY,
    entity_type TEXT,
    entity_id TEXT,
    count INT,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS release_batches (
    id TEXT PRIMARY KEY,
    name TEXT,
    release_date TIMESTAMPTZ,
    description TEXT,
    source TEXT,
    document_count INT,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);
"""

# ─── Column Mapping ──────────────────────────────────────────────────
# Maps parquet column names to DB column names when they differ

def safe_json(val):
    """Convert value to JSON-safe format."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, default=str)
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return json.dumps(parsed, default=str)
        except (json.JSONDecodeError, TypeError):
            return json.dumps(val)
    return json.dumps(str(val))


def safe_str(val):
    if val is None:
        return None
    return str(val)


def safe_int(val):
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def safe_bool(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    return bool(val)


def safe_timestamp(val):
    if val is None:
        return None
    return str(val)


def load_parquet_to_table(con, cur, parquet_path, table_name, column_map, id_field="id"):
    """Load a parquet file into a Postgres table using DuckDB to read and psycopg2 to write."""
    print(f"\n  Loading {parquet_path.name} -> {table_name}")

    # Get column names from parquet
    parquet_cols = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").fetchall()]
    print(f"    Parquet columns: {parquet_cols}")

    # Determine which columns to load
    # Build a filtered list of (db_col, parquet_col, converter) tuples
    available_cols = []  # list of (db_col, parquet_col, converter)

    for db_col, (parquet_col, converter) in column_map.items():
        if parquet_col in parquet_cols or parquet_col == "__raw_json__":
            available_cols.append((db_col, parquet_col, converter))

    if not available_cols:
        print(f"    No matching columns found, skipping")
        return 0

    available_db_cols = [c[0] for c in available_cols]
    print(f"    Mapping {len(available_cols)} columns: {available_db_cols}")

    total_count = con.execute(f"SELECT count(*) FROM '{parquet_path}'").fetchone()[0]
    print(f"    Total rows: {total_count:,}")

    # Truncate existing data if rerunning
    cur.execute(f"DELETE FROM {table_name}")

    # Read and batch insert
    offset = 0
    loaded = 0

    while offset < total_count:
        batch_query = f"SELECT * FROM '{parquet_path}' LIMIT {BATCH_SIZE} OFFSET {offset}"
        rows = con.execute(batch_query).fetchall()
        all_col_names = [desc[0] for desc in con.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").fetchall()]

        if not rows:
            break

        values_list = []
        for row in rows:
            row_dict = dict(zip(all_col_names, row))
            values = []
            for db_col, parquet_col, converter in available_cols:
                if parquet_col == "__raw_json__":
                    values.append(json.dumps(row_dict, default=str))
                elif parquet_col in row_dict:
                    values.append(converter(row_dict[parquet_col]))
                else:
                    values.append(None)
            values_list.append(values)

        placeholders = ", ".join(["%s"] * len(available_cols))
        cols_str = ", ".join(available_db_cols)

        # Use ON CONFLICT for tables with primary keys
        if id_field and id_field in available_db_cols:
            insert_sql = f"""
                INSERT INTO {table_name} ({cols_str})
                VALUES ({placeholders})
                ON CONFLICT ({id_field}) DO NOTHING
            """
        else:
            insert_sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"

        psycopg2.extras.execute_batch(cur, insert_sql, values_list, page_size=1000)

        loaded += len(rows)
        offset += BATCH_SIZE
        sys.stdout.write(f"\r    Loaded {loaded:,}/{total_count:,}")
        sys.stdout.flush()

    print(f"\r    Loaded {loaded:,}/{total_count:,} rows [OK]")
    return loaded


def normalize_email_recipients(cur):
    """Extract recipients from emails JSON into email_recipients table."""
    print("\n  Normalizing email recipients...")
    cur.execute("DELETE FROM email_recipients")

    for rtype in ['recipients', 'cc', 'bcc']:
        sql = """
            INSERT INTO email_recipients (email_id, recipient_type, email, name)
            SELECT
                e.id,
                %s,
                CASE
                    WHEN jsonb_typeof(elem) = 'object' THEN elem->>'email'
                    WHEN jsonb_typeof(elem) = 'string' THEN trim('"' FROM elem::text)
                    ELSE NULL
                END,
                CASE
                    WHEN jsonb_typeof(elem) = 'object' THEN elem->>'name'
                    ELSE NULL
                END
            FROM emails e,
                 jsonb_array_elements(
                     CASE
                         WHEN e.""" + rtype + """ IS NOT NULL AND jsonb_typeof(e.""" + rtype + """) = 'array'
                         THEN e.""" + rtype + """
                         ELSE '[]'::jsonb
                     END
                 ) AS elem
        """
        cur.execute(sql, (rtype,))

    cur.execute("SELECT count(*) FROM email_recipients")
    count = cur.fetchone()[0]
    print(f"    Created {count:,} recipient rows [OK]")
    return count


def main():
    print("=" * 60)
    print("Jmail Data Ingestion")
    print("=" * 60)

    LOGS_ROOT.mkdir(parents=True, exist_ok=True)

    # Connect to Postgres
    print("\nConnecting to PostgreSQL...")
    pg = psycopg2.connect(DATABASE_URL)
    pg.autocommit = False
    cur = pg.cursor()

    # Create schema
    print("Creating tables...")
    cur.execute(SCHEMA_SQL)
    pg.commit()
    print("  [OK] Schema created")

    # Connect DuckDB for parquet reading
    duck = duckdb.connect()

    # Record ingest run
    cur.execute("INSERT INTO ingest_runs (status) VALUES ('running') RETURNING id")
    run_id = cur.fetchone()[0]
    pg.commit()

    start_time = time.time()
    row_counts = {}
    errors = {}
    tables_loaded = []

    # ─── Load each dataset ────────────────────────────────────────

    try:
        # 1. Release Batches
        pf = RAW_DATA_ROOT / "release_batches.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "release_batches", {
                "id": ("id", safe_str),
                "name": ("name", safe_str),
                "release_date": ("release_date", safe_timestamp),
                "description": ("description", safe_str),
                "source": ("source", safe_str),
                "document_count": ("document_count", safe_int),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field="id")
            pg.commit()
            row_counts["release_batches"] = count
            tables_loaded.append("release_batches")

        # 2. People
        pf = RAW_DATA_ROOT / "people.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "people", {
                "id": ("id", safe_str),
                "name": ("name", safe_str),
                "slug": ("slug", safe_str),
                "aliases": ("aliases", safe_json),
                "description": ("description", safe_str),
                "image_url": ("image_url", safe_str),
                "email_addresses": ("email_addresses", safe_json),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field="id")
            pg.commit()
            row_counts["people"] = count
            tables_loaded.append("people")

        # 3. Photos
        pf = RAW_DATA_ROOT / "photos.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "photos", {
                "id": ("id", safe_str),
                "filename": ("filename", safe_str),
                "title": ("title", safe_str),
                "description": ("description", safe_str),
                "date_taken": ("date_taken", safe_timestamp),
                "width": ("width", safe_int),
                "height": ("height", safe_int),
                "image_url": ("image_url", safe_str),
                "thumbnail_url": ("thumbnail_url", safe_str),
                "volume": ("volume", safe_str),
                "release_batch": ("release_batch", safe_str),
                "source": ("source", safe_str),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field="id")
            pg.commit()
            row_counts["photos"] = count
            tables_loaded.append("photos")

        # 4. Photo Faces
        pf = RAW_DATA_ROOT / "photo_faces.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "photo_faces", {
                "photo_id": ("photo_id", safe_str),
                "person_id": ("person_id", safe_str),
                "confidence": ("confidence", safe_str),
                "bounding_box": ("bounding_box", safe_json),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field=None)
            pg.commit()
            row_counts["photo_faces"] = count
            tables_loaded.append("photo_faces")

        # 5. iMessage Conversations
        pf = RAW_DATA_ROOT / "imessage_conversations.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "imessage_conversations", {
                "id": ("id", safe_str),
                "slug": ("slug", safe_str),
                "title": ("title", safe_str),
                "participants": ("participants", safe_json),
                "message_count": ("message_count", safe_int),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field="id")
            pg.commit()
            row_counts["imessage_conversations"] = count
            tables_loaded.append("imessage_conversations")

        # 6. iMessage Messages
        pf = RAW_DATA_ROOT / "imessage_messages.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "imessage_messages", {
                "id": ("id", safe_str),
                "conversation_id": ("conversation_id", safe_str),
                "conversation_slug": ("conversation_slug", safe_str),
                "sender": ("sender", safe_str),
                "body": ("body", safe_str),
                "date": ("date", safe_timestamp),
                "attachments": ("attachments", safe_json),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field="id")
            pg.commit()
            row_counts["imessage_messages"] = count
            tables_loaded.append("imessage_messages")

        # 7. Star Counts
        pf = RAW_DATA_ROOT / "star_counts.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "star_counts", {
                "entity_type": ("entity_type", safe_str),
                "entity_id": ("entity_id", safe_str),
                "count": ("count", safe_int),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field=None)
            pg.commit()
            row_counts["star_counts"] = count
            tables_loaded.append("star_counts")

        # 8. Documents (metadata only, not full text)
        pf = RAW_DATA_ROOT / "documents.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "documents", {
                "id": ("id", safe_str),
                "doc_id": ("doc_id", safe_str),
                "title": ("title", safe_str),
                "filename": ("filename", safe_str),
                "file_type": ("file_type", safe_str),
                "page_count": ("page_count", safe_int),
                "volume": ("volume", safe_str),
                "bates_start": ("bates_start", safe_str),
                "bates_end": ("bates_end", safe_str),
                "release_batch": ("release_batch", safe_str),
                "source": ("source", safe_str),
                "pdf_url": ("pdf_url", safe_str),
                "thumbnail_url": ("thumbnail_url", safe_str),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field="id")
            pg.commit()
            row_counts["documents"] = count
            tables_loaded.append("documents")

        # 9. Document Full-text shards
        fulltext_shards = sorted((RAW_DATA_ROOT / "documents-full").glob("*.parquet")) if (RAW_DATA_ROOT / "documents-full").exists() else []
        if fulltext_shards:
            cur.execute("DELETE FROM document_fulltext")
            pg.commit()
            total_ft = 0
            for shard in fulltext_shards:
                shard_name = shard.stem
                print(f"\n  Loading document fulltext shard: {shard_name}")

                # Read schema to find text column
                shard_cols = [row[0] for row in duck.execute(f"DESCRIBE SELECT * FROM '{shard}'").fetchall()]
                print(f"    Columns: {shard_cols}")

                row_count = duck.execute(f"SELECT count(*) FROM '{shard}'").fetchone()[0]
                print(f"    Rows: {row_count:,}")

                offset = 0
                shard_loaded = 0
                while offset < row_count:
                    rows = duck.execute(f"SELECT * FROM '{shard}' LIMIT {BATCH_SIZE} OFFSET {offset}").fetchall()
                    if not rows:
                        break

                    values_list = []
                    for row in rows:
                        row_dict = dict(zip(shard_cols, row))
                        doc_id = safe_str(row_dict.get("id") or row_dict.get("doc_id") or row_dict.get("document_id"))
                        text_val = safe_str(row_dict.get("text") or row_dict.get("content") or row_dict.get("body") or row_dict.get("full_text") or row_dict.get("extracted_text"))
                        page_num = safe_int(row_dict.get("page_number") or row_dict.get("page"))
                        raw = json.dumps(row_dict, default=str)
                        values_list.append((doc_id, shard_name, page_num, text_val, raw))

                    psycopg2.extras.execute_batch(
                        cur,
                        "INSERT INTO document_fulltext (doc_id, shard_name, page_number, text, raw_json) VALUES (%s, %s, %s, %s, %s)",
                        values_list,
                        page_size=1000
                    )

                    shard_loaded += len(rows)
                    offset += BATCH_SIZE
                    sys.stdout.write(f"\r    Loaded {shard_loaded:,}/{row_count:,}")
                    sys.stdout.flush()

                pg.commit()
                total_ft += shard_loaded
                print(f"\r    Loaded {shard_loaded:,} rows from {shard_name} [OK]")

            row_counts["document_fulltext"] = total_ft
            tables_loaded.append("document_fulltext")

        # 10. Emails (full - largest dataset)
        pf = RAW_DATA_ROOT / "emails.parquet"
        if pf.exists():
            count = load_parquet_to_table(duck, cur, pf, "emails", {
                "id": ("id", safe_str),
                "doc_id": ("doc_id", safe_str),
                "subject": ("subject", safe_str),
                "sender": ("sender", safe_str),
                "sender_name": ("sender_name", safe_str),
                "recipients": ("recipients", safe_json),
                "cc": ("cc", safe_json),
                "bcc": ("bcc", safe_json),
                "date": ("date", safe_timestamp),
                "body": ("body", safe_str),
                "body_html": ("body_html", safe_str),
                "thread_id": ("thread_id", safe_str),
                "in_reply_to": ("in_reply_to", safe_str),
                "labels": ("labels", safe_json),
                "attachments": ("attachments", safe_json),
                "starred": ("starred", safe_bool),
                "star_count": ("star_count", safe_int),
                "release_batch": ("release_batch", safe_str),
                "source": ("source", safe_str),
                "raw_json": ("__raw_json__", safe_json),
            }, id_field="id")
            pg.commit()
            row_counts["emails"] = count
            tables_loaded.append("emails")

            # Normalize recipients
            recipient_count = normalize_email_recipients(cur)
            pg.commit()
            row_counts["email_recipients"] = recipient_count
            tables_loaded.append("email_recipients")

        # Record manifest in DB
        manifest_path = RAW_DATA_ROOT / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
            cur.execute(
                "INSERT INTO dataset_manifest (run_id, generated_at, raw_json) VALUES (%s, %s, %s)",
                (manifest.get("run_id"), manifest.get("generated_at"), json.dumps(manifest))
            )

            # Record mirrored files
            base_url = manifest.get("base_url", "")
            for ds_name, ds_info in manifest.get("datasets", {}).items():
                for fmt, file_info in ds_info.get("formats", {}).items():
                    url = file_info.get("url", "")
                    url_path = url.replace(base_url + "/", "")
                    local_path = str(RAW_DATA_ROOT / url_path)
                    cur.execute("""
                        INSERT INTO mirrored_files (dataset_name, format, url, local_path, expected_size, expected_sha256, status, downloaded_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 'downloaded', NOW())
                        ON CONFLICT (dataset_name, format) DO UPDATE SET
                            status = 'downloaded', downloaded_at = NOW()
                    """, (ds_name, fmt, url, local_path, file_info.get("size_bytes"), file_info.get("sha256")))
            pg.commit()

        # Update ingest run
        elapsed = time.time() - start_time
        cur.execute("""
            UPDATE ingest_runs SET
                completed_at = NOW(),
                status = 'completed',
                tables_loaded = %s,
                row_counts = %s
            WHERE id = %s
        """, (json.dumps(tables_loaded), json.dumps(row_counts), run_id))
        pg.commit()

    except Exception as e:
        pg.rollback()
        errors["fatal"] = str(e)
        cur.execute("""
            UPDATE ingest_runs SET
                completed_at = NOW(),
                status = 'failed',
                errors = %s
            WHERE id = %s
        """, (json.dumps(errors), run_id))
        pg.commit()
        print(f"\n\n  [FAIL] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        duck.close()
        cur.close()
        pg.close()

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Duration: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"Tables loaded: {len(tables_loaded)}")
    for table, count in row_counts.items():
        print(f"  {table}: {count:,}")

    log_path = LOGS_ROOT / "ingest_results.json"
    with open(log_path, "w") as f:
        json.dump({"row_counts": row_counts, "tables_loaded": tables_loaded, "duration_s": round(elapsed, 2)}, f, indent=2)
    print(f"\nLog saved to: {log_path}")


if __name__ == "__main__":
    main()
