#!/usr/bin/env python3
"""Download manifest.json and all referenced dataset files from Jmail data API."""

import os
import sys
import json
import hashlib
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("JMAIL_DATA_BASE_URL", "https://data.jmail.world/v1")
RAW_DATA_ROOT = Path(os.getenv("RAW_DATA_ROOT", "./data/raw/jmail"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path, expected_size: int = None, expected_sha256: str = None) -> dict:
    """Download a file with resume support and verification."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded and valid
    if dest.exists():
        actual_size = dest.stat().st_size
        if expected_size and actual_size == expected_size:
            if expected_sha256:
                actual_hash = sha256_file(dest)
                if actual_hash == expected_sha256:
                    print(f"  ✓ Already exists and verified: {dest.name}")
                    return {"status": "verified", "size": actual_size, "sha256": actual_hash}
                else:
                    print(f"  ✗ Hash mismatch for {dest.name}, re-downloading...")
            else:
                print(f"  ✓ Already exists (size match): {dest.name}")
                return {"status": "downloaded", "size": actual_size}

    print(f"  ↓ Downloading: {url}")
    start = time.time()

    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                pct = (downloaded / total_size) * 100
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                sys.stdout.write(f"\r    {mb_done:.1f}/{mb_total:.1f} MB ({pct:.1f}%)")
                sys.stdout.flush()

    elapsed = time.time() - start
    actual_size = dest.stat().st_size
    speed = actual_size / elapsed / (1024 * 1024) if elapsed > 0 else 0
    print(f"\r    Downloaded {actual_size / (1024*1024):.1f} MB in {elapsed:.1f}s ({speed:.1f} MB/s)")

    result = {"status": "downloaded", "size": actual_size, "duration_s": round(elapsed, 2)}

    if expected_sha256:
        actual_hash = sha256_file(dest)
        if actual_hash == expected_sha256:
            result["status"] = "verified"
            result["sha256"] = actual_hash
            print(f"    ✓ SHA256 verified")
        else:
            result["status"] = "hash_mismatch"
            result["sha256"] = actual_hash
            print(f"    ✗ SHA256 MISMATCH! Expected: {expected_sha256[:16]}... Got: {actual_hash[:16]}...")

    return result


def main():
    print("=" * 60)
    print("Jmail Dataset Mirror")
    print("=" * 60)
    print(f"Source:      {BASE_URL}")
    print(f"Destination: {RAW_DATA_ROOT.resolve()}")
    print()

    # Step 1: Download manifest
    manifest_url = f"{BASE_URL}/manifest.json"
    manifest_path = RAW_DATA_ROOT / "manifest.json"
    print("[1/3] Downloading manifest.json...")
    download_file(manifest_url, manifest_path)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"\nManifest version: {manifest.get('version')}")
    print(f"Run ID: {manifest.get('run_id')}")
    print(f"Generated: {manifest.get('generated_at')}")
    print(f"Datasets: {len(manifest.get('datasets', {}))}")

    # Step 2: Build download list
    datasets = manifest.get("datasets", {})
    downloads = []

    for dataset_name, dataset_info in datasets.items():
        formats = dataset_info.get("formats", {})
        record_count = dataset_info.get("record_count", "?")

        for fmt, file_info in formats.items():
            url = file_info.get("url", "")
            size = file_info.get("size_bytes", 0)
            sha256 = file_info.get("sha256", "")

            # Determine local path preserving structure
            url_path = url.replace(BASE_URL + "/", "")
            local_path = RAW_DATA_ROOT / url_path

            downloads.append({
                "dataset": dataset_name,
                "format": fmt,
                "url": url,
                "local_path": local_path,
                "size": size,
                "sha256": sha256,
                "records": record_count,
            })

    total_size = sum(d["size"] for d in downloads)
    print(f"\n[2/3] Files to mirror: {len(downloads)}")
    print(f"Total size: {total_size / (1024*1024*1024):.2f} GB")
    print()

    # Step 3: Download all files
    results = []
    for i, dl in enumerate(downloads, 1):
        print(f"[{i}/{len(downloads)}] {dl['dataset']} ({dl['format']}) - {dl['records']} records, {dl['size']/(1024*1024):.1f} MB")
        result = download_file(dl["url"], dl["local_path"], dl["size"], dl["sha256"])
        result["dataset"] = dl["dataset"]
        result["format"] = dl["format"]
        result["local_path"] = str(dl["local_path"])
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("MIRROR SUMMARY")
    print("=" * 60)

    verified = sum(1 for r in results if r["status"] == "verified")
    downloaded = sum(1 for r in results if r["status"] == "downloaded")
    failed = sum(1 for r in results if r["status"] not in ("verified", "downloaded"))

    print(f"Verified:   {verified}")
    print(f"Downloaded: {downloaded}")
    print(f"Failed:     {failed}")

    if failed > 0:
        print("\nFailed files:")
        for r in results:
            if r["status"] not in ("verified", "downloaded"):
                print(f"  - {r['dataset']} ({r['format']}): {r['status']}")

    # Save results log
    log_path = Path(os.getenv("LOGS_ROOT", "./data/logs")) / "mirror_results.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nLog saved to: {log_path}")


if __name__ == "__main__":
    main()
