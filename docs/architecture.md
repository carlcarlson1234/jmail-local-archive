# Architecture

## Design Principles

1. **Official structured files are the primary source of truth** — not the Jmail website UI
2. **Website asset harvesting is secondary** — opportunistic discovery of binary assets
3. **Local-first** — after setup, no internet required for querying
4. **Deployment-portable** — clean layer separation for future cloud hosting

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        UI Layer                               │
│   Next.js App Router (localhost:3001)                         │
│   • Search page with full-text + fuzzy matching               │
│   • Entity detail pages (emails, documents, people, etc)      │
│   • Admin/status dashboard                                    │
├──────────────────────────────────────────────────────────────┤
│                       API Layer                               │
│   Next.js API Routes (/api/*)                                │
│   • RESTful endpoints for all entities                        │
│   • Search with ranking, snippets, type filtering             │
│   • Health/stats monitoring                                   │
├──────────────────────────────────────────────────────────────┤
│                  Data Access Layer                            │
│   packages/db (Drizzle ORM + raw SQL)                        │
│   • searchAll(), getEmailById(), getDocumentById(), etc       │
│   • PostgreSQL full-text search (tsvector + GIN)              │
│   • pg_trgm fuzzy matching on names, subjects                 │
├──────────────────────────────────────────────────────────────┤
│                   Database Layer                              │
│   PostgreSQL 16+                                              │
│   • 17 tables (data + infrastructure)                         │
│   • Full-text search indexes (GIN on tsvector)                │
│   • Trigram indexes for fuzzy matching                         │
│   • B-tree indexes on IDs, FKs, timestamps                    │
├──────────────────────────────────────────────────────────────┤
│                 Raw Archival Layer                            │
│   Local filesystem (swappable to S3/R2/B2)                   │
│   • data/raw/jmail/ — official Parquet + NDJSON files         │
│   • data/raw-assets/ — downloaded binary assets               │
│   • Manifest-driven, checksum-verified                        │
└──────────────────────────────────────────────────────────────┘
```

## Schema Overview

### Infrastructure Tables
- **dataset_manifest** — cached manifest.json from upstream
- **mirrored_files** — tracks every mirrored file with checksums
- **ingest_runs** — pipeline execution history
- **asset_registry** — discovered asset URLs and download status
- **download_audit** — detailed log of every download attempt

### Structured Data Tables
- **emails** — 1.78M email records with full body text
- **email_recipients** — normalized To/CC/BCC from email JSON
- **documents** — 1.41M document metadata records
- **document_fulltext** — merged full-text from 5 volume shards
- **photos** — 18K photo records
- **people** — 473 identified individuals
- **photo_faces** — 975 face detection results
- **imessage_conversations** — 15 iMessage conversations
- **imessage_messages** — 4,509 iMessage messages
- **star_counts** — 414K user star/vote counts
- **release_batches** — 11 government release batches

## Storage Model

The storage abstraction (`src/lib/storage/`) provides a clean interface:

```typescript
interface StorageProvider {
  read(path: string): Promise<Buffer>;
  write(path: string, data: Buffer | string): Promise<void>;
  exists(path: string): Promise<boolean>;
  list(prefix: string): Promise<string[]>;
  delete(path: string): Promise<void>;
  getUrl(path: string): string;
}
```

Currently uses `LocalStorageProvider` backed by the filesystem. To switch to cloud storage, implement the same interface for S3/R2/B2.

## Search & Indexing Strategy

### PostgreSQL Full-Text Search
- `tsvector` columns on emails (subject + body), document_fulltext (text), and imessage_messages (body)
- GIN indexes for fast full-text queries
- `ts_rank()` for relevance scoring
- `ts_headline()` for result snippets with keyword highlighting

### pg_trgm Fuzzy Matching
- Trigram GIN indexes on people.name, emails.sender, emails.subject, documents.filename
- Supports ILIKE pattern matching and similarity queries
- Catches misspellings and partial matches

### B-tree Indexes
- All primary keys, foreign keys, timestamps
- Frequently filtered fields: sender, doc_id, release_batch, conversation_slug, volume

## Deployment Portability

The architecture is designed for easy migration:
1. **Storage** — swap LocalStorageProvider for S3Provider
2. **Database** — change DATABASE_URL to point to managed Postgres
3. **App** — deploy Next.js to Vercel/Railway/Fly.io
4. **No hardcoded paths** — all paths come from env vars
