/*
migration_014_crs_add_document_number.sql

Purpose:
  Add document_number column to audit_core.crs_comment.
  This field stores a reference to a project document that contains the tag,
  extracted from the DOCUMENT_NUMBER column in the CRS detail sheet.

  Distinct from crs_doc_number (the CRS source file header number).
  Stores 'Not Applicable' when the DOCUMENT_NUMBER column is absent in the detail sheet.

Gate:
  All CREATE/ALTER operations use IF NOT EXISTS / IF EXISTS — idempotent, safe to re-run.

Changes:
  2026-03-27 — Initial implementation.
*/

BEGIN;

ALTER TABLE "audit_core"."crs_comment"
    ADD COLUMN IF NOT EXISTS "document_number" TEXT NULL;

COMMENT ON COLUMN "audit_core"."crs_comment"."document_number" IS
    'Project document reference containing the tag (DOCUMENT_NUMBER column in '
    'detail sheet). Stores ''Not Applicable'' when column is absent in source. '
    'Distinct from crs_doc_number (the CRS header file number).';

-- Partial index: exclude NULL and 'Not Applicable' — only index actionable references
CREATE INDEX IF NOT EXISTS "idx_crs_comment_document_number"
    ON "audit_core"."crs_comment"("document_number")
    WHERE "document_number" IS NOT NULL
      AND "document_number" != 'Not Applicable';

COMMIT;


-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm after applying)
-- =============================================================================

/*
-- 1. Column exists with correct type:
SELECT attname, format_type(atttypid, atttypmod), attnotnull
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'audit_core'
  AND c.relname = 'crs_comment'
  AND a.attname = 'document_number'
  AND NOT a.attisdropped;
-- Expected: document_number | text | false

-- 2. Partial index created:
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'audit_core'
  AND tablename = 'crs_comment'
  AND indexname = 'idx_crs_comment_document_number';

-- 3. Column comment:
SELECT col_description(
    'audit_core.crs_comment'::regclass,
    (SELECT attnum FROM pg_attribute
     WHERE attrelid = 'audit_core.crs_comment'::regclass
       AND attname = 'document_number')
);
*/
