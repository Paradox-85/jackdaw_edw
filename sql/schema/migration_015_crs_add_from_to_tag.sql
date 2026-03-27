-- =============================================================================
-- migration_015_crs_add_from_to_tag.sql
--
-- Purpose:
--   Add from_tag / to_tag columns to audit_core.crs_comment.
--   These fields represent directional tag relationships found in specific
--   CRS detail sheets (e.g. pipeline / cable routing comments).
--   Both columns are NULL when the detail sheet does not contain FROM_TAG/TO_TAG.
--   In these cases tag_name remains the primary tag identifier.
--
-- Applies after: migration_014_crs_add_document_number.sql
-- =============================================================================

BEGIN;

ALTER TABLE "audit_core"."crs_comment"
    ADD COLUMN IF NOT EXISTS "from_tag" TEXT NULL,
    ADD COLUMN IF NOT EXISTS "to_tag"   TEXT NULL;

COMMENT ON COLUMN "audit_core"."crs_comment"."from_tag" IS
    'Source tag in a directional tag pair (FROM_TAG column in detail sheet). '
    'NULL when not applicable to this record type.';

COMMENT ON COLUMN "audit_core"."crs_comment"."to_tag" IS
    'Destination tag in a directional tag pair (TO_TAG column in detail sheet). '
    'NULL when not applicable to this record type.';

CREATE INDEX IF NOT EXISTS "idx_crs_comment_from_tag"
    ON "audit_core"."crs_comment"("from_tag")
    WHERE "from_tag" IS NOT NULL;

CREATE INDEX IF NOT EXISTS "idx_crs_comment_to_tag"
    ON "audit_core"."crs_comment"("to_tag")
    WHERE "to_tag" IS NOT NULL;

COMMIT;


-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm after applying)
-- =============================================================================

/*
-- 1. Columns exist with correct types:
SELECT attname, format_type(atttypid, atttypmod), attnotnull
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'audit_core'
  AND c.relname = 'crs_comment'
  AND a.attname IN ('from_tag', 'to_tag')
  AND NOT a.attisdropped;
-- Expected: from_tag | text | false
--           to_tag   | text | false

-- 2. Partial indexes created:
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'audit_core'
  AND tablename = 'crs_comment'
  AND indexname IN ('idx_crs_comment_from_tag', 'idx_crs_comment_to_tag');
*/
