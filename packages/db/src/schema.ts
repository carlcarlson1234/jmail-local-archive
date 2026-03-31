import {
  pgTable, serial, text, integer, bigint, boolean, timestamp, jsonb,
  index, uniqueIndex, varchar,
} from 'drizzle-orm/pg-core';
import { sql } from 'drizzle-orm';

// ─── Infrastructure Tables ───────────────────────────────────────────

export const datasetManifest = pgTable('dataset_manifest', {
  id: serial('id').primaryKey(),
  runId: text('run_id'),
  generatedAt: timestamp('generated_at', { withTimezone: true }),
  rawJson: jsonb('raw_json'),
  fetchedAt: timestamp('fetched_at', { withTimezone: true }).defaultNow(),
});

export const mirroredFiles = pgTable('mirrored_files', {
  id: serial('id').primaryKey(),
  datasetName: text('dataset_name').notNull(),
  format: text('format').notNull(),
  url: text('url').notNull(),
  localPath: text('local_path').notNull(),
  expectedSize: bigint('expected_size', { mode: 'number' }),
  actualSize: bigint('actual_size', { mode: 'number' }),
  expectedSha256: text('expected_sha256'),
  actualSha256: text('actual_sha256'),
  status: text('status').default('pending'),
  downloadedAt: timestamp('downloaded_at', { withTimezone: true }),
  verifiedAt: timestamp('verified_at', { withTimezone: true }),
}, (t) => [
  uniqueIndex('mirrored_files_dataset_format_idx').on(t.datasetName, t.format),
]);

export const ingestRuns = pgTable('ingest_runs', {
  id: serial('id').primaryKey(),
  startedAt: timestamp('started_at', { withTimezone: true }).defaultNow(),
  completedAt: timestamp('completed_at', { withTimezone: true }),
  status: text('status').default('running'),
  tablesLoaded: jsonb('tables_loaded'),
  rowCounts: jsonb('row_counts'),
  errors: jsonb('errors'),
});

export const assetRegistry = pgTable('asset_registry', {
  id: serial('id').primaryKey(),
  assetUrl: text('asset_url').notNull(),
  referringUrl: text('referring_url'),
  sourceDataset: text('source_dataset'),
  sourceEntityType: text('source_entity_type'),
  sourceEntityId: text('source_entity_id'),
  localPath: text('local_path'),
  contentType: text('content_type'),
  sizeBytes: bigint('size_bytes', { mode: 'number' }),
  sha256: text('sha256'),
  httpStatus: integer('http_status'),
  status: text('status').default('discovered'),
  discoveredAt: timestamp('discovered_at', { withTimezone: true }).defaultNow(),
  downloadedAt: timestamp('downloaded_at', { withTimezone: true }),
}, (t) => [
  uniqueIndex('asset_registry_url_idx').on(t.assetUrl),
  index('asset_registry_source_idx').on(t.sourceEntityType, t.sourceEntityId),
  index('asset_registry_status_idx').on(t.status),
]);

export const downloadAudit = pgTable('download_audit', {
  id: serial('id').primaryKey(),
  url: text('url').notNull(),
  httpStatus: integer('http_status'),
  contentType: text('content_type'),
  sizeBytes: bigint('size_bytes', { mode: 'number' }),
  durationMs: integer('duration_ms'),
  error: text('error'),
  attemptedAt: timestamp('attempted_at', { withTimezone: true }).defaultNow(),
});

// ─── Core Data Tables ────────────────────────────────────────────────

