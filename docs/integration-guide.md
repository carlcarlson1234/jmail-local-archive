# Jmail Local Archive — Integration Guide for External Apps

> This document tells another coding agent everything it needs to connect to and query the Jmail Local Archive data from a separate application.

## Connection Details

### PostgreSQL (Direct Database Access — Recommended)

```
Host:     localhost
Port:     5432
Database: jmail
User:     jmail
Password: jmail_local
```

**Connection string:**
```
postgresql://jmail:jmail_local@localhost:5432/jmail
```

The database is PostgreSQL 18 with `pg_trgm` and `unaccent` extensions enabled.

### Local HTTP API (REST)

```
Base URL: http://localhost:3001/api
```

The API is a Next.js app that must be running (`pnpm dev` from `C:\Users\13603\jmail-local-archive`).

---

## Option A: Direct PostgreSQL Access (Best for Apps with Their Own Backend)

Connect directly to the PostgreSQL database. This is the most flexible option and doesn't require the Jmail web app to be running.

### Available Tables and Row Counts

| Table | Rows | Primary Key | Description |
|-------|------|-------------|-------------|
| `emails` | 1,783,792 | `id` (text) | Full email archive with body text |
| `documents` | 1,413,417 | `id` (text) | Document metadata (filename, volume, bates numbers) |
| `document_fulltext` | 1,413,024 | `id` (serial) | Full extracted text of documents, linked by `doc_id` |
| `star_counts` | 414,274 | `id` (serial) | User star/vote counts per entity |
| `photos` | 18,308 | `id` (text) | Photo metadata (filename, dimensions, dates) |
| `imessage_messages` | 4,509 | `id` (text) | iMessage message content |
| `photo_faces` | 975 | `id` (serial) | Face detection results linking photos to people |
| `people` | 473 | `id` (text) | Identified individuals |
| `imessage_conversations` | 15 | `id` (text) | iMessage conversation metadata |
| `release_batches` | 11 | `id` (text) | Government document release batches |
| `asset_registry` | varies | `id` (serial) | Cataloged binary asset URLs |
| `mirrored_files` | 30 | `id` (serial) | Metadata about mirrored dataset files |

### Full Schema Reference

#### `emails`
```
id                  TEXT PRIMARY KEY    -- unique email identifier
doc_id              TEXT                -- document ID reference
subject             TEXT                -- email subject line
sender              TEXT                -- sender email address
sender_name         TEXT                -- sender display name
recipients          JSONB               -- array of recipient objects/strings
cc                  JSONB               -- array of CC recipients
bcc                 JSONB               -- array of BCC recipients
date                TIMESTAMPTZ         -- email date
body                TEXT                -- plain text body
body_html           TEXT                -- HTML body (if available)
thread_id           TEXT                -- thread grouping ID
in_reply_to         TEXT                -- parent message ID
labels              JSONB               -- email labels/folders
attachments         JSONB               -- attachment metadata array
starred             BOOLEAN             -- whether starred
star_count          INTEGER             -- number of stars
release_batch       TEXT                -- which government release batch
source              TEXT                -- data source identifier
raw_json            JSONB               -- complete original record
search_vector       TSVECTOR            -- pre-computed full-text index (subject + body + sender)
ingested_at         TIMESTAMPTZ         -- when ingested
```

#### `documents`
```
id                  TEXT PRIMARY KEY
doc_id              TEXT                -- document ID
title               TEXT                -- document title
filename            TEXT                -- original filename
file_type           TEXT                -- file extension/type
page_count          INTEGER             -- number of pages
volume              TEXT                -- DOJ volume (e.g., "VOL00009")
bates_start         TEXT                -- bates number range start
bates_end           TEXT                -- bates number range end
release_batch       TEXT
source              TEXT
pdf_url             TEXT                -- URL to source PDF (may not be local)
thumbnail_url       TEXT
raw_json            JSONB
ingested_at         TIMESTAMPTZ
```

