-- =============================================================================
-- migration_020_crs_template_short_text.sql
--
-- Purpose: Add short_template_text column to audit_core.crs_comment_template
--          for compact LLM prompt injection.
--
-- Applies after: migration_019_crs_audit_reset_type.sql
-- =============================================================================

BEGIN;

ALTER TABLE audit_core.crs_comment_template
    ADD COLUMN IF NOT EXISTS short_template_text TEXT NULL;

COMMENT ON COLUMN audit_core.crs_comment_template.short_template_text IS
    'Compact one-line description for LLM prompt injection. '
    'Format: "KEYWORD: brief description". '
    'Example: "TAG_MISSING: tag not in register". '
    'NULL = use check_type as fallback in _build_categories_line().';

COMMIT;


-- =============================================================================
-- VERIFICATION (run manually after applying)
-- =============================================================================

/*
SELECT attname, format_type(atttypid, atttypmod)
FROM pg_attribute
WHERE attrelid = 'audit_core.crs_comment_template'::regclass
  AND attname = 'short_template_text'
  AND NOT attisdropped;
-- Expected: short_template_text | text
*/
