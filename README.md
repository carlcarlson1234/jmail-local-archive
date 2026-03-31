# Jmail Local Archive

A complete local-first archival and query platform for the public [Jmail](https://jmail.world) ecosystem — Jeffrey Epstein's emails, documents, photos, and more from government releases.

## What This Is

This project mirrors all official structured datasets from `data.jmail.world`, loads them into a local PostgreSQL database with full-text search, and exposes a local Next.js web app + API so you can query everything offline.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    localhost:3001                        │
│              Next.js App + API Routes                   │
├─────────────────────────────────────────────────────────┤
│                  Data Access Layer                      │
│          (Drizzle ORM + raw SQL queries)                │
├─────────────────────────────────────────────────────────┤
│                 PostgreSQL (local)                      │
│        Full-text search + pg_trgm indexes               │
├─────────────────────────────────────────────────────────┤
│               Raw File Storage                          │
│     data/raw/jmail/  +  data/raw-assets/               │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Node.js** 18+ and **pnpm**
- **Python** 3.10+ with pip
- **PostgreSQL** 16+ (local install or Docker)
- ~3 GB disk space for datasets

## Quick Start

```bash
# 1. Clone and install
cd C:\Users\13603\jmail-local-archive
pnpm install
pip install -r scripts/requirements.txt

# 2. Set up PostgreSQL
#    If using Docker:
docker compose up -d
#    If using local PostgreSQL, create database:
#    CREATE USER jmail WITH PASSWORD 'jmail_local' CREATEDB;
#    CREATE DATABASE jmail OWNER jmail;
#    Then enable extensions in the jmail database:
#    CREATE EXTENSION IF NOT EXISTS pg_trgm;
#    CREATE EXTENSION IF NOT EXISTS unaccent;

# 3. Mirror official datasets (~2GB)
python scripts/ingest/download_manifest_and_files.py

# 4. Verify downloads
python scripts/ingest/verify_raw_files.py

# 5. Load data into PostgreSQL
python scripts/ingest/load_structured_data.py

# 6. Build search indexes
python scripts/ingest/rebuild_search_indexes.py

# 7. Discover asset URLs
python scripts/assets/discover_assets.py

# 8. Start the app
pnpm dev
# Open http://localhost:3001
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make db-up` | Start Docker PostgreSQL |
| `make db-down` | Stop Docker PostgreSQL |
| `make download` | Mirror all official dataset files |
| `make verify-raw` | Verify mirrored files against checksums |
| `make inspect` | Inspect parquet schemas with DuckDB |
| `make ingest` | Load structured data into PostgreSQL |
| `make rebuild-indexes` | Build full-text and trigram indexes |
| `make discover-assets` | Catalog asset URLs from datasets |
| `make download-assets` | Download cataloged assets |
| `make dev` | Start Next.js dev server on port 3001 |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Database health check |
| `GET /api/stats` | Row counts and status |
| `GET /api/search?q=...&type=...` | Full-text search |
| `GET /api/emails/:id` | Email detail |
| `GET /api/documents/:id` | Document detail with fulltext |
| `GET /api/people/:id` | Person detail |
| `GET /api/photos/:id` | Photo detail |
| `GET /api/conversations/:slug` | Conversation with messages |
| `GET /api/messages/:id` | Single message |
| `GET /api/assets/:id` | Asset registry entry |
| `GET /api/entities/:type/:id/assets` | Assets for entity |

## Data Refresh

To refresh data from the upstream source:

```bash
python scripts/ingest/download_manifest_and_files.py  # re-downloads changed files
python scripts/ingest/load_structured_data.py          # re-loads all tables
python scripts/ingest/rebuild_search_indexes.py        # rebuilds indexes
python scripts/assets/discover_assets.py               # re-discovers assets
```

## Project Structure

```
├── apps/web/                → Next.js app + API routes
├── packages/db/             → Drizzle schema + data access layer
├── src/lib/storage/         → Storage abstraction (local → cloud later)
├── scripts/ingest/          → Download + ingestion pipeline (Python)
├── scripts/assets/          → Asset discovery + download (Python)
├── data/raw/jmail/          → Mirrored official dataset files
├── data/raw-assets/         → Downloaded binary assets
├── data/logs/               → Pipeline logs
├── docs/                    → Architecture and API docs
├── docker-compose.yml       → PostgreSQL container
└── .env                     → Configuration
```

## Hosting Later

See [docs/hosting-readiness.md](docs/hosting-readiness.md) for deployment guidance. The architecture cleanly separates storage, database, and API layers so you can swap local disk for S3/R2 and move PostgreSQL to a managed service.

## License

This project archives publicly released government records.
