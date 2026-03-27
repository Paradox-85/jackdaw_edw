-- =============================================================================
-- migration_017_crs_templates.sql
--
-- Purpose:
--   Phase 2 CRS Cascade Classifier — template knowledge base.
--   1. Create audit_core.crs_comment_template (auto-growing KB from Tier 3 LLM)
--   2. Add classification_tier + template_id columns to audit_core.crs_comment
--
-- Applies after: migration_016_crs_phase2.sql
-- =============================================================================

BEGIN;

-- =============================================================================
-- Part A: Knowledge base table — crs_comment_template
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_core.crs_comment_template (
    id                UUID        NOT NULL DEFAULT gen_random_uuid(),
    template_text     TEXT        NOT NULL,
    template_hash     TEXT        NOT NULL,
    category          TEXT        NOT NULL,
    check_type        TEXT        NULL,
    response_template TEXT        NULL,
    source            TEXT        NOT NULL DEFAULT 'llm',
    confidence        REAL        NOT NULL DEFAULT 1.0,
    usage_count       INTEGER     NOT NULL DEFAULT 0,
    last_used_at      TIMESTAMP   NOT NULL DEFAULT now(),
    created_at        TIMESTAMP   NOT NULL DEFAULT now(),
    object_status     TEXT        NOT NULL DEFAULT 'Active',

    CONSTRAINT crs_comment_template_pkey       PRIMARY KEY (id),
    CONSTRAINT crs_comment_template_hash_key   UNIQUE      (template_hash),
    CONSTRAINT chk_crs_template_source         CHECK (source IN ('llm', 'manual', 'rule')),
    CONSTRAINT chk_crs_template_confidence     CHECK (confidence BETWEEN 0.0 AND 1.0),
    CONSTRAINT chk_crs_template_object_status  CHECK (object_status IN ('Active', 'Inactive'))
);

COMMENT ON TABLE audit_core.crs_comment_template IS
    'Accumulating knowledge base of normalised CRS comment patterns and their '
    'classifications. Auto-populated from Tier 3 LLM results. Tier 1 looks up '
    'this table for exact/fuzzy matching before calling the LLM.';

COMMENT ON COLUMN audit_core.crs_comment_template.template_text IS
    'Normalised comment text (tag names, doc numbers, digits replaced with placeholders). '
    'Used for fuzzy matching in Tier 1.';
COMMENT ON COLUMN audit_core.crs_comment_template.template_hash IS
    'MD5 of lower(trim(template_text)). Used for O(1) exact matching in Tier 1.';
COMMENT ON COLUMN audit_core.crs_comment_template.category IS
    'Classification category: MISSING_DOCUMENT_LINK, TAG_NOT_FOUND, MISSING_PROPERTY, etc.';
COMMENT ON COLUMN audit_core.crs_comment_template.check_type IS
    'Validation query type: TAG_EXISTS, TAG_HAS_DOCUMENT, TAG_HAS_PROPERTY, TAG_FROM_TO_LINK.';
COMMENT ON COLUMN audit_core.crs_comment_template.response_template IS
    'Templated response string with {tag_name}, {property_name} placeholders.';
COMMENT ON COLUMN audit_core.crs_comment_template.source IS
    'Origin: llm (auto-populated from Tier 3) | manual (curated) | rule (from Tier 2).';
COMMENT ON COLUMN audit_core.crs_comment_template.confidence IS
    '1.0 for exact matches; fuzzy ratio (0.92–1.0) for approximate matches.';
COMMENT ON COLUMN audit_core.crs_comment_template.usage_count IS
    'How many times this template has been matched. Incremented on each Tier 1 hit.';

CREATE INDEX IF NOT EXISTS idx_crs_template_category
    ON audit_core.crs_comment_template(category)
    WHERE object_status = 'Active';

CREATE INDEX IF NOT EXISTS idx_crs_template_hash
    ON audit_core.crs_comment_template(template_hash)
    WHERE object_status = 'Active';


-- =============================================================================
-- Part B: Extend audit_core.crs_comment with classification columns
-- =============================================================================

ALTER TABLE audit_core.crs_comment
    ADD COLUMN IF NOT EXISTS classification_tier SMALLINT NULL,
    ADD COLUMN IF NOT EXISTS template_id         UUID     NULL;

-- FK constraint (separate statement — cannot combine with ADD COLUMN IF NOT EXISTS)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'crs_comment_template_id_fkey'
          AND conrelid = 'audit_core.crs_comment'::regclass
    ) THEN
        ALTER TABLE audit_core.crs_comment
            ADD CONSTRAINT crs_comment_template_id_fkey
            FOREIGN KEY (template_id)
            REFERENCES audit_core.crs_comment_template(id)
            ON DELETE SET NULL;
    END IF;
END $$;

COMMENT ON COLUMN audit_core.crs_comment.classification_tier IS
    '0=Skipped (Tier 0 pre-filter), 1=Template matched (Tier 1 KB), '
    '2=Keyword rule (Tier 2 regex/sheet), 3=LLM classified (Tier 3 Qwen3). '
    'NULL = not yet classified (status=RECEIVED).';

COMMENT ON COLUMN audit_core.crs_comment.template_id IS
    'FK to audit_core.crs_comment_template. Set when classification_tier=1 '
    '(template match). NULL for all other tiers.';

-- Partial index: only populated rows
CREATE INDEX IF NOT EXISTS idx_crs_comment_classification_tier
    ON audit_core.crs_comment(classification_tier)
    WHERE classification_tier IS NOT NULL;

COMMIT;


-- =============================================================================
-- VERIFICATION QUERIES (run manually after applying)
-- =============================================================================

/*
-- 1. Template table exists:
SELECT COUNT(*) FROM audit_core.crs_comment_template;
-- Expected: 0 (empty, populated during classification runs)

-- 2. New columns on crs_comment:
SELECT attname, format_type(atttypid, atttypmod)
FROM pg_attribute
WHERE attrelid = 'audit_core.crs_comment'::regclass
  AND attname IN ('classification_tier', 'template_id')
  AND NOT attisdropped;
-- Expected: classification_tier | smallint, template_id | uuid

-- 3. FK constraint:
SELECT conname FROM pg_constraint
WHERE conname = 'crs_comment_template_id_fkey';
*/