#### `document_fulltext`
```
id                  SERIAL PRIMARY KEY
doc_id              TEXT NOT NULL       -- FK to documents.id
shard_name          TEXT                -- source shard (VOL00008, VOL00009, etc.)
page_number         INTEGER             -- page within document
text                TEXT                -- extracted text content
raw_json            JSONB
search_vector       TSVECTOR            -- pre-computed full-text index on text
ingested_at         TIMESTAMPTZ
```

#### `photos`
```
id                  TEXT PRIMARY KEY
filename            TEXT
title               TEXT
description         TEXT
date_taken          TIMESTAMPTZ
width               INTEGER
height              INTEGER
image_url           TEXT                -- source image URL
thumbnail_url       TEXT
volume              TEXT
release_batch       TEXT
source              TEXT
raw_json            JSONB
ingested_at         TIMESTAMPTZ
```

#### `people`
```
id                  TEXT PRIMARY KEY
name                TEXT                -- display name
slug                TEXT                -- URL-safe slug
aliases             JSONB               -- array of alternative names
description         TEXT
image_url           TEXT
email_addresses     JSONB               -- array of known email addresses
raw_json            JSONB
ingested_at         TIMESTAMPTZ
```

#### `imessage_conversations`
```
id                  TEXT PRIMARY KEY
slug                TEXT                -- URL-safe slug
title               TEXT                -- conversation title
participants        JSONB               -- array of participant info
message_count       INTEGER
raw_json            JSONB
ingested_at         TIMESTAMPTZ
```

#### `imessage_messages`
```
id                  TEXT PRIMARY KEY
conversation_id     TEXT                -- FK to imessage_conversations.id
conversation_slug   TEXT
sender              TEXT
body                TEXT                -- message text
date                TIMESTAMPTZ
attachments         JSONB
raw_json            JSONB
search_vector       TSVECTOR            -- full-text index on body + sender
ingested_at         TIMESTAMPTZ
```

#### `photo_faces`
```
id                  SERIAL PRIMARY KEY
photo_id            TEXT                -- FK to photos.id
person_id           TEXT                -- FK to people.id
confidence          TEXT
bounding_box        JSONB
raw_json            JSONB
ingested_at         TIMESTAMPTZ
```

#### `star_counts`
```
id                  SERIAL PRIMARY KEY
entity_type         TEXT                -- which table this refers to
entity_id           TEXT                -- ID within that table
count               INTEGER             -- star count
raw_json            JSONB
ingested_at         TIMESTAMPTZ
```

#### `release_batches`
```
id                  TEXT PRIMARY KEY
name                TEXT
release_date        TIMESTAMPTZ
description         TEXT
source              TEXT
document_count      INTEGER
raw_json            JSONB
ingested_at         TIMESTAMPTZ
```

#### `asset_registry`
```
id                  SERIAL PRIMARY KEY
asset_url           TEXT NOT NULL UNIQUE -- original URL of the asset
source_dataset      TEXT                -- which dataset it was found in
source_entity_type  TEXT                -- entity type (photo, document, etc.)
source_entity_id    TEXT                -- ID of the entity it belongs to
local_path          TEXT                -- local file path (if downloaded)
content_type        TEXT                -- MIME type
size_bytes          BIGINT
sha256              TEXT
http_status         INTEGER
status              TEXT                -- discovered | downloaded | unreachable | failed
discovered_at       TIMESTAMPTZ
downloaded_at       TIMESTAMPTZ
```

### Key Relationships

```
emails.id           → email_recipients.email_id
documents.id        → document_fulltext.doc_id
photos.id           → photo_faces.photo_id
people.id           → photo_faces.person_id
imessage_conversations.id → imessage_messages.conversation_id
imessage_conversations.slug → imessage_messages.conversation_slug
```

### Search Indexes Available

These indexes are pre-built and ready to use:

