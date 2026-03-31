#!/usr/bin/env python3
"""Verify downloaded assets against asset registry."""

import os
import hashlib
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jmail:jmail_local@localhost:5432/jmail")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=" * 60)
    print("Jmail Asset Verification")
    print("=" * 60)

    pg = psycopg2.connect(DATABASE_URL)
    cur = pg.cursor()

    cur.execute("SELECT id, asset_url, local_path, sha256, size_bytes, status FROM asset_registry WHERE status = 'downloaded'")
    assets = cur.fetchall()

    print(f"Assets to verify: {len(assets)}")

    verified = 0
    missing = 0
    corrupt = 0

    for asset_id, url, local_path, expected_sha256, expected_size, status in assets:
        if not local_path or not Path(local_path).exists():
            missing += 1
            cur.execute("UPDATE asset_registry SET status = 'missing' WHERE id = %s", (asset_id,))
            continue

        actual_size = Path(local_path).stat().st_size
        if expected_size and actual_size != expected_size:
            corrupt += 1
            continue

        if expected_sha256:
            actual_hash = sha256_file(Path(local_path))
            if actual_hash != expected_sha256:
                corrupt += 1
                continue

        verified += 1

    pg.commit()

    # Overall summary
    cur.execute("SELECT status, count(*)::int FROM asset_registry GROUP BY status ORDER BY count(*) DESC")
    status_counts = cur.fetchall()

    print(f"\nVerified:  {verified}")
    print(f"Missing:   {missing}")
    print(f"Corrupt:   {corrupt}")
    print(f"\nOverall status:")
    for status, count in status_counts:
        print(f"  {status}: {count:,}")

    cur.close()
    pg.close()


if __name__ == "__main__":
    main()
