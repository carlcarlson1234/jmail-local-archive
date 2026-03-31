#!/usr/bin/env python3
"""Verify all mirrored raw files against manifest checksums."""

import os
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DATA_ROOT = Path(os.getenv("RAW_DATA_ROOT", "./data/raw/jmail"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest_path = RAW_DATA_ROOT / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: manifest.json not found. Run download_manifest_and_files.py first.")
        return

    with open(manifest_path) as f:
        manifest = json.load(f)

    base_url = manifest.get("base_url", "https://data.jmail.world/v1")
    datasets = manifest.get("datasets", {})

    print("Verifying mirrored files...")
    print("=" * 60)

    total = 0
    verified = 0
    missing = 0
    size_mismatch = 0
    hash_mismatch = 0

    for dataset_name, dataset_info in datasets.items():
        formats = dataset_info.get("formats", {})
        for fmt, file_info in formats.items():
            total += 1
            url = file_info.get("url", "")
            expected_size = file_info.get("size_bytes", 0)
            expected_sha256 = file_info.get("sha256", "")

            url_path = url.replace(base_url + "/", "")
            local_path = RAW_DATA_ROOT / url_path

            if not local_path.exists():
                print(f"  ✗ MISSING: {url_path}")
                missing += 1
                continue

            actual_size = local_path.stat().st_size
            if expected_size and actual_size != expected_size:
                print(f"  ✗ SIZE MISMATCH: {url_path} (expected {expected_size}, got {actual_size})")
                size_mismatch += 1
                continue

            if expected_sha256:
                actual_hash = sha256_file(local_path)
                if actual_hash != expected_sha256:
                    print(f"  ✗ HASH MISMATCH: {url_path}")
                    hash_mismatch += 1
                    continue

            print(f"  ✓ {url_path} ({actual_size / (1024*1024):.1f} MB)")
            verified += 1

    print("\n" + "=" * 60)
    print(f"Total:          {total}")
    print(f"Verified:       {verified}")
    print(f"Missing:        {missing}")
    print(f"Size mismatch:  {size_mismatch}")
    print(f"Hash mismatch:  {hash_mismatch}")

    if missing + size_mismatch + hash_mismatch > 0:
        print("\n⚠ Some files need attention. Re-run the download script.")
    else:
        print("\n✓ All files verified successfully!")


if __name__ == "__main__":
    main()
