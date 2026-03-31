import { db } from './index';
import * as schema from './schema';
import { eq, ilike, sql, desc, asc, and, or, SQL } from 'drizzle-orm';

// ─── Search ──────────────────────────────────────────────────────────

export interface SearchOptions {
  query: string;
  type?: 'all' | 'emails' | 'documents' | 'messages' | 'photos' | 'people';
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  entityType: string;
  entityId: string;
  title: string;
  snippet: string;
  date: string | null;
  source: string | null;
  score: number;
}

export async function searchAll(options: SearchOptions): Promise<SearchResult[]> {
  const { query, type = 'all', limit = 20, offset = 0 } = options;
  const results: SearchResult[] = [];
  const tsQuery = query.split(/\s+/).filter(Boolean).join(' & ');

  if (type === 'all' || type === 'emails') {
    const emailResults = await db.execute(sql`
      SELECT id, subject, sender, date, release_batch,
             ts_rank(to_tsvector('english', coalesce(subject,'') || ' ' || coalesce(body,'')), to_tsquery('english', ${tsQuery})) as score,
             ts_headline('english', coalesce(body, coalesce(subject,'')), to_tsquery('english', ${tsQuery}),
               'MaxFragments=1,MaxWords=30,MinWords=10') as snippet
      FROM emails
      WHERE to_tsvector('english', coalesce(subject,'') || ' ' || coalesce(body,'')) @@ to_tsquery('english', ${tsQuery})
      ORDER BY score DESC
      LIMIT ${limit} OFFSET ${offset}
    `);
    for (const row of emailResults) {
      results.push({
        entityType: 'email',
        entityId: String(row.id),
        title: String(row.subject || '(no subject)'),
        snippet: String(row.snippet || ''),
        date: row.date ? String(row.date) : null,
        source: String(row.release_batch || ''),
        score: Number(row.score || 0),
      });
    }
  }

  if (type === 'all' || type === 'documents') {
    const docResults = await db.execute(sql`
      SELECT df.doc_id as id, d.title, d.filename, d.volume,
             ts_rank(to_tsvector('english', coalesce(df.text,'')), to_tsquery('english', ${tsQuery})) as score,
             ts_headline('english', coalesce(df.text,''), to_tsquery('english', ${tsQuery}),
               'MaxFragments=1,MaxWords=30,MinWords=10') as snippet
      FROM document_fulltext df
      LEFT JOIN documents d ON df.doc_id = d.id
      WHERE to_tsvector('english', coalesce(df.text,'')) @@ to_tsquery('english', ${tsQuery})
      ORDER BY score DESC
      LIMIT ${limit} OFFSET ${offset}
    `);
    for (const row of docResults) {
      results.push({
        entityType: 'document',
        entityId: String(row.id),
        title: String(row.title || row.filename || row.id),
        snippet: String(row.snippet || ''),
        date: null,
        source: String(row.volume || ''),
        score: Number(row.score || 0),
      });
    }
  }

  if (type === 'all' || type === 'messages') {
    const msgResults = await db.execute(sql`
      SELECT id, sender, body, date, conversation_slug,
             ts_rank(to_tsvector('english', coalesce(body,'')), to_tsquery('english', ${tsQuery})) as score,
             ts_headline('english', coalesce(body,''), to_tsquery('english', ${tsQuery}),
               'MaxFragments=1,MaxWords=30,MinWords=10') as snippet
      FROM imessage_messages
      WHERE to_tsvector('english', coalesce(body,'')) @@ to_tsquery('english', ${tsQuery})
      ORDER BY score DESC
      LIMIT ${limit} OFFSET ${offset}
    `);
    for (const row of msgResults) {
      results.push({
        entityType: 'message',
        entityId: String(row.id),
        title: `Message from ${row.sender || 'unknown'}`,
        snippet: String(row.snippet || ''),
        date: row.date ? String(row.date) : null,
        source: String(row.conversation_slug || ''),
        score: Number(row.score || 0),
      });
    }
  }

  if (type === 'all' || type === 'people') {
    const peopleResults = await db.execute(sql`
      SELECT id, name, slug, description
      FROM people
      WHERE name ILIKE ${'%' + query + '%'}
         OR description ILIKE ${'%' + query + '%'}
      LIMIT ${limit} OFFSET ${offset}
    `);
    for (const row of peopleResults) {
      results.push({
        entityType: 'person',
        entityId: String(row.id),
        title: String(row.name || ''),
        snippet: String(row.description || '').substring(0, 200),
        date: null,
        source: null,
        score: 1.0,
      });
    }
  }

  if (type === 'all' || type === 'photos') {
    const photoResults = await db.execute(sql`
      SELECT id, title, filename, description, date_taken, volume
      FROM photos
      WHERE title ILIKE ${'%' + query + '%'}
         OR filename ILIKE ${'%' + query + '%'}
         OR description ILIKE ${'%' + query + '%'}
      LIMIT ${limit} OFFSET ${offset}
    `);
    for (const row of photoResults) {
      results.push({
        entityType: 'photo',
        entityId: String(row.id),
        title: String(row.title || row.filename || ''),
        snippet: String(row.description || '').substring(0, 200),
        date: row.date_taken ? String(row.date_taken) : null,
        source: String(row.volume || ''),
        score: 1.0,
      });
    }
  }

  // Sort all results by score descending
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, limit);
}