**Full-text search (tsvector + GIN):**
- `emails.search_vector` — covers subject + body + sender
- `document_fulltext.search_vector` — covers extracted text
- `imessage_messages.search_vector` — covers body + sender

**Trigram fuzzy matching (pg_trgm + GIN):**
- `people.name`
- `emails.sender`, `emails.subject`
- `documents.filename`, `documents.title`

### Example Queries

#### Full-text search across emails
```sql
SELECT id, subject, sender, date,
       ts_rank(search_vector, to_tsquery('english', 'Gates & meeting')) as score,
       ts_headline('english', body, to_tsquery('english', 'Gates & meeting'),
         'MaxFragments=1,MaxWords=30') as snippet
FROM emails
WHERE search_vector @@ to_tsquery('english', 'Gates & meeting')
ORDER BY score DESC
LIMIT 20;
```

#### Fuzzy name matching on people
```sql
SELECT id, name, slug
FROM people
WHERE name % 'Epstein'  -- trigram similarity
ORDER BY similarity(name, 'Epstein') DESC
LIMIT 10;
```

#### Get a document with its full text
```sql
SELECT d.id, d.title, d.filename, d.volume,
       string_agg(df.text, E'\n' ORDER BY df.page_number) as full_text
FROM documents d
JOIN document_fulltext df ON df.doc_id = d.id
WHERE d.id = 'SOME_DOC_ID'
GROUP BY d.id, d.title, d.filename, d.volume;
```

#### Find people in photos
```sql
SELECT p.name, ph.filename, pf.confidence
FROM photo_faces pf
JOIN people p ON p.id = pf.person_id
JOIN photos ph ON ph.id = pf.photo_id
WHERE p.name ILIKE '%Maxwell%';
```

#### Get all messages in a conversation
```sql
SELECT sender, body, date
FROM imessage_messages
WHERE conversation_slug = 'some-slug'
ORDER BY date;
```

#### Search documents by text content
```sql
SELECT df.doc_id, d.title, d.volume,
       ts_headline('english', df.text, to_tsquery('english', 'financial & records'),
         'MaxFragments=2,MaxWords=40') as snippet
FROM document_fulltext df
JOIN documents d ON d.id = df.doc_id
WHERE df.search_vector @@ to_tsquery('english', 'financial & records')
LIMIT 20;
```

### The `raw_json` Escape Hatch

Every table has a `raw_json` JSONB column containing the complete, original parquet record. If a column you need isn't broken out into a dedicated column, check `raw_json`:

```sql
SELECT raw_json->>'some_field' FROM emails WHERE id = 'some_id';
```

---

## Option B: HTTP API Access (Best for Frontend-Only or Cross-Language Apps)

Requires the Jmail web app to be running (`pnpm dev` from `C:\Users\13603\jmail-local-archive`).

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | `{ status, database, timestamp }` |
| GET | `/api/stats` | Row counts, mirror status, last ingest |
| GET | `/api/search?q=...&type=...&limit=...&offset=...` | Full-text search |
| GET | `/api/emails/:id` | Single email with all fields |
| GET | `/api/documents/:id` | Document + fulltext pages |
| GET | `/api/people/:id` | Person record |
| GET | `/api/photos/:id` | Photo record |
| GET | `/api/conversations/:slug` | Conversation + all messages |
| GET | `/api/messages/:id` | Single message |
| GET | `/api/assets/:id` | Asset registry entry |
| GET | `/api/entities/:type/:id/assets` | All assets for an entity |

### Search API

```
GET http://localhost:3001/api/search?q=Gates&type=emails&limit=20&offset=0
```

**Parameters:**
- `q` (required) — search query (words joined with `&` for AND matching)
- `type` — `all` | `emails` | `documents` | `messages` | `photos` | `people`
- `limit` — max results (default 20, max 100)
- `offset` — pagination offset

