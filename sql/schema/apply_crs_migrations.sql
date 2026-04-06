-- =============================================================================
-- Apply CRS Migrations
--
-- Purpose: Apply all missing CRS (Comment Resolution System) migrations
--          to bring the database schema in sync with schema.sql
--
-- Applies migrations:
--   1. migration_014_crs_module.sql — base CRS tables
--   2. migration_015_crs_add_document_number.sql — document_number column
--   3. migration_016_crs_add_from_to_tag.sql — from_tag/to_tag columns
--   4. migration_017_crs_phase2.sql — views + validation queries
--   5. migration_018_crs_templates.sql — template table + classification tier
--   6. migration_021_add_crs_llm_staging.sql — LLM staging table
--
-- All migrations use IF NOT EXISTS / IF EXISTS — idempotent, safe to re-run
-- =============================================================================

-- =============================================================================
-- MIGRATION 014: CRS Module — Phase 1 tables
-- =============================================================================

BEGIN;

-- TABLE 1: audit_core.crs_comment
CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment" (
    "id"                           UUID      NOT NULL DEFAULT gen_random_uuid(),

    -- Source document metadata (from CRS Excel header)
    "doc_number"                   TEXT      NOT NULL,
    "doc_id"                       UUID      NULL REFERENCES "project_core"."document"("id") ON DELETE SET NULL,
    "revision"                     TEXT      NULL,
    "return_code"                  TEXT      NULL,
    "transmittal_number"           TEXT      NULL,
    "transmittal_date"             DATE      NULL,

    -- Comment identification & location
    "comment_id"                   TEXT      NOT NULL UNIQUE,
    "group_comment"                TEXT      NOT NULL,
    "comment"                      TEXT      NOT NULL,

    -- Related entity from detail sheet
    "tag_name"                     TEXT      NULL,
    "tag_id"                       UUID      NULL REFERENCES "project_core"."tag"("id") ON DELETE SET NULL,
    "property_name"                TEXT      NULL,
    "response_vendor"              TEXT      NULL,

    -- Source file tracking
    "source_file"                  TEXT      NOT NULL,
    "detail_file"                  TEXT      NULL,
    "detail_sheet"                 TEXT      NULL,
    "crs_file_path"                TEXT      NOT NULL,
    "crs_file_timestamp"           TIMESTAMP NULL,

    -- AI/LLM Processing (Phase 2)
    "llm_category"                 TEXT      NULL,
    "llm_category_confidence"      REAL      NULL CHECK ("llm_category_confidence" >= 0.0 AND "llm_category_confidence" <= 1.0),
    "llm_response"                 TEXT      NULL,
    "llm_response_timestamp"       TIMESTAMP NULL,
    "llm_model_used"               TEXT      NULL,

    -- Response & Resolution
    "status"                       TEXT      NOT NULL DEFAULT 'RECEIVED',
    "formal_response"              TEXT      NULL,
    "formal_response_rationale"    TEXT      NULL,
    "response_author"              TEXT      NULL,
    "response_approval_date"       DATE      NULL,
    "response_review_notes"        TEXT      NULL,

    -- SCD2 change tracking
    "row_hash"                     TEXT      NULL,
    "sync_timestamp"               TIMESTAMP NOT NULL DEFAULT now(),
    "object_status"                TEXT      NOT NULL DEFAULT 'Active',

    CONSTRAINT "crs_comment_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "crs_comment_comment_id_key" UNIQUE ("comment_id"),
    CONSTRAINT "crs_comment_status_check"
        CHECK ("status" IN ('RECEIVED','IN_REVIEW','RESPONDED','APPROVED','CLOSED','DEFERRED')),
    CONSTRAINT "crs_comment_object_status_check"
        CHECK ("object_status" IN ('Active','Inactive'))
);