// ─── Entity Queries ──────────────────────────────────────────────────

export async function getEmailById(id: string) {
  const rows = await db.select().from(schema.emails).where(eq(schema.emails.id, id)).limit(1);
  return rows[0] ?? null;
}

export async function getDocumentById(id: string) {
  const doc = await db.select().from(schema.documents).where(eq(schema.documents.id, id)).limit(1);
  const fulltext = await db.select().from(schema.documentFulltext)
    .where(eq(schema.documentFulltext.docId, id))
    .orderBy(asc(schema.documentFulltext.pageNumber));
  return doc[0] ? { ...doc[0], fulltext } : null;
}

export async function getPersonById(id: string) {
  const rows = await db.select().from(schema.people).where(eq(schema.people.id, id)).limit(1);
  return rows[0] ?? null;
}

export async function getPhotoById(id: string) {
  const rows = await db.select().from(schema.photos).where(eq(schema.photos.id, id)).limit(1);
  return rows[0] ?? null;
}

export async function getConversationBySlug(slug: string) {
  const conv = await db.select().from(schema.imessageConversations)
    .where(eq(schema.imessageConversations.slug, slug)).limit(1);
  if (!conv[0]) return null;
  const messages = await db.select().from(schema.imessageMessages)
    .where(eq(schema.imessageMessages.conversationSlug, slug))
    .orderBy(asc(schema.imessageMessages.date));
  return { ...conv[0], messages };
}

export async function getMessageById(id: string) {
  const rows = await db.select().from(schema.imessageMessages)
    .where(eq(schema.imessageMessages.id, id)).limit(1);
  return rows[0] ?? null;
}

export async function getAssetById(id: number) {
  const rows = await db.select().from(schema.assetRegistry)
    .where(eq(schema.assetRegistry.id, id)).limit(1);
  return rows[0] ?? null;
}

export async function listAssetsForEntity(entityType: string, entityId: string) {
  return db.select().from(schema.assetRegistry)
    .where(and(
      eq(schema.assetRegistry.sourceEntityType, entityType),
      eq(schema.assetRegistry.sourceEntityId, entityId)
    ));
}

// ─── Stats ───────────────────────────────────────────────────────────

export async function getStats() {
  const tableStats: Record<string, number> = {};
  const tables = [
    { name: 'emails', table: schema.emails },
    { name: 'email_recipients', table: schema.emailRecipients },
    { name: 'documents', table: schema.documents },
    { name: 'document_fulltext', table: schema.documentFulltext },
    { name: 'photos', table: schema.photos },
    { name: 'people', table: schema.people },
    { name: 'photo_faces', table: schema.photoFaces },
    { name: 'imessage_conversations', table: schema.imessageConversations },
    { name: 'imessage_messages', table: schema.imessageMessages },
    { name: 'star_counts', table: schema.starCounts },
    { name: 'release_batches', table: schema.releaseBatches },
    { name: 'mirrored_files', table: schema.mirroredFiles },
    { name: 'asset_registry', table: schema.assetRegistry },
  ];

  for (const { name } of tables) {
    try {
      const result = await db.execute(sql.raw(`SELECT count(*)::int as count FROM ${name}`));
      tableStats[name] = Number(result[0]?.count ?? 0);
    } catch {
      tableStats[name] = -1;
    }
  }

  const mirrorStatus = await db.execute(sql`
    SELECT status, count(*)::int as count FROM mirrored_files GROUP BY status
  `);

  const assetStatus = await db.execute(sql`
    SELECT status, count(*)::int as count FROM asset_registry GROUP BY status
  `);

  const lastIngest = await db.select().from(schema.ingestRuns)
    .orderBy(desc(schema.ingestRuns.startedAt))
    .limit(1);

  return {
    rowCounts: tableStats,
    mirrorStatus: mirrorStatus as any[],
    assetStatus: assetStatus as any[],
    lastIngest: lastIngest[0] ?? null,
  };
}
