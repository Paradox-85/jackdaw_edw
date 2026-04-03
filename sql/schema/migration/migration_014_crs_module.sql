/*
migration_012_crs_module.sql

Purpose:
  CRS (Comment Review Sheet) module — Phase 1 schema.
  4 tables in audit_core for managing customer comment processing.

Tables:
  1. audit_core.crs_comment          — main storage (SCD2, FK → project_core.tag + document)
  2. audit_core.crs_validation_query — registry of SQL validation queries (seeded)
  3. audit_core.crs_comment_validation — M2M: comment ↔ validation_query (filled in Phase 2)
  4. audit_core.crs_comment_audit    — SCD Type 2 audit trail (full JSONB snapshot per change)

Safety:
  All CREATE TABLE IF NOT EXISTS — idempotent, safe to re-run.

Changes:
  2026-03-26 — Initial implementation (Phase 1).

Fixes applied vs prompts/crs_module/migration_012_crs_module_revised.sql:
  ✅ FK schema: project_core.document / project_core.tag (not projectcore.*)
  ✅ Column naming: object_status (not objectstatus) — consistent with project convention
  ✅ Seed queries: project_core.*, ontology_core.*, correct snake_case column names
  ✅ CRS_DEFECT_IN_VALIDATION_RULES: removed AND objectstatus='Active' (column doesn't exist)
  ✅ has_parameters = true for 3 parametric seed queries
*/

-- =============================================================================
-- TABLE 1: audit_core.crs_comment
-- =============================================================================

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
    "comment_id"                   TEXT      NOT NULL UNIQUE,   -- Business key: {doc_number}#{row_hash[:8]}
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

-- Partial index for low-confidence LLM results (Phase 2 quality filtering)
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


-- =============================================================================
-- TABLE 2: audit_core.crs_validation_query
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_validation_query" (
    "id"                   UUID      NOT NULL DEFAULT gen_random_uuid(),

    "query_code"           TEXT      NOT NULL UNIQUE,
    "query_name"           TEXT      NOT NULL,
    "description"          TEXT      NULL,

    -- Link to comment classification
    "category"             TEXT      NOT NULL,
    "category_description" TEXT      NULL,

    -- SQL query to execute (supports :param placeholder syntax)
    "sql_query"            TEXT      NOT NULL,
    "expected_result"      TEXT      NULL,

    -- Parameters
    "has_parameters"       BOOLEAN   NOT NULL DEFAULT false,
    "parameter_names"      TEXT[]    NULL,

    -- Metadata
    "is_active"            BOOLEAN   NOT NULL DEFAULT true,
    "created_at"           TIMESTAMP NOT NULL DEFAULT now(),
    "updated_at"           TIMESTAMP NOT NULL DEFAULT now(),
    "created_by"           TEXT      NULL,
    "notes"                TEXT      NULL,
    "object_status"        TEXT      NOT NULL DEFAULT 'Active',

    CONSTRAINT "crs_validation_query_pkey"     PRIMARY KEY ("id"),
    CONSTRAINT "crs_validation_query_code_key" UNIQUE ("query_code"),
    CONSTRAINT "crs_query_category_check"
        CHECK ("category" IN (
            'tag_missing','property_missing','property_defect',
            'document_inactive','defect_pattern','design_clarification',
            'vendor_response','other'
        )),
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
    'Each query validates a specific aspect of the EDW data referenced in a CRS comment.';


-- =============================================================================
-- TABLE 3: audit_core.crs_comment_validation (M2M)
-- =============================================================================

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


-- =============================================================================
-- TABLE 4: audit_core.crs_comment_audit (SCD Type 2)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_audit" (
    "id"             UUID      NOT NULL DEFAULT gen_random_uuid(),
    "comment_id"     UUID      NOT NULL REFERENCES "audit_core"."crs_comment"("id") ON DELETE CASCADE,

    "change_type"    TEXT      NOT NULL CHECK ("change_type" IN ('INSERT','UPDATE','DELETE')),
    "snapshot"       JSONB     NOT NULL,   -- Full row copy at time of change
    "changed_fields" TEXT[]    NULL,       -- Array of field names that changed (UPDATE only)
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
    'Enables temporal queries: "what was the status of comment X on date Y?"';

COMMENT ON COLUMN "audit_core"."crs_comment_audit"."snapshot" IS
    'Full crs_comment row as JSONB at time of change. All columns captured.';

COMMENT ON COLUMN "audit_core"."crs_comment_audit"."changed_fields" IS
    'Array of column names that changed (for UPDATE events). NULL for INSERT/DELETE.';