export const emails = pgTable('emails', {
  id: text('id').primaryKey(),
  docId: text('doc_id'),
  subject: text('subject'),
  sender: text('sender'),
  senderName: text('sender_name'),
  recipients: jsonb('recipients'),
  cc: jsonb('cc'),
  bcc: jsonb('bcc'),
  date: timestamp('date', { withTimezone: true }),
  body: text('body'),
  bodyHtml: text('body_html'),
  threadId: text('thread_id'),
  inReplyTo: text('in_reply_to'),
  labels: jsonb('labels'),
  attachments: jsonb('attachments'),
  starred: boolean('starred'),
  starCount: integer('star_count'),
  releaseBatch: text('release_batch'),
  source: text('source'),
  rawJson: jsonb('raw_json'),
  searchVector: text('search_vector'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('emails_doc_id_idx').on(t.docId),
  index('emails_sender_idx').on(t.sender),
  index('emails_date_idx').on(t.date),
  index('emails_thread_id_idx').on(t.threadId),
  index('emails_release_batch_idx').on(t.releaseBatch),
]);

export const emailRecipients = pgTable('email_recipients', {
  id: serial('id').primaryKey(),
  emailId: text('email_id').notNull(),
  recipientType: text('recipient_type').notNull(), // to, cc, bcc
  email: text('email'),
  name: text('name'),
}, (t) => [
  index('email_recipients_email_id_idx').on(t.emailId),
  index('email_recipients_email_idx').on(t.email),
]);

export const documents = pgTable('documents', {
  id: text('id').primaryKey(),
  docId: text('doc_id'),
  title: text('title'),
  filename: text('filename'),
  fileType: text('file_type'),
  pageCount: integer('page_count'),
  volume: text('volume'),
  batesStart: text('bates_start'),
  batesEnd: text('bates_end'),
  releaseBatch: text('release_batch'),
  source: text('source'),
  pdfUrl: text('pdf_url'),
  thumbnailUrl: text('thumbnail_url'),
  rawJson: jsonb('raw_json'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('documents_doc_id_idx').on(t.docId),
  index('documents_volume_idx').on(t.volume),
  index('documents_release_batch_idx').on(t.releaseBatch),
  index('documents_filename_idx').on(t.filename),
]);

export const documentFulltext = pgTable('document_fulltext', {
  id: serial('id').primaryKey(),
  docId: text('doc_id').notNull(),
  shardName: text('shard_name'),
  pageNumber: integer('page_number'),
  text: text('text'),
  rawJson: jsonb('raw_json'),
  searchVector: text('search_vector'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('document_fulltext_doc_id_idx').on(t.docId),
  index('document_fulltext_shard_idx').on(t.shardName),
]);

export const photos = pgTable('photos', {
  id: text('id').primaryKey(),
  filename: text('filename'),
  title: text('title'),
  description: text('description'),
  dateTaken: timestamp('date_taken', { withTimezone: true }),
  width: integer('width'),
  height: integer('height'),
  imageUrl: text('image_url'),
  thumbnailUrl: text('thumbnail_url'),
  volume: text('volume'),
  releaseBatch: text('release_batch'),
  source: text('source'),
  rawJson: jsonb('raw_json'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('photos_release_batch_idx').on(t.releaseBatch),
  index('photos_date_taken_idx').on(t.dateTaken),
]);

export const people = pgTable('people', {
  id: text('id').primaryKey(),
  name: text('name'),
  slug: text('slug'),
  aliases: jsonb('aliases'),
  description: text('description'),
  imageUrl: text('image_url'),
  emailAddresses: jsonb('email_addresses'),
  rawJson: jsonb('raw_json'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('people_slug_idx').on(t.slug),
  index('people_name_idx').on(t.name),
]);

export const photoFaces = pgTable('photo_faces', {
  id: serial('id').primaryKey(),
  photoId: text('photo_id'),
  personId: text('person_id'),
  confidence: text('confidence'),
  boundingBox: jsonb('bounding_box'),
  rawJson: jsonb('raw_json'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('photo_faces_photo_id_idx').on(t.photoId),
  index('photo_faces_person_id_idx').on(t.personId),
]);

export const imessageConversations = pgTable('imessage_conversations', {
  id: text('id').primaryKey(),
  slug: text('slug'),
  title: text('title'),
  participants: jsonb('participants'),
  messageCount: integer('message_count'),
  rawJson: jsonb('raw_json'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('imessage_conversations_slug_idx').on(t.slug),
]);

export const imessageMessages = pgTable('imessage_messages', {
  id: text('id').primaryKey(),
  conversationId: text('conversation_id'),
  conversationSlug: text('conversation_slug'),
  sender: text('sender'),
  body: text('body'),
  date: timestamp('date', { withTimezone: true }),
  attachments: jsonb('attachments'),
  rawJson: jsonb('raw_json'),
  searchVector: text('search_vector'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('imessage_messages_conversation_id_idx').on(t.conversationId),
  index('imessage_messages_conversation_slug_idx').on(t.conversationSlug),
  index('imessage_messages_sender_idx').on(t.sender),
  index('imessage_messages_date_idx').on(t.date),
]);

export const starCounts = pgTable('star_counts', {
  id: serial('id').primaryKey(),
  entityType: text('entity_type'),
  entityId: text('entity_id'),
  count: integer('count'),
  rawJson: jsonb('raw_json'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
}, (t) => [
  index('star_counts_entity_idx').on(t.entityType, t.entityId),
]);

export const releaseBatches = pgTable('release_batches', {
  id: text('id').primaryKey(),
  name: text('name'),
  releaseDate: timestamp('release_date', { withTimezone: true }),
  description: text('description'),
  source: text('source'),
  documentCount: integer('document_count'),
  rawJson: jsonb('raw_json'),
  ingestedAt: timestamp('ingested_at', { withTimezone: true }).defaultNow(),
});