CREATE INDEX IF NOT EXISTS "idx_crs_comment_status"         ON "audit_core"."crs_comment"("status");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_category"       ON "audit_core"."crs_comment"("llm_category");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_tag_id"         ON "audit_core"."crs_comment"("tag_id");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_doc_id"         ON "audit_core"."crs_comment"("doc_id");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_doc_number"     ON "audit_core"."crs_comment"("doc_number");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_source_file"    ON "audit_core"."crs_comment"("source_file");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_transmittal"    ON "audit_core"."crs_comment"("transmittal_date");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_sync_timestamp" ON "audit_core"."crs_comment"("sync_timestamp");

-- Partial index for low-confidence LLM results
CREATE INDEX IF NOT EXISTS "idx_crs_comment_low_confidence"
    ON "audit_core"."crs_comment"("llm_category_confidence")
    WHERE "llm_category_confidence" < 0.7 AND "llm_category" IS NOT NULL;

COMMENT ON TABLE "audit_core"."crs_comment" IS
    'CRS comment master table. One row = one detail-level comment from CRS Excel files. '
    'Validation relationships stored in crs_comment_validation (M2M). '
    'Phase 2: LLM fields populated by classify_crs_comment task.';

COMMENT ON COLUMN "audit_core"."crs_comment"."comment_id" IS
    'Business key: {doc_number}#{row_hash[:8]}. Stable across re-runs for ON CONFLICT upsert.';

COMMENT ON COLUMN "audit_core"."crs_comment"."llm_category_confidence" IS
    'LLM confidence score 0–1. Partial index idx_crs_comment_low_confidence for values < 0.7.';

-- TABLE 2: audit_core.crs_validation_query
CREATE TABLE IF NOT EXISTS "audit_core"."crs_validation_query" (
    "id"                   UUID      NOT NULL DEFAULT gen_random_uuid(),
    "query_code"           TEXT      NOT NULL UNIQUE,
    "query_name"           TEXT      NOT NULL,
    "description"          TEXT      NULL,
    "category"             TEXT      NOT NULL,
    "category_description" TEXT      NULL,
    "sql_query"            TEXT      NOT NULL,
    "expected_result"      TEXT      NULL,
    "has_parameters"       BOOLEAN   NOT NULL DEFAULT false,
    "parameter_names"      TEXT[]    NULL,
    "is_active"            BOOLEAN   NOT NULL DEFAULT true,
    "created_at"           TIMESTAMP NOT NULL DEFAULT now(),
    "updated_at"           TIMESTAMP NOT NULL DEFAULT now(),
    "created_by"           TEXT      NULL,
    "notes"                TEXT      NULL,
    "object_status"        TEXT      NOT NULL DEFAULT 'Active',
    CONSTRAINT "crs_validation_query_pkey"     PRIMARY KEY ("id"),
    CONSTRAINT "crs_validation_query_code_key" UNIQUE ("query_code"),
    CONSTRAINT "crs_query_object_status_check"
        CHECK ("object_status" IN ('Active','Inactive'))
);

CREATE INDEX IF NOT EXISTS "idx_crs_query_category"  ON "audit_core"."crs_validation_query"("category");
CREATE INDEX IF NOT EXISTS "idx_crs_query_is_active" ON "audit_core"."crs_validation_query"("is_active");

DROP TRIGGER IF EXISTS "trg_crs_validation_query_updated_at" ON "audit_core"."crs_validation_query";

CREATE OR REPLACE FUNCTION "audit_core"."set_crs_query_updated_at"()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER "trg_crs_validation_query_updated_at"
    BEFORE UPDATE ON "audit_core"."crs_validation_query"
    FOR EACH ROW EXECUTE FUNCTION "audit_core"."set_crs_query_updated_at"();

COMMENT ON TABLE "audit_core"."crs_validation_query" IS
    'Registry of SQL validation queries used in Phase 2 CRS comment processing. '
    'Each query validates a specific aspect of EDW data referenced in a CRS comment.';

