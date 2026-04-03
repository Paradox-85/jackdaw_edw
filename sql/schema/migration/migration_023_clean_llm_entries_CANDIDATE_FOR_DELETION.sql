-- =============================================================================
-- migration_023_clean_llm_entries_from_reference_table.sql
--
-- Purpose:
--   One-time cleanup: migrate LLM-generated rows out of the reference table
--   audit_core.crs_comment_template and into the staging table
--   audit_core.crs_llm_template_staging.
--
--   Background: update_template_db() previously wrote LLM results directly
--   into crs_comment_template (source='llm'), polluting the read-only reference
--   table with unvalidated data. After this migration:
--     - crs_comment_template contains only manual entries (source='manual')
--     - all llm rows are preserved in crs_llm_template_staging as PendingReview
--
--   Safe to re-run: INSERT uses ON CONFLICT DO NOTHING; DELETE is idempotent.
--
-- Applies after: migration_022_add_crs_llm_staging.sql
-- Requires: crs_llm_template_staging table exists
-- =============================================================================

BEGIN;

-- Step 1: Migrate existing LLM rows to staging (preserve all data, nothing lost).
-- template_hash is CHAR(32) in staging vs TEXT in source — cast ensures type match.
INSERT INTO audit_core.crs_llm_template_staging (
    template_text,
    template_hash,
    suggested_category,
    check_type,
    confidence,
    llm_response,
    revision,
    occurrence_count,
    last_seen_at,
    created_at,
    object_status
)
SELECT
    template_text,
    CAST(template_hash AS CHAR(32)),
    category,
    check_type,
    CAST(confidence AS NUMERIC(4,3)),
    NULL,                                         -- llm_response was not stored in old table
    NULL,                                         -- revision was not stored in old table
    COALESCE(usage_count, 1),
    COALESCE(last_used_at, created_at),
    created_at,
    'PendingReview'
FROM audit_core.crs_comment_template
WHERE source = 'llm'
ON CONFLICT (template_hash) DO NOTHING;           -- safe re-run: skip already-migrated rows


-- Step 2: Remove LLM entries from the reference table.
DELETE FROM audit_core.crs_comment_template
WHERE source = 'llm';

COMMIT;


-- =============================================================================
-- VERIFICATION QUERIES (run manually after applying)
-- =============================================================================

/*
-- 1. Reference table should contain only manual entries:
SELECT source, COUNT(*) AS cnt
FROM audit_core.crs_comment_template
GROUP BY source;
-- Expected: manual | 50

-- 2. Migrated rows now in staging:
SELECT object_status, COUNT(*) AS cnt
FROM audit_core.crs_llm_template_staging
GROUP BY object_status;
-- Expected: PendingReview | N  (where N = number of LLM rows that existed)

-- 3. No LLM rows remain in reference table:
SELECT COUNT(*) FROM audit_core.crs_comment_template WHERE source = 'llm';
-- Expected: 0
*/
