#!/usr/bin/env python3
"""Download discovered assets from the asset registry with rate limiting."""

import os
import sys
import time
import hashlib
import requests
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jmail:jmail_local@localhost:5432/jmail")
RAW_ASSETS_ROOT = Path(os.getenv("RAW_ASSETS_ROOT", "./data/raw-assets"))
RATE_LIMIT_MS = int(os.getenv("ASSET_RATE_LIMIT_MS", "1000"))
MAX_RETRIES = int(os.getenv("ASSET_MAX_RETRIES", "3"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def url_to_local_path(url: str, entity_type: str) -> Path:
    """Convert a URL to a local file path organized by entity type."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        path = hashlib.md5(url.encode()).hexdigest()
    return RAW_ASSETS_ROOT / (entity_type or "unknown") / path


def download_asset(url: str, dest: Path, max_retries: int = MAX_RETRIES) -> dict:
    """Download a single asset with retries."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(max_retries):
        try:
            start = time.time()
            response = requests.get(url, stream=True, timeout=60,
                                     headers={"User-Agent": "JmailLocalArchive/1.0"})
            duration_ms = int((time.time() - start) * 1000)

            if response.status_code != 200:
                return {
                    "http_status": response.status_code,
                    "error": f"HTTP {response.status_code}",
                    "duration_ms": duration_ms,
                }

            content_type = response.headers.get("content-type", "")
            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            size = dest.stat().st_size
            checksum = sha256_file(dest)

            return {
                "http_status": 200,
                "content_type": content_type,
                "size_bytes": size,
                "sha256": checksum,
                "duration_ms": duration_ms,
                "local_path": str(dest),
            }

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": str(e), "http_status": None, "duration_ms": 0}

    return {"error": "Max retries exceeded", "http_status": None, "duration_ms": 0}


def main():
    print("=" * 60)
    print("Jmail Asset Download")
    print("=" * 60)

    pg = psycopg2.connect(DATABASE_URL)
    cur = pg.cursor()

    # Get pending assets
    cur.execute("""
        SELECT id, asset_url, source_entity_type, source_entity_id
        FROM asset_registry
        WHERE status = 'discovered'
        ORDER BY id
    """)
    pending = cur.fetchall()

    print(f"Pending downloads: {len(pending)}")
    if not pending:
        print("Nothing to download.")
        return

    downloaded = 0
    failed = 0
    unreachable = 0

    for i, (asset_id, url, entity_type, entity_id) in enumerate(pending, 1):
        sys.stdout.write(f"\r[{i}/{len(pending)}] Downloading...")
        sys.stdout.flush()

        local_path = url_to_local_path(url, entity_type)
        result = download_asset(url, local_path)

        # Record attempt in audit trail
        cur.execute("""
            INSERT INTO download_audit (url, http_status, content_type, size_bytes, duration_ms, error)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (url, result.get("http_status"), result.get("content_type"),
              result.get("size_bytes"), result.get("duration_ms"), result.get("error")))

        if result.get("http_status") == 200:
            cur.execute("""
                UPDATE asset_registry SET
                    status = 'downloaded',
                    local_path = %s,
                    content_type = %s,
                    size_bytes = %s,
                    sha256 = %s,
                    http_status = %s,
                    downloaded_at = NOW()
                WHERE id = %s
            """, (result["local_path"], result["content_type"],
                  result["size_bytes"], result["sha256"], 200, asset_id))
            downloaded += 1
        elif result.get("http_status") in (404, 403, 410):
            cur.execute("""
                UPDATE asset_registry SET status = 'unreachable', http_status = %s WHERE id = %s
            """, (result["http_status"], asset_id))
            unreachable += 1
        else:
            cur.execute("""
                UPDATE asset_registry SET status = 'failed', http_status = %s WHERE id = %s
            """, (result.get("http_status"), asset_id))
            failed += 1

        pg.commit()

        # Rate limit
        time.sleep(RATE_LIMIT_MS / 1000.0)

    print(f"\n\n{'=' * 60}")
    print("DOWNLOAD SUMMARY")
    print(f"{'=' * 60}")
    print(f"Downloaded:   {downloaded}")
    print(f"Unreachable:  {unreachable}")
    print(f"Failed:       {failed}")

    cur.close()
    pg.close()


if __name__ == "__main__":
    main()
