# Ingestion Summary

This document is generated during the ingestion process and will be updated with actual counts.

## Official Structured Files

Source: `https://data.jmail.world/v1/manifest.json`

| Dataset | Format | Records | Size |
|---------|--------|---------|------|
| emails | parquet | 1,783,792 | 319 MB |
| emails | ndjson.gz | 1,783,792 | 432 MB |
| emails-slim | parquet | 1,783,792 | 39 MB |
| emails-slim | ndjson.gz | 1,783,792 | 53 MB |
| documents | parquet | 1,413,417 | 24 MB |
| documents | ndjson.gz | 1,413,417 | 35 MB |
| documents-full/VOL00008 | parquet | 31,999 | 24 MB |
| documents-full/VOL00008 | ndjson.gz | 31,999 | 29 MB |
| documents-full/VOL00009 | parquet | 531,253 | 235 MB |
| documents-full/VOL00009 | ndjson.gz | 531,253 | 285 MB |
| documents-full/VOL00010 | parquet | 502,989 | 155 MB |
| documents-full/VOL00010 | ndjson.gz | 502,989 | 216 MB |
| documents-full/DataSet11 | parquet | 331,603 | 90 MB |
| documents-full/DataSet11 | ndjson.gz | 331,603 | 122 MB |
| documents-full/other | parquet | 15,180 | 7.5 MB |
| documents-full/other | ndjson.gz | 15,180 | 9.8 MB |
| photos | parquet | 18,308 | 1.1 MB |
| photos | ndjson.gz | 18,308 | 17 MB |
| people | parquet | 473 | 10 KB |
| people | ndjson.gz | 473 | 8 KB |
| photo_faces | parquet | 975 | 58 KB |
| photo_faces | ndjson.gz | 975 | 50 KB |
| star_counts | parquet | 414,274 | 2 MB |
| star_counts | ndjson.gz | 414,274 | 2.2 MB |
| release_batches | parquet | 11 | 1.3 KB |
| release_batches | ndjson.gz | 11 | 541 B |
| imessage_conversations | parquet | 15 | 3.7 KB |
| imessage_conversations | ndjson.gz | 15 | 1.8 KB |
| imessage_messages | parquet | 4,509 | 168 KB |
| imessage_messages | ndjson.gz | 4,509 | 211 KB |
| manifest.json | json | - | ~8 KB |

**Total: ~2.1 GB (Parquet + NDJSON.GZ)**

## Asset Discovery

Asset URLs are extracted from:
- Photo records (`image_url`, `thumbnail_url`)
- Document records (`pdf_url`, `thumbnail_url`)
- Email attachments (from JSON `attachments` field)
- iMessage attachments

Assets are **cataloged**, not automatically downloaded. Run `python scripts/assets/download_assets.py` to download.

## Caveats

1. **emails-slim** is downloaded but not loaded into DB (full `emails` is loaded instead)
2. **Document fulltext** from 5 shard files is merged into one `document_fulltext` table
3. **Email recipients** are normalized from JSON into `email_recipients` table
4. The schema dynamically adapts to whatever columns exist in the parquet files
5. Asset download is a separate optional step with rate limiting