**Response:**
```json
{
  "results": [
    {
      "entityType": "email",
      "entityId": "EFTA02605171",
      "title": "Re: Meeting",
      "snippet": "...confirmed the <b>Gates</b> meeting...",
      "date": "2014-03-15T10:30:00Z",
      "source": "batch_1",
      "score": 0.892
    }
  ],
  "query": "Gates",
  "type": "emails",
  "limit": 20,
  "offset": 0
}
```

### Example: Fetch from JavaScript/TypeScript

```typescript
// Search
const res = await fetch('http://localhost:3001/api/search?q=Maxwell&type=all&limit=10');
const { results } = await res.json();

// Get specific email
const email = await fetch('http://localhost:3001/api/emails/EFTA02605171').then(r => r.json());

// Get document with fulltext
const doc = await fetch('http://localhost:3001/api/documents/SOME_ID').then(r => r.json());
// doc.fulltext is an array of { doc_id, shard_name, page_number, text } objects

// Get person
const person = await fetch('http://localhost:3001/api/people/some-id').then(r => r.json());
```

### Example: Fetch from Python

```python
import requests

# Search
results = requests.get('http://localhost:3001/api/search', params={
    'q': 'Maxwell', 'type': 'emails', 'limit': 20
}).json()

# Get entity
email = requests.get(f'http://localhost:3001/api/emails/{email_id}').json()
```

---

## Raw File Access

All original dataset files are mirrored locally and can be read directly with DuckDB or pandas:

```
C:\Users\13603\jmail-local-archive\data\raw\jmail\
├── manifest.json              -- dataset index with checksums
├── emails.parquet             -- 319 MB, 1.78M rows
├── emails.ndjson.gz           -- 432 MB
├── emails-slim.parquet        -- 39 MB (emails without body text)
├── emails-slim.ndjson.gz
├── documents.parquet          -- 24 MB, 1.41M rows
├── documents.ndjson.gz
├── documents-full/
│   ├── VOL00008.parquet       -- 24 MB, 32K rows
│   ├── VOL00009.parquet       -- 235 MB, 531K rows
│   ├── VOL00010.parquet       -- 155 MB, 503K rows
│   ├── DataSet11.parquet      -- 90 MB, 332K rows
│   ├── other.parquet          -- 7.5 MB, 15K rows
│   └── *.ndjson.gz            -- same data in NDJSON format
├── photos.parquet             -- 1.1 MB, 18K rows
├── people.parquet             -- 10 KB, 473 rows
├── photo_faces.parquet        -- 58 KB, 975 rows
├── star_counts.parquet        -- 2 MB, 414K rows
├── release_batches.parquet    -- 1.3 KB, 11 rows
├── imessage_conversations.parquet
└── imessage_messages.parquet
```

### Reading with DuckDB (Python)
```python
import duckdb
con = duckdb.connect()
df = con.execute("SELECT * FROM 'C:/Users/13603/jmail-local-archive/data/raw/jmail/emails.parquet' LIMIT 10").fetchdf()
```

### Reading with pandas
```python
import pandas as pd
df = pd.read_parquet('C:/Users/13603/jmail-local-archive/data/raw/jmail/emails.parquet')
```

---

## Important Notes for Integration

1. **All text IDs**: Most primary keys are `TEXT`, not integers. Always use string comparison.
2. **JSONB columns**: `recipients`, `cc`, `bcc`, `labels`, `attachments`, `aliases`, `participants`, `email_addresses` are all JSONB. Use `->` for JSON access, `->>` for text extraction.
3. **The `raw_json` column** on every table contains the complete original record. If a field you need isn't in a dedicated column, it's in there.
4. **Timestamps are UTC** with timezone (`TIMESTAMPTZ`).
5. **No foreign key constraints** are enforced at the DB level — joins work but cascading deletes aren't configured. This is intentional for bulk-load performance.
6. **Search vectors are pre-computed** — don't recompute them; query against the existing `search_vector` columns.
7. **The database is read-heavy** — the data is loaded once via batch ingestion and then queried. Your app should treat it as a read-only data source.