-- TABLE 3: audit_core.crs_comment_validation (M2M)
CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_validation" (
    "id"                     UUID      NOT NULL DEFAULT gen_random_uuid(),
    "comment_id"             UUID      NOT NULL REFERENCES "audit_core"."crs_comment"("id") ON DELETE CASCADE,
    "validation_query_id"    UUID      NOT NULL REFERENCES "audit_core"."crs_validation_query"("id") ON DELETE RESTRICT,
    "validation_status"      TEXT      NOT NULL DEFAULT 'PENDING',
    "validation_result_json" JSONB     NULL,
    "validation_timestamp"   TIMESTAMP NULL,
    "validation_error"       TEXT      NULL,
    "run_id"                 UUID      NULL,
    CONSTRAINT "crs_comment_validation_pkey"   PRIMARY KEY ("id"),
    CONSTRAINT "crs_comment_validation_unique" UNIQUE ("comment_id", "validation_query_id"),
    CONSTRAINT "crs_validation_status_check"
        CHECK ("validation_status" IN ('PENDING','PASSED','FAILED','INCONCLUSIVE','SKIPPED'))
);

CREATE INDEX IF NOT EXISTS "idx_crs_cv_comment"    ON "audit_core"."crs_comment_validation"("comment_id");
CREATE INDEX IF NOT EXISTS "idx_crs_cv_query"      ON "audit_core"."crs_comment_validation"("validation_query_id");
CREATE INDEX IF NOT EXISTS "idx_crs_cv_status"     ON "audit_core"."crs_comment_validation"("validation_status");
CREATE INDEX IF NOT EXISTS "idx_crs_cv_timestamp"  ON "audit_core"."crs_comment_validation"("validation_timestamp");

COMMENT ON TABLE "audit_core"."crs_comment_validation" IS
    'M2M: one comment may have multiple validation queries. '
    'Populated in Phase 2 by validate_crs_comment task. '
    'Stores validation status + result JSONB for each query execution.';

-- TABLE 4: audit_core.crs_comment_audit (SCD Type 2)
CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_audit" (
    "id"             UUID      NOT NULL DEFAULT gen_random_uuid(),
    "comment_id"     UUID      NOT NULL REFERENCES "audit_core"."crs_comment"("id") ON DELETE CASCADE,
    "change_type"    TEXT      NOT NULL CHECK ("change_type" IN ('INSERT','UPDATE','DELETE')),
    "snapshot"       JSONB     NOT NULL,
    "changed_fields" TEXT[]    NULL,
    "changed_by"     TEXT      NULL,
    "change_reason"  TEXT      NULL,
    "changed_at"     TIMESTAMP NOT NULL DEFAULT now(),
    "run_id"         UUID      NULL,
    CONSTRAINT "crs_comment_audit_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "idx_crs_audit_comment"     ON "audit_core"."crs_comment_audit"("comment_id");
CREATE INDEX IF NOT EXISTS "idx_crs_audit_changed_at"  ON "audit_core"."crs_comment_audit"("changed_at");
CREATE INDEX IF NOT EXISTS "idx_crs_audit_change_type" ON "audit_core"."crs_comment_audit"("change_type");

COMMENT ON TABLE "audit_core"."crs_comment_audit" IS
    'SCD Type 2 audit trail for crs_comment. Full JSONB snapshot + changed field list per change. '
    'Enables temporal queries: "what was the status of comment X on date Y?".';

COMMENT ON COLUMN "audit_core"."crs_comment_audit"."snapshot" IS
    'Full crs_comment row as JSONB at time of change. All columns captured.';

COMMENT ON COLUMN "audit_core"."crs_comment_audit"."changed_fields" IS
    'Array of column names that changed (for UPDATE events). NULL for INSERT/DELETE.';

COMMIT;

-- =============================================================================
-- MIGRATION 015: Add document_number column
-- =============================================================================

BEGIN;

ALTER TABLE "audit_core"."crs_comment"
    ADD COLUMN IF NOT EXISTS "document_number" TEXT NULL;

COMMENT ON COLUMN "audit_core"."crs_comment"."document_number" IS
    'Project document reference containing the tag (DOCUMENT_NUMBER column in '
    'detail sheet). Stores ''Not Applicable'' when column is absent in source. '
    'Distinct from crs_doc_number (the CRS header file number).';

-- Partial index: exclude NULL and 'Not Applicable'
CREATE INDEX IF NOT EXISTS "idx_crs_comment_document_number"
    ON "audit_core"."crs_comment"("document_number")
    WHERE "document_number" IS NOT NULL
      AND "document_number" != 'Not Applicable';

