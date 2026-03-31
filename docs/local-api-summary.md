# Local API Summary

Base URL: `http://localhost:3001`

All responses are JSON. All data comes from the local PostgreSQL database — no live Jmail calls.

## Endpoints

### Health & Stats

#### GET /api/health
Check database connectivity.

```bash
curl http://localhost:3001/api/health
```

```json
{"status": "ok", "database": "connected", "timestamp": "2026-03-31T00:00:00.000Z"}
```

#### GET /api/stats
Row counts, mirror status, asset status, last ingest info.

```bash
curl http://localhost:3001/api/stats
```

### Search

#### GET /api/search
Full-text search across all entity types.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | required | Search query |
| `type` | string | `all` | Filter: `all`, `emails`, `documents`, `messages`, `photos`, `people` |
| `limit` | int | `20` | Max results (capped at 100) |
| `offset` | int | `0` | Pagination offset |

```bash
# Search all types
curl "http://localhost:3001/api/search?q=Gates&type=all&limit=10"

# Search only emails
curl "http://localhost:3001/api/search?q=meeting+tomorrow&type=emails"

# Search documents
curl "http://localhost:3001/api/search?q=financial+records&type=documents&limit=20"
```

**Response shape:**
```json
{
  "results": [
    {
      "entityType": "email",
      "entityId": "EFTA02605171",
      "title": "Re: Meeting Tomorrow",
      "snippet": "...confirmed the <b>meeting</b> for <b>tomorrow</b> at...",
      "date": "2014-03-15T10:30:00Z",
      "source": "batch_1",
      "score": 0.892
    }
  ],
  "query": "meeting tomorrow",
  "type": "emails",
  "limit": 20,
  "offset": 0
}
```

### Entity Detail Endpoints

#### GET /api/emails/:id
```bash
curl http://localhost:3001/api/emails/EFTA02605171
```

#### GET /api/documents/:id
Returns document metadata + full text pages.
```bash
curl http://localhost:3001/api/documents/HOUSE_OVERSIGHT_029088
```

#### GET /api/people/:id
```bash
curl http://localhost:3001/api/people/jeffrey-epstein
```

#### GET /api/photos/:id
```bash
curl http://localhost:3001/api/photos/photo-12345
```

#### GET /api/conversations/:slug
Returns conversation metadata + all messages.
```bash
curl http://localhost:3001/api/conversations/some-conversation-slug
```

#### GET /api/messages/:id
```bash
curl http://localhost:3001/api/messages/msg-12345
```

#### GET /api/assets/:id
```bash
curl http://localhost:3001/api/assets/1
```

#### GET /api/entities/:type/:id/assets
List all discovered assets for a given entity.
```bash
curl http://localhost:3001/api/entities/email/EFTA02605171/assets
```

## TypeScript Usage

Future apps can import the data access layer directly:

```typescript
import { searchAll, getEmailById, getDocumentById } from '@jmail/db/queries';

// Search
const results = await searchAll({ query: 'Gates', type: 'emails', limit: 10 });

// Get entity
const email = await getEmailById('EFTA02605171');
const doc = await getDocumentById('HOUSE_OVERSIGHT_029088');
```

## Error Handling

- `200` — Success
- `404` — Entity not found
- `500` — Server error (check response body for `error` field)
- `503` — Database unavailable
