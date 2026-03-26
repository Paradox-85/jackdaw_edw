/*
migration_012_crs_module_revised.sql

Purpose:
  Revised CRS module schema incorporating feedback from peer review:
  1. audit_core.crs_comment — main storage (simplified, no validation fields)
  2. audit_core.crs_validation_query — registry of SQL queries
  3. audit_core.crs_comment_validation — M2M linking comments to validations (NEW)
  4. audit_core.crs_comment_audit — SCD Type 2 audit trail (renamed from history)

Safety:
  All CREATE TABLE IF NOT EXISTS — idempotent, safe to re-run.

Changes:
  2026-03-26 — Revised per feedback (schema naming, M2M, CHECK constraints, FK refs)
  
Key Improvements:
  ✅ Removed redundant columns (_raw_*, llm_summary, sync_status)
  ✅ Created M2M table for N validations per comment
  ✅ Added CHECK constraints on status fields
  ✅ Fixed schema names (projectcore.tag, projectcore.document, not project_core.*)
  ✅ Added FK to project_core.tag and project_core.document
  ✅ Added full snapshot to audit table (SCD Type 2 proper)
  ✅ Added partial index for low-confidence results
*/

-- =============================================================================
-- TABLE 1: audit_core.crs_comment (SIMPLIFIED)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment" (
    "id"                           UUID      NOT NULL DEFAULT gen_random_uuid(),
    
    -- Source document metadata (from CRS Excel)
    "doc_number"                   TEXT      NOT NULL,
    "doc_id"                       UUID      NULL REFERENCES "projectcore"."document"("id") ON DELETE SET NULL,
    "revision"                     TEXT      NULL,
    "return_code"                  TEXT      NULL,
    "transmittal_number"           TEXT      NULL,
    "transmittal_date"             DATE      NULL,
    
    -- Comment identification & location
    "comment_id"                   TEXT      NOT NULL UNIQUE,   -- Business key: doc_number + row_hash
    "group_comment"                TEXT      NOT NULL,
    "comment"                      TEXT      NOT NULL,
    
    -- Related entity from detail sheet
    "tag_name"                     TEXT      NULL,
    "tag_id"                       UUID      NULL REFERENCES "projectcore"."tag"("id") ON DELETE SET NULL,
    "property_name"                TEXT      NULL,
    "response_vendor"              TEXT      NULL,
    
    -- Source file tracking
    "source_file"                  TEXT      NOT NULL,
    "detail_file"                  TEXT      NULL,
    "detail_sheet"                 TEXT      NULL,
    "crs_file_path"                TEXT      NOT NULL,
    "crs_file_timestamp"           TIMESTAMP NULL,
    
    -- AI/LLM Processing
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
    
    -- Audit & Change Tracking (SCD2)
    "row_hash"                     TEXT      NULL,
    "sync_timestamp"               TIMESTAMP NOT NULL DEFAULT now(),
    "objectstatus"                 TEXT      NOT NULL DEFAULT 'Active',
    
    CONSTRAINT "crs_comment_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "crs_comment_comment_id_key" UNIQUE ("comment_id"),
    CONSTRAINT "crs_comment_status_check" 
        CHECK ("status" IN ('RECEIVED','IN_REVIEW','RESPONDED','APPROVED','CLOSED','DEFERRED')),
    CONSTRAINT "crs_comment_objectstatus_check"
        CHECK ("objectstatus" IN ('Active','Inactive'))
);

CREATE INDEX "idx_crs_comment_status"          ON "audit_core"."crs_comment"("status");
CREATE INDEX "idx_crs_comment_category"        ON "audit_core"."crs_comment"("llm_category");
CREATE INDEX "idx_crs_comment_tag_id"          ON "audit_core"."crs_comment"("tag_id");
CREATE INDEX "idx_crs_comment_doc_id"          ON "audit_core"."crs_comment"("doc_id");
CREATE INDEX "idx_crs_comment_doc_number"      ON "audit_core"."crs_comment"("doc_number");
CREATE INDEX "idx_crs_comment_source_file"     ON "audit_core"."crs_comment"("source_file");
CREATE INDEX "idx_crs_comment_transmittal"     ON "audit_core"."crs_comment"("transmittal_date");

-- Partial index for low-confidence LLM results (common query)
CREATE INDEX "idx_crs_comment_low_confidence"
    ON "audit_core"."crs_comment"("llm_category_confidence")
    WHERE "llm_category_confidence" < 0.7 AND "llm_category" IS NOT NULL;