COMMIT;

-- =============================================================================
-- MIGRATION 016: Add from_tag/to_tag columns
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
-- MIGRATION 017: CRS Phase 2 — Views + Validation Queries
-- =============================================================================

BEGIN;

-- Part A: Views
CREATE OR REPLACE VIEW project_core.v_tag_with_docs AS
SELECT
    t.id, t.tag_name, t.tag_status, t.object_status,
    d.id AS document_id, d.doc_number
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id AND d.object_status = 'Active'
WHERE t.object_status = 'Active';

COMMENT ON VIEW project_core.v_tag_with_docs IS
    'Active tags with their linked documents. Excludes properties to prevent '
    'Cartesian product with v_tag_properties. Used by Tier 3 LLM verifier.';

CREATE OR REPLACE VIEW project_core.v_tag_properties AS
SELECT
    t.id, t.tag_name, t.tag_status, t.object_status,
    p.code AS property_code, p.name AS property_name,
    pv.property_value, pv.property_uom_raw
FROM project_core.tag t
LEFT JOIN project_core.property_value pv ON pv.tag_id = t.id AND pv.object_status = 'Active'
LEFT JOIN ontology_core.property p ON p.id = pv.property_id
WHERE t.object_status = 'Active';

COMMENT ON VIEW project_core.v_tag_properties IS
    'Active tags with their property values. Excludes document links to prevent '
    'Cartesian product with v_tag_with_docs. Used by Tier 3 LLM verifier.';

-- Part B: Update constraint for crs_validation_query category
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'crs_query_category_check'
          AND conrelid = 'audit_core.crs_validation_query'::regclass
    ) THEN
        ALTER TABLE audit_core.crs_validation_query
            DROP CONSTRAINT IF EXISTS crs_query_category_check;
    END IF;
END $$;

-- Part C: Seed 5 validation queries
INSERT INTO audit_core.crs_validation_query
    (id, query_code, query_name, description, category, sql_query,
     expected_result, has_parameters, parameter_names, is_active,
     created_at, updated_at, created_by, object_status)
