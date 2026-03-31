#!/usr/bin/env python3
"""Build full-text search indexes and pg_trgm indexes in PostgreSQL."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jmail:jmail_local@localhost:5432/jmail")


INDEX_SQL = [
    # ─── Full-text search tsvector updates ─────────────────────
    ("Updating email search vectors",
     """UPDATE emails SET search_vector = to_tsvector('english',
         coalesce(subject, '') || ' ' || coalesce(body, '') || ' ' || coalesce(sender, '')
     ) WHERE search_vector IS NULL"""),

    ("Updating document fulltext search vectors",
     """UPDATE document_fulltext SET search_vector = to_tsvector('english',
         coalesce(text, '')
     ) WHERE search_vector IS NULL"""),

    ("Updating imessage search vectors",
     """UPDATE imessage_messages SET search_vector = to_tsvector('english',
         coalesce(body, '') || ' ' || coalesce(sender, '')
     ) WHERE search_vector IS NULL"""),

    # ─── GIN indexes on tsvectors ──────────────────────────────
    ("Creating GIN index on emails.search_vector",
     "CREATE INDEX IF NOT EXISTS emails_search_idx ON emails USING GIN (search_vector)"),

    ("Creating GIN index on document_fulltext.search_vector",
     "CREATE INDEX IF NOT EXISTS document_fulltext_search_idx ON document_fulltext USING GIN (search_vector)"),

    ("Creating GIN index on imessage_messages.search_vector",
     "CREATE INDEX IF NOT EXISTS imessage_messages_search_idx ON imessage_messages USING GIN (search_vector)"),

    # ─── pg_trgm indexes for fuzzy matching ────────────────────
    ("Creating trigram index on people.name",
     "CREATE INDEX IF NOT EXISTS people_name_trgm_idx ON people USING GIN (name gin_trgm_ops)"),

    ("Creating trigram index on emails.sender",
     "CREATE INDEX IF NOT EXISTS emails_sender_trgm_idx ON emails USING GIN (sender gin_trgm_ops)"),

    ("Creating trigram index on emails.subject",
     "CREATE INDEX IF NOT EXISTS emails_subject_trgm_idx ON emails USING GIN (subject gin_trgm_ops)"),

    ("Creating trigram index on documents.filename",
     "CREATE INDEX IF NOT EXISTS documents_filename_trgm_idx ON documents USING GIN (filename gin_trgm_ops)"),

    ("Creating trigram index on documents.title",
     "CREATE INDEX IF NOT EXISTS documents_title_trgm_idx ON documents USING GIN (title gin_trgm_ops)"),

    # ─── B-tree indexes ────────────────────────────────────────
    ("Creating index on emails.doc_id",
     "CREATE INDEX IF NOT EXISTS emails_doc_id_idx ON emails (doc_id)"),

    ("Creating index on emails.sender",
     "CREATE INDEX IF NOT EXISTS emails_sender_btree_idx ON emails (sender)"),

    ("Creating index on emails.date",
     "CREATE INDEX IF NOT EXISTS emails_date_idx ON emails (date)"),

    ("Creating index on emails.thread_id",
     "CREATE INDEX IF NOT EXISTS emails_thread_id_idx ON emails (thread_id)"),

    ("Creating index on emails.release_batch",
     "CREATE INDEX IF NOT EXISTS emails_release_batch_idx ON emails (release_batch)"),

    ("Creating index on email_recipients.email_id",
     "CREATE INDEX IF NOT EXISTS email_recipients_email_id_idx ON email_recipients (email_id)"),

    ("Creating index on email_recipients.email",
     "CREATE INDEX IF NOT EXISTS email_recipients_email_idx ON email_recipients (email)"),

    ("Creating index on documents.doc_id",
     "CREATE INDEX IF NOT EXISTS documents_doc_id_idx ON documents (doc_id)"),

    ("Creating index on documents.volume",
     "CREATE INDEX IF NOT EXISTS documents_volume_idx ON documents (volume)"),

    ("Creating index on documents.release_batch",
     "CREATE INDEX IF NOT EXISTS documents_release_batch_idx ON documents (release_batch)"),

    ("Creating index on document_fulltext.doc_id",
     "CREATE INDEX IF NOT EXISTS document_fulltext_doc_id_idx ON document_fulltext (doc_id)"),

    ("Creating index on photos.release_batch",
     "CREATE INDEX IF NOT EXISTS photos_release_batch_idx ON photos (release_batch)"),

    ("Creating index on photos.date_taken",
     "CREATE INDEX IF NOT EXISTS photos_date_taken_idx ON photos (date_taken)"),

    ("Creating index on people.slug",
     "CREATE INDEX IF NOT EXISTS people_slug_idx ON people (slug)"),

    ("Creating index on photo_faces.photo_id",
     "CREATE INDEX IF NOT EXISTS photo_faces_photo_id_idx ON photo_faces (photo_id)"),

    ("Creating index on photo_faces.person_id",
     "CREATE INDEX IF NOT EXISTS photo_faces_person_id_idx ON photo_faces (person_id)"),

    ("Creating index on imessage_conversations.slug",
     "CREATE INDEX IF NOT EXISTS imessage_conversations_slug_idx ON imessage_conversations (slug)"),

    ("Creating index on imessage_messages.conversation_slug",
     "CREATE INDEX IF NOT EXISTS imessage_messages_conversation_slug_idx ON imessage_messages (conversation_slug)"),

    ("Creating index on imessage_messages.date",
     "CREATE INDEX IF NOT EXISTS imessage_messages_date_idx ON imessage_messages (date)"),

    ("Creating index on star_counts entity",
     "CREATE INDEX IF NOT EXISTS star_counts_entity_idx ON star_counts (entity_type, entity_id)"),

    ("Creating index on asset_registry.status",
     "CREATE INDEX IF NOT EXISTS asset_registry_status_idx ON asset_registry (status)"),

    ("Creating index on asset_registry source",
     "CREATE INDEX IF NOT EXISTS asset_registry_source_idx ON asset_registry (source_entity_type, source_entity_id)"),
]


def main():
    print("=" * 60)
    print("Building Search Indexes")
    print("=" * 60)

    pg = psycopg2.connect(DATABASE_URL)
    pg.autocommit = True
    cur = pg.cursor()

    for i, (desc, sql) in enumerate(INDEX_SQL, 1):
        print(f"  [{i}/{len(INDEX_SQL)}] {desc}...")
        try:
            cur.execute(sql)
            print(f"    ✓ Done")
        except Exception as e:
            print(f"    ✗ Error: {e}")

    # Analyze tables for query planner
    print("\n  Running ANALYZE on all tables...")
    tables = [
        "emails", "email_recipients", "documents", "document_fulltext",
        "photos", "people", "photo_faces", "imessage_conversations",
        "imessage_messages", "star_counts", "release_batches",
        "asset_registry", "mirrored_files"
    ]
    for table in tables:
        try:
            cur.execute(f"ANALYZE {table}")
        except Exception:
            pass

    print("    ✓ ANALYZE complete")

    cur.close()
    pg.close()

    print("\n✓ All indexes built successfully!")


if __name__ == "__main__":
    main()