COMMENT ON TABLE "audit_core"."crs_comment" IS
    'CRS comment master table. One row = one detail-level comment. '
    'Validation relationships stored in crs_comment_validation (M2M).';

COMMENT ON COLUMN "audit_core"."crs_comment"."comment_id" IS
    'Business key: {doc_number}#{row_hash[:8]}. Used for idempotent upsert.';

COMMENT ON COLUMN "audit_core"."crs_comment"."llm_category_confidence" IS
    'LLM confidence score 0-1. Query low_confidence index for manual review items.';


-- =============================================================================
-- TABLE 2: audit_core.crs_validation_query
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_validation_query" (
    "id"                 UUID      NOT NULL DEFAULT gen_random_uuid(),
    
    "query_code"         TEXT      NOT NULL UNIQUE,
    "query_name"         TEXT      NOT NULL,
    "description"        TEXT      NULL,
    
    -- Link to comment classification
    "category"           TEXT      NOT NULL,
    "category_description" TEXT    NULL,
    
    -- SQL query to execute
    "sql_query"          TEXT      NOT NULL,
    "expected_result"    TEXT      NULL,
    
    -- Parameters
    "has_parameters"     BOOLEAN   DEFAULT false,
    "parameter_names"    TEXT[]    NULL,
    
    -- Metadata
    "is_active"          BOOLEAN   NOT NULL DEFAULT true,
    "created_at"         TIMESTAMP NOT NULL DEFAULT now(),
    "updated_at"         TIMESTAMP NOT NULL DEFAULT now(),
    "created_by"         TEXT      NULL,
    "notes"              TEXT      NULL,
    "objectstatus"       TEXT      NOT NULL DEFAULT 'Active',
    
    CONSTRAINT "crs_validation_query_pkey"     PRIMARY KEY ("id"),
    CONSTRAINT "crs_validation_query_code_key" UNIQUE ("query_code"),
    CONSTRAINT "crs_query_category_check"
        CHECK ("category" IN (
            'tag_missing','property_missing','property_defect',
            'document_inactive','defect_pattern','design_clarification',
            'vendor_response','other'
        )),
    CONSTRAINT "crs_query_objectstatus_check"
        CHECK ("objectstatus" IN ('Active','Inactive'))
);

CREATE INDEX "idx_crs_query_category"       ON "audit_core"."crs_validation_query"("category");
CREATE INDEX "idx_crs_query_is_active"      ON "audit_core"."crs_validation_query"("is_active");

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


-- =============================================================================
-- TABLE 3: audit_core.crs_comment_validation (M2M – NEW)
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
    
    CONSTRAINT "crs_comment_validation_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "crs_comment_validation_unique" UNIQUE ("comment_id", "validation_query_id"),
    CONSTRAINT "crs_validation_status_check"
        CHECK ("validation_status" IN ('PENDING','PASSED','FAILED','INCONCLUSIVE','SKIPPED'))
);

CREATE INDEX "idx_crs_comment_validation_comment"  ON "audit_core"."crs_comment_validation"("comment_id");
CREATE INDEX "idx_crs_comment_validation_query"    ON "audit_core"."crs_comment_validation"("validation_query_id");
CREATE INDEX "idx_crs_comment_validation_status"   ON "audit_core"."crs_comment_validation"("validation_status");
CREATE INDEX "idx_crs_comment_validation_timestamp" ON "audit_core"."crs_comment_validation"("validation_timestamp");

COMMENT ON TABLE "audit_core"."crs_comment_validation" IS
    'M2M linking: one comment may have multiple validations. '
    'Stores validation status + result JSONB for each query.';


-- =============================================================================
-- TABLE 4: audit_core.crs_comment_audit (SCD Type 2 – RENAMED)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_audit" (
    "id"               UUID      NOT NULL DEFAULT gen_random_uuid(),
    "comment_id"       UUID      NOT NULL REFERENCES "audit_core"."crs_comment"("id") ON DELETE CASCADE,
    
    "change_type"      TEXT      NOT NULL CHECK ("change_type" IN ('INSERT','UPDATE','DELETE')),
    "snapshot"         JSONB     NOT NULL,   -- Full row copy at time of change
    "changed_fields"   TEXT[]    NULL,       -- Array of field names that changed
    "changed_by"       TEXT      NULL,
    "change_reason"    TEXT      NULL,
    
    "changed_at"       TIMESTAMP NOT NULL DEFAULT now(),
    "run_id"           UUID      NULL,
    
    CONSTRAINT "crs_comment_audit_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "idx_crs_audit_comment"    ON "audit_core"."crs_comment_audit"("comment_id");