VALUES
(
    gen_random_uuid(), 'TAG_EXISTS', 'Tag Exists in EDW',
    'Verify that a tag with given tag_name exists in project_core.tag with Active status.',
    'tag_existence',
    'SELECT id, tag_name, tag_status, object_status
     FROM project_core.tag
     WHERE tag_name = :tag_name AND object_status = ''Active''
     LIMIT 1',
    'One row if tag exists and is active; zero rows if not found or inactive.',
    true, ARRAY['tag_name'], true, now(), now(), 'migration_016', 'Active'
),
(
    gen_random_uuid(), 'TAG_HAS_DOCUMENT', 'Tag Has Document Link',
    'Verify that a tag has at least one active document link in mapping.tag_document.',
    'document_link',
    'SELECT t.tag_name, d.doc_number, td.mapping_status
     FROM project_core.tag t
     JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = ''Active''
     JOIN project_core.document d ON d.id = td.document_id AND d.object_status = ''Active''
     WHERE t.tag_name = :tag_name AND t.object_status = ''Active''
     LIMIT 10',
    'Rows if tag has document links; empty if no documents linked.',
    true, ARRAY['tag_name'], true, now(), now(), 'migration_016', 'Active'
),
(
    gen_random_uuid(), 'TAG_HAS_PROPERTY', 'Tag Has Property Value',
    'Verify that a tag has a specific property defined (non-empty value).',
    'property_check',
    'SELECT t.tag_name, p.code AS property_code, p.name AS property_name,
            pv.property_value, pv.property_uom_raw
     FROM project_core.tag t
     JOIN project_core.property_value pv ON pv.tag_id = t.id AND pv.object_status = ''Active''
     JOIN ontology_core.property p ON p.id = pv.property_id
     WHERE t.tag_name = :tag_name AND t.object_status = ''Active''
       AND (p.code = :property_code OR p.name ILIKE :property_name)
     LIMIT 5',
    'Rows with property value if set; empty if property is missing or blank.',
    true, ARRAY['tag_name', 'property_code', 'property_name'],
    true, now(), now(), 'migration_016', 'Active'
),
(
    gen_random_uuid(), 'TAG_FROM_TO_LINK', 'Tag FROM/TO Directional Link',
    'Verify that FROM_TAG and TO_TAG both exist and are active tags in EDW.',
    'tag_relationship',
    'SELECT ft.tag_name AS from_tag, ft.tag_status AS from_status,
            tt.tag_name AS to_tag, tt.tag_status AS to_status
     FROM project_core.tag ft
     CROSS JOIN project_core.tag tt
     WHERE ft.tag_name = :from_tag AND tt.tag_name = :to_tag
       AND ft.object_status = ''Active'' AND tt.object_status = ''Active''',
    'One row if both tags exist and are active; empty if either is missing.',
    true, ARRAY['from_tag', 'to_tag'],
    true, now(), now(), 'migration_016', 'Active'
),
(
    gen_random_uuid(), 'TAGS_WITHOUT_PROPERTIES', 'Tags Without Any Properties',
    'Bulk check: count of active tags that have no property values at all.',
    'bulk_check',
    'SELECT COUNT(*) AS tags_without_properties
     FROM project_core.tag t
     WHERE t.object_status = ''Active''
       AND NOT EXISTS (
           SELECT 1 FROM project_core.property_value pv
           WHERE pv.tag_id = t.id AND pv.object_status = ''Active''
       )',
    'Integer count. Zero means all active tags have at least one property.',
    false, ARRAY[]::text[],
    true, now(), now(), 'migration_016', 'Active'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name      = EXCLUDED.query_name,
    description     = EXCLUDED.description,
    category        = EXCLUDED.category,
    sql_query       = EXCLUDED.sql_query,
    expected_result = EXCLUDED.expected_result,
    has_parameters  = EXCLUDED.has_parameters,
    parameter_names = EXCLUDED.parameter_names,
    is_active       = EXCLUDED.is_active,
    updated_at      = now(),
    object_status   = EXCLUDED.object_status;

COMMIT;

-- =============================================================================
-- MIGRATION 018: CRS Templates + Classification Tier
-- =============================================================================

BEGIN;

-- Part A: Knowledge base table
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

CREATE INDEX IF NOT EXISTS idx_crs_template_category
    ON audit_core.crs_comment_template(category)
    WHERE object_status = 'Active';

CREATE INDEX IF NOT EXISTS idx_crs_template_hash
    ON audit_core.crs_comment_template(template_hash)
    WHERE object_status = 'Active';

COMMENT ON TABLE audit_core.crs_comment_template IS
    'Accumulating knowledge base of normalised CRS comment patterns and their '
    'classifications. Auto-populated from Tier 3 LLM results. Tier 1 looks up '
    'this table for exact/fuzzy matching before calling LLM.';

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

-- Part B: Extend audit_core.crs_comment with classification columns
ALTER TABLE audit_core.crs_comment
    ADD COLUMN IF NOT EXISTS classification_tier SMALLINT NULL,
    ADD COLUMN IF NOT EXISTS template_id         UUID     NULL;

-- FK constraint (separate statement)
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
-- MIGRATION 021: CRS LLM Staging Table
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
-- 1. Check all CRS tables created:
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'audit_core' AND table_name LIKE 'crs_%'
ORDER BY table_name;
-- Expected: crs_comment, crs_comment_audit, crs_comment_validation,
--            crs_validation_query, crs_comment_template, crs_llm_template_staging

-- 2. Check views created:
SELECT viewname FROM information_schema.views
WHERE schemaname IN ('project_core')
ORDER BY viewname;
-- Expected: v_tag_with_docs, v_tag_properties

-- 3. Test table access:
SELECT COUNT(*) FROM audit_core.crs_comment;
SELECT COUNT(*) FROM audit_core.crs_validation_query;
SELECT COUNT(*) FROM audit_core.crs_comment_template;
SELECT COUNT(*) FROM audit_core.crs_llm_template_staging;
*/
