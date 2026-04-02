-- =============================================================================
-- migration_022_add_crs_llm_staging.sql
--
-- Purpose:
--   Add audit_core.crs_llm_template_staging — a staging table where Tier 3
--   LLM classification results are held for human review before being promoted
--   to the read-only reference table audit_core.crs_comment_template.
--
--   crs_comment_template = manual/curated reference only (50 CRS-C01…C50 rows).
--   LLM writes go HERE, not to crs_comment_template.
--
-- Applies after: migration_021_crs_short_text_seed.sql
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS audit_core.crs_llm_template_staging (
    id                 UUID         NOT NULL DEFAULT gen_random_uuid(),
    template_text      TEXT         NOT NULL,
    template_hash      CHAR(32)     NOT NULL,
    suggested_category VARCHAR(20)  NOT NULL,
    check_type         VARCHAR(50)  NULL,
    confidence         NUMERIC(4,3) NOT NULL,
    llm_response       TEXT         NULL,
    revision           VARCHAR(20)  NULL,
    occurrence_count   INTEGER      NOT NULL DEFAULT 1,
    last_seen_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    object_status      VARCHAR(20)  NOT NULL DEFAULT 'PendingReview',
    reviewed_at        TIMESTAMPTZ  NULL,
    review_notes       TEXT         NULL,

    CONSTRAINT crs_llm_staging_pkey         PRIMARY KEY (id),
    CONSTRAINT uq_llm_staging_hash          UNIQUE (template_hash),
    CONSTRAINT chk_llm_staging_confidence   CHECK (confidence BETWEEN 0.0 AND 1.0),
    CONSTRAINT chk_llm_staging_status       CHECK (object_status IN ('PendingReview', 'Approved', 'Rejected'))
);

COMMENT ON TABLE audit_core.crs_llm_template_staging IS
    'LLM-suggested CRS comment templates pending human review. '
    'Populated automatically by Tier 3 classifier. '
    'Approved rows are promoted to audit_core.crs_comment_template manually. '
    'crs_comment_template itself is read-only (manual entries only).';

COMMENT ON COLUMN audit_core.crs_llm_template_staging.template_hash IS
    'MD5 of lower(trim(template_text)) — unique deduplication key matching Tier 1 lookup.';
COMMENT ON COLUMN audit_core.crs_llm_template_staging.suggested_category IS
    'CRS category suggested by LLM (e.g. CRS-C08). Not trusted until Approved.';
COMMENT ON COLUMN audit_core.crs_llm_template_staging.occurrence_count IS
    'How many times this pattern was returned by LLM across classification runs.';
COMMENT ON COLUMN audit_core.crs_llm_template_staging.object_status IS
    'PendingReview = awaiting human decision | Approved = promoted to reference table | Rejected = discarded.';

CREATE INDEX IF NOT EXISTS idx_llm_staging_status
    ON audit_core.crs_llm_template_staging (object_status);

CREATE INDEX IF NOT EXISTS idx_llm_staging_category
    ON audit_core.crs_llm_template_staging (suggested_category);

COMMIT;


-- =============================================================================
-- VERIFICATION QUERIES (run manually after applying)
-- =============================================================================

/*
-- 1. Table exists with correct structure:
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'audit_core'
  AND table_name = 'crs_llm_template_staging'
ORDER BY ordinal_position;

-- 2. Constraints in place:
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'audit_core.crs_llm_template_staging'::regclass;

-- 3. Table is empty (populated during classification runs):
SELECT COUNT(*) FROM audit_core.crs_llm_template_staging;
-- Expected: 0
*/