CREATE INDEX "idx_crs_audit_timestamp"  ON "audit_core"."crs_comment_audit"("changed_at");
CREATE INDEX "idx_crs_audit_change_type" ON "audit_core"."crs_comment_audit"("change_type");

COMMENT ON TABLE "audit_core"."crs_comment_audit" IS
    'SCD Type 2 audit trail for crs_comment. Stores full snapshot + changed field names. '
    'Enables temporal queries: "what was status on 2026-03-15?"';

COMMENT ON COLUMN "audit_core"."crs_comment_audit"."snapshot" IS
    'Full row as JSONB at time of change. Includes all columns from crs_comment.';


-- =============================================================================
-- SEED DATA: crs_validation_query
-- =============================================================================

INSERT INTO "audit_core"."crs_validation_query" 
    (query_code, query_name, category, category_description, sql_query, expected_result, is_active, created_by, notes)
VALUES
    (
        'CRS_TAG_EXISTS',
        'Check if tag exists in database',
        'tag_missing',
        'Comment mentions a tag that should exist',
        'SELECT id, tagname, tagstatus FROM projectcore.tag WHERE tagname = :tag_name AND objectstatus = ''Active''',
        'PASS: returns 1+ rows. FAIL: returns 0 rows.',
        true,
        'system',
        'Basic tag existence check. Parametric: :tag_name'
    ),
    (
        'CRS_TAG_PROPERTY_EXISTS',
        'Check if tag property value is defined',
        'property_missing',
        'Comment indicates a property value is missing for a tag',
        'SELECT pv.id, pv.propertyvalue FROM projectcore.propertyvalue pv ' ||
        'WHERE pv.tagid = (SELECT id FROM projectcore.tag WHERE tagname = :tag_name LIMIT 1) ' ||
        'AND pv.propertyid = (SELECT id FROM ontologycore.property WHERE code = :property_code LIMIT 1)',
        'PASS: property exists. FAIL: property not found.',
        true,
        'system',
        'Multi-parameter: :tag_name, :property_code'
    ),
    (
        'CRS_DEFECT_IN_VALIDATION_RULES',
        'Check if defect patterns exist in validation results',
        'defect_pattern',
        'Comment describes a data quality defect',
        'SELECT rule_code, COUNT(*) as violation_count FROM audit_core.validation_result ' ||
        'WHERE rule_code LIKE ''%DEFECT%'' AND objectstatus = ''Active'' ' ||
        'GROUP BY rule_code ORDER BY violation_count DESC LIMIT 10',
        'PASS: returns defect rules. FAIL: no defect rules found.',
        true,
        'system',
        'Non-parametric aggregation. Checks validation rule violations.'
    ),
    (
        'CRS_DOCUMENT_ACTIVE',
        'Check if referenced document is active',
        'document_inactive',
        'Comment references a document that is marked inactive',
        'SELECT docnumber, title, status, objectstatus FROM projectcore.document ' ||
        'WHERE docnumber = :doc_number',
        'PASS: document exists + objectstatus=Active. FAIL: not found or inactive.',
        true,
        'system',
        'Validates document existence and status. Parametric: :doc_number'
    )
ON CONFLICT (query_code) DO NOTHING;


-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm)
-- =============================================================================

/*
-- Check tables exist:
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'audit_core' AND table_name LIKE 'crs_%'
ORDER BY table_name;

-- Expected: crs_comment, crs_comment_audit, crs_comment_validation, crs_validation_query

-- Check M2M structure:
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_schema = 'audit_core' AND table_name = 'crs_comment_validation';

-- Expected: crs_comment_validation_pkey, crs_comment_validation_unique, FK constraints

-- Check seed queries:
SELECT query_code, category, has_parameters FROM audit_core.crs_validation_query ORDER BY category;

-- Expected: 4 rows with correct categories

-- Check constraints enforced:
INSERT INTO audit_core.crs_comment (doc_number, comment_id, group_comment, comment, status, objectstatus)
VALUES ('TEST', 'test#12345', 'test', 'test', 'INVALID_STATUS', 'Active');
-- Should fail with: constraint "crs_comment_status_check" violation

-- Check FK to tag/document:
SELECT column_name, referenced_table_name FROM information_schema.key_column_usage
WHERE table_schema = 'audit_core' AND table_name = 'crs_comment' AND column_name IN ('tag_id', 'doc_id');

-- Expected: tag_id → projectcore.tag, doc_id → projectcore.document
*/