-- =============================================================================
-- SEED DATA: audit_core.crs_validation_query
-- Corrected queries using actual EDW schema (project_core.*, ontology_core.*, snake_case columns)
-- =============================================================================

INSERT INTO "audit_core"."crs_validation_query"
    (query_code, query_name, category, category_description, sql_query, expected_result,
     has_parameters, parameter_names, is_active, created_by, notes)
VALUES
    (
        'CRS_TAG_EXISTS',
        'Check if tag exists in database',
        'tag_missing',
        'Comment mentions a tag that should exist in project_core.tag',
        'SELECT id, tag_name, tag_status FROM project_core.tag WHERE tag_name = :tag_name AND object_status = ''Active''',
        'PASS: returns 1+ rows. FAIL: returns 0 rows (tag not in EDW).',
        true,
        ARRAY['tag_name'],
        true,
        'system',
        'Basic tag existence check. Parametric: :tag_name'
    ),
    (
        'CRS_TAG_PROPERTY_EXISTS',
        'Check if tag property value is defined',
        'property_missing',
        'Comment indicates a property value is missing for a specific tag',
        'SELECT pv.id, pv.property_value FROM project_core.property_value pv WHERE pv.tag_id = (SELECT id FROM project_core.tag WHERE tag_name = :tag_name LIMIT 1) AND pv.property_id = (SELECT id FROM ontology_core.property WHERE code = :property_code LIMIT 1)',
        'PASS: property exists. FAIL: property not found for this tag.',
        true,
        ARRAY['tag_name', 'property_code'],
        true,
        'system',
        'Multi-parameter: :tag_name, :property_code'
    ),
    (
        'CRS_DEFECT_IN_VALIDATION_RULES',
        'Check if defect patterns exist in validation results',
        'defect_pattern',
        'Comment describes a data quality defect that may be tracked as a validation violation',
        'SELECT rule_code, COUNT(*) as violation_count FROM audit_core.validation_result WHERE rule_code LIKE ''%DEFECT%'' GROUP BY rule_code ORDER BY violation_count DESC LIMIT 10',
        'PASS: returns defect rules. FAIL: no defect rules found.',
        false,
        NULL,
        true,
        'system',
        'Non-parametric aggregation. Checks audit_core.validation_result for defect-type violations.'
    ),
    (
        'CRS_DOCUMENT_ACTIVE',
        'Check if referenced document is active',
        'document_inactive',
        'Comment references a document that may be marked inactive or not found',
        'SELECT doc_number, title, status, object_status FROM project_core.document WHERE doc_number = :doc_number',
        'PASS: document exists + object_status=Active. FAIL: not found or object_status=Inactive.',
        true,
        ARRAY['doc_number'],
        true,
        'system',
        'Validates document existence and status. Parametric: :doc_number'
    )
ON CONFLICT (query_code) DO NOTHING;


-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm after applying)
-- =============================================================================

/*
-- 1. Check 4 tables created:
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'audit_core' AND table_name LIKE 'crs_%'
ORDER BY table_name;
-- Expected: crs_comment, crs_comment_audit, crs_comment_validation, crs_validation_query

-- 2. Check seed queries (3 parametric, 1 non-parametric):
SELECT query_code, category, has_parameters
FROM audit_core.crs_validation_query
ORDER BY category;
-- Expected: 4 rows, has_parameters: true/true/false/true

-- 3. Check FK references point to correct schemas:
SELECT
    tc.constraint_name,
    kcu.column_name,
    ccu.table_schema AS foreign_schema,
    ccu.table_name AS foreign_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_schema = 'audit_core'
  AND tc.table_name = 'crs_comment'
  AND tc.constraint_type = 'FOREIGN KEY';
-- Expected: doc_id → project_core.document, tag_id → project_core.tag

-- 4. Test CHECK constraint enforcement:
INSERT INTO audit_core.crs_comment
    (doc_number, comment_id, group_comment, comment, status, object_status, crs_file_path, source_file)
VALUES ('TEST', 'test#check01', 'test', 'test', 'INVALID_STATUS', 'Active', '/tmp', 'test.xlsx');
-- Expected: ERROR: violates check constraint "crs_comment_status_check"
ROLLBACK;

-- 5. Test valid insert:
INSERT INTO audit_core.crs_comment
    (doc_number, comment_id, group_comment, comment, status, object_status, crs_file_path, source_file)
VALUES ('JDAW-TEST', 'test#check02', 'Test group comment', 'Test detail', 'RECEIVED', 'Active', '/tmp/test', 'test.xlsx');
SELECT comment_id, status, object_status FROM audit_core.crs_comment WHERE doc_number = 'JDAW-TEST';
DELETE FROM audit_core.crs_comment WHERE doc_number = 'JDAW-TEST';
*/
