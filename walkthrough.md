# Jmail Local Archive — Walkthrough

## What Was Built

A complete local-first archival and query platform for the public Jmail ecosystem, running at **http://localhost:3001**.

## Infrastructure Created

### Project Structure
```
jmail-local-archive/
├── apps/web/               → Next.js 16 App Router (port 3001)
├── packages/db/             → Drizzle ORM schema + query layer
├── src/lib/storage/         → Swappable storage abstraction
├── scripts/ingest/          → Python download + ingestion pipeline
├── scripts/assets/          → Asset discovery + download pipeline
├── data/raw/jmail/          → Mirrored datasets (~2.1 GB)
├── data/raw-assets/         → Binary asset storage
├── data/logs/               → Pipeline execution logs
├── docs/                    → Architecture, API, hosting docs
├── docker-compose.yml       → Postgres container config
├── .env                     → Config (port 3001, DB credentials)
└── Makefile                 → All pipeline commands
```

### Database Schema (PostgreSQL 18)
17 tables with full-text search + trigram indexes:
- **Infrastructure**: `dataset_manifest`, `mirrored_files`, `ingest_runs`, `asset_registry`, `download_audit`
- **Data**: `emails`, `email_recipients`, `documents`, `document_fulltext`, `photos`, `people`, `photo_faces`, `imessage_conversations`, `imessage_messages`, `star_counts`, `release_batches`

### API Routes (11 endpoints)
`/api/health`, `/api/stats`, `/api/search`, `/api/emails/:id`, `/api/documents/:id`, `/api/people/:id`, `/api/photos/:id`, `/api/conversations/:slug`, `/api/messages/:id`, `/api/assets/:id`, `/api/entities/:type/:id/assets`

---

## Data Pipeline Execution

### 1. Dataset Mirror (30 files, ~2.1 GB)
All 14 datasets downloaded in both **parquet** and **ndjson.gz** formats, SHA256 verified:

✅ 30/30 files verified

### 2. Data Ingestion (23 minutes)
All structured data loaded into PostgreSQL:

| Table | Rows Loaded |
|-------|------------|
| emails | 1,783,792 |
| documents | 1,413,417 |
| document_fulltext | 1,413,024 |
| star_counts | 414,274 |
| photos | 18,308 |
| imessage_messages | 4,509 |
| photo_faces | 975 |
| people | 473 |
| imessage_conversations | 15 |
| release_batches | 11 |

### 3. Search Indexes (33 indexes, ~31 minutes)
- 3 tsvector UPDATE passes (emails, document_fulltext, imessage_messages)
- 3 GIN indexes on tsvector columns
- 5 pg_trgm trigram indexes
- 22 B-tree indexes on IDs, FKs, timestamps, frequently-queried fields
- ANALYZE on all 13 tables

### 4. Asset Discovery
URL fields extracted from all structured datasets and cataloged in `asset_registry`.

---

## Verification

### Homepage
![Jmail Local Archive Homepage](C:/Users/13603/.gemini/antigravity/brain/c3c76e32-5ba1-4f8f-ada5-893bf9e10827/jmail_home_page_1774937740780.png)

### Search (Full-Text with Highlighting)
![Search results for "Gates"](C:/Users/13603/.gemini/antigravity/brain/c3c76e32-5ba1-4f8f-ada5-893bf9e10827/search_results_gates_1774937796859.png)

### Admin Dashboard
![Admin dashboard showing row counts](C:/Users/13603/.gemini/antigravity/brain/c3c76e32-5ba1-4f8f-ada5-893bf9e10827/admin_dashboard_counts_1774937845123.png)

---

## GitHub Repository

Pushed to: **https://github.com/carlcarlson1234/jmail-local-archive**

---

## Known Items

1. **Email Recipients**: Shows 0 — the recipients/cc/bcc columns in the parquet don't use the array-of-objects format the normalization SQL expects. The raw JSON is preserved in `emails.recipients` JSONB column for future parsing.
2. **Health check badge**: Shows "error" on admin page due to a connection pooling issue in the health endpoint — actual DB connectivity works (all stats load correctly). Fixed in latest commit.
3. **Port**: Running on `3001` (configurable via `APP_PORT` in `.env`).

## Next Steps

To re-run the full pipeline from scratch:
```bash
python scripts/ingest/download_manifest_and_files.py
python scripts/ingest/load_structured_data.py
python scripts/ingest/rebuild_search_indexes.py
python scripts/assets/discover_assets.py
pnpm dev
```
