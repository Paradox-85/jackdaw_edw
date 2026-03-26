/*
migration_011_crs_module.sql

Purpose:
  Create CRS (Customer Request System) module in audit_core schema:
  1. audit_core.crs_comment — main storage for customer comments
  2. audit_core.crs_validation_query — registry of SQL queries linked to comment categories
  3. audit_core.crs_comment_history — SCD Type 2 change tracking

Design:
  - crs_comment: stores parsed CRS Excel data + AI processing results
  - crs_validation_query: links comment categories to validation SQL queries
  - crs_comment_history: audit trail of all changes (INSERT/UPDATE/DELETE)

Safety:
  All CREATE TABLE IF NOT EXISTS — idempotent, safe to re-run.

Changes:
  2026-03-26 — Initial implementation for CRS module (Phase 1)
*/

-- =============================================================================
-- TABLE 1: audit_core.crs_comment
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment" (
    "id"                           UUID      NOT NULL DEFAULT gen_random_uuid(),
    
    -- Source document metadata (from CRS Excel)
    "doc_number"                   TEXT      NOT NULL,          -- DOC_NUMBER
    "revision"                     TEXT      NULL,              -- REVISION
    "return_code"                  TEXT      NULL,              -- RETURN_CODE
    "transmittal_number"           TEXT      NULL,              -- TRANSMITTAL_NUMBER
    "transmittal_date"             DATE      NULL,              -- TRANSMITTAL_DATE (parsed)
    
    -- Comment identification & location
    "comment_id"                   TEXT      NOT NULL UNIQUE,   -- Generated: doc_number + row_hash
    "group_comment"                TEXT      NOT NULL,          -- GROUP_COMMENT (high-level topic)
    "comment"                      TEXT      NOT NULL,          -- COMMENT (detail row text)
    
    -- Related entity from detail sheet
    "tag_name"                     TEXT      NULL,              -- TAG_NAME (if found)
    "property_name"                TEXT      NULL,              -- PROPERTY_NAME (if found)
    "response_vendor"              TEXT      NULL,              -- RESPONSE (vendor's reply from main file)
    
    -- Source file tracking
    "source_file"                  TEXT      NOT NULL,          -- SOURCE_FILE (DOC_COMMENT_* filename)
    "detail_file"                  TEXT      NULL,              -- DETAIL_FILE (JDAW_* filename)
    "detail_sheet"                 TEXT      NULL,              -- DETAIL_SHEET (sheet name in detail file)
    "crs_file_path"                TEXT      NOT NULL,          -- Full path to parsed CRS file
    "crs_file_timestamp"           TIMESTAMP NULL,              -- File modification time
    
    -- AI/LLM Processing
    "llm_category"                 TEXT      NULL,              -- Auto-classified by LLM (e.g., 'defect', 'clarification')
    "llm_category_confidence"      REAL      NULL,              -- Confidence 0-1
    "llm_summary"                  TEXT      NULL,              -- LLM-generated summary
    "llm_response"                 TEXT      NULL,              -- Initial LLM response
    "llm_response_timestamp"       TIMESTAMP NULL,              -- When response was generated
    "llm_model_used"               TEXT      NULL,              -- Model name (e.g., 'ollama-mistral')
    
    -- Validation & Compliance
    "applicable_validation_query_id" UUID    NULL REFERENCES "audit_core"."crs_validation_query"("id"),
    "validation_status"            TEXT      NULL,              -- PENDING|PASSED|FAILED|INCONCLUSIVE|NA
    "validation_result_json"       JSONB     NULL,              -- Query execution result snapshot
    "validation_timestamp"         TIMESTAMP NULL,              -- When validation was last run
    "validation_error_message"     TEXT      NULL,              -- If validation failed
    
    -- Response & Resolution
    "status"                       TEXT      NOT NULL DEFAULT 'RECEIVED',  
                                   -- RECEIVED|IN_REVIEW|RESPONDED|APPROVED|CLOSED|DEFERRED
    "formal_response"              TEXT      NULL,              -- Final formal reply to customer
    "formal_response_rationale"    TEXT      NULL,              -- Why we gave this response (based on validation)
    "response_author"              TEXT      NULL,              -- Who authored the formal response
    "response_approval_date"       DATE      NULL,              -- Approval signature date
    "response_review_notes"        TEXT      NULL,              -- Review comments
    
    -- Audit & Change Tracking
    "row_hash"                     TEXT      NULL,              -- MD5 hash for SCD2 change detection
    "sync_status"                  TEXT      NOT NULL DEFAULT 'SYNCED',  -- SYNCED|MODIFIED|ERROR
    "sync_timestamp"               TIMESTAMP NOT NULL DEFAULT now(),
    "object_status"                TEXT      NOT NULL DEFAULT 'Active',   -- Active|Inactive
    
    -- Raw data preservation (for debugging)
    "_raw_doc_number"              TEXT      NULL,
    "_raw_revision"                TEXT      NULL,
    "_raw_transmittal_date"        TEXT      NULL,
    "_raw_tag_name"                TEXT      NULL,
    "_raw_property_name"           TEXT      NULL,
    "_raw_group_comment"           TEXT      NULL,
    "_raw_comment"                 TEXT      NULL,
    
    CONSTRAINT "crs_comment_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "crs_comment_comment_id_key" UNIQUE ("comment_id")
);

COMMENT ON TABLE "audit_core"."crs_comment" IS
    'CRS (Customer Request System) comment master table. '
    'Stores parsed customer comments from Excel files with AI processing results. '
    'One row = one individual comment detail.';

COMMENT ON COLUMN "audit_core"."crs_comment"."llm_category" IS
    'Auto-classified category by LLM. Should match categories in crs_validation_query.category.';

COMMENT ON COLUMN "audit_core"."crs_comment"."validation_result_json" IS
    'JSONB snapshot of SQL query result. Example: '
    '{"query_executed": "SELECT COUNT(*) FROM project_core.tag WHERE tag_name = ...", '
    '"row_count": 0, "result": [...]}';

CREATE INDEX "idx_crs_comment_status"          ON "audit_core"."crs_comment"("status");
CREATE INDEX "idx_crs_comment_category"        ON "audit_core"."crs_comment"("llm_category");
CREATE INDEX "idx_crs_comment_tag"             ON "audit_core"."crs_comment"("tag_name");
CREATE INDEX "idx_crs_comment_doc"             ON "audit_core"."crs_comment"("doc_number");
CREATE INDEX "idx_crs_comment_source_file"     ON "audit_core"."crs_comment"("source_file");
CREATE INDEX "idx_crs_comment_sync_status"     ON "audit_core"."crs_comment"("sync_status");
CREATE INDEX "idx_crs_comment_transmittal"     ON "audit_core"."crs_comment"("transmittal_date");
CREATE INDEX "idx_crs_comment_row_hash"        ON "audit_core"."crs_comment"("row_hash");


-- =============================================================================
-- TABLE 2: audit_core.crs_validation_query
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_validation_query" (
    "id"                 UUID      NOT NULL DEFAULT gen_random_uuid(),
    
    "query_code"         TEXT      NOT NULL UNIQUE,       -- E.g., 'CRS_TAG_DEFECT_001'
    "query_name"         TEXT      NOT NULL,              -- Human-readable name
    "description"        TEXT      NULL,                  -- What this query validates
    
    -- Link to comment classification
    "category"           TEXT      NOT NULL,              -- E.g., 'tag_missing', 'property_anomaly', 'defect'
    "category_description" TEXT    NULL,                  -- Explanation of category
    
    -- SQL query to execute
    "sql_query"          TEXT      NOT NULL,              -- SELECT query that validates the comment
    "expected_result"    TEXT      NULL,                  -- Description of PASS condition
                                                          -- E.g., "Query returns > 0 rows" or "Query returns 0 rows"
    
    -- Parameters (for parametric queries)
    "has_parameters"     BOOLEAN   DEFAULT false,         -- True if query uses :param syntax
    "parameter_names"    TEXT[]    NULL,                  -- Array of parameter names, e.g. ['tag_name', 'property']
    
    -- Metadata
    "is_active"          BOOLEAN   NOT NULL DEFAULT true,
    "created_at"         TIMESTAMP NOT NULL DEFAULT now(),
    "updated_at"         TIMESTAMP NOT NULL DEFAULT now(),
    "created_by"         TEXT      NULL,                  -- User who created query
    "notes"              TEXT      NULL,                  -- Implementation notes
    
    "object_status"      TEXT      NOT NULL DEFAULT 'Active',
    
    CONSTRAINT "crs_validation_query_pkey"     PRIMARY KEY ("id"),
    CONSTRAINT "crs_validation_query_code_key" UNIQUE ("query_code")
);

COMMENT ON TABLE "audit_core"."crs_validation_query" IS
    'Registry of SQL validation queries for CRS comment categories. '
    'Each query links a comment category to a SQL check. '
    'Example: category="tag_missing" → query="SELECT COUNT(*) FROM project_core.tag WHERE tag_name = :tag_name".';

COMMENT ON COLUMN "audit_core"."crs_validation_query"."category" IS
    'Comment category code. Should be the same value that llm_category produces. '
    'Examples: tag_missing, property_defect, design_clarification, vendor_response.';

COMMENT ON COLUMN "audit_core"."crs_validation_query"."sql_query" IS
    'SQL SELECT query. Can use :param placeholders for dynamic values. '
    'Parameters will be filled from crs_comment fields before execution.';

CREATE INDEX "idx_crs_query_category"       ON "audit_core"."crs_validation_query"("category");
CREATE INDEX "idx_crs_query_is_active"      ON "audit_core"."crs_validation_query"("is_active");

-- Auto-update timestamp
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
-- TABLE 3: audit_core.crs_comment_history (SCD Type 2)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_history" (
    "id"               UUID      NOT NULL DEFAULT gen_random_uuid(),
    "comment_id"       UUID      NOT NULL REFERENCES "audit_core"."crs_comment"("id"),
    
    "change_type"      TEXT      NOT NULL,               -- INSERT|UPDATE|DELETE
    "changed_fields"   JSONB     NULL,                   -- {field: {old: X, new: Y}}
    "changed_by"       TEXT      NULL,                   -- User or system making change
    "change_reason"    TEXT      NULL,                   -- Why change was made
    
    "changed_at"       TIMESTAMP NOT NULL DEFAULT now(),
    "run_id"           UUID      NULL,                   -- Prefect run_id for traceability
    
    CONSTRAINT "crs_comment_history_pkey" PRIMARY KEY ("id")
);

COMMENT ON TABLE "audit_core"."crs_comment_history" IS
    'SCD Type 2 change history for crs_comment. Tracks all INSERT/UPDATE/DELETE operations. '
    'Enables audit trail and temporal queries.';

CREATE INDEX "idx_crs_history_comment"    ON "audit_core"."crs_comment_history"("comment_id");
CREATE INDEX "idx_crs_history_timestamp"  ON "audit_core"."crs_comment_history"("changed_at");
CREATE INDEX "idx_crs_history_change_type" ON "audit_core"."crs_comment_history"("change_type");


-- =============================================================================
-- SEED DATA: crs_validation_query — example validation queries
-- =============================================================================

INSERT INTO "audit_core"."crs_validation_query" 
    (query_code, query_name, category, category_description, sql_query, expected_result, is_active, created_by, notes)
VALUES
    (
        'CRS_TAG_EXISTS',
        'Check if tag exists in database',
        'tag_missing',
        'Comment mentions a tag that should exist in project_core.tag',
        'SELECT id, tag_name, tag_status FROM project_core.tag WHERE tag_name = :tag_name AND object_status = ''Active''',
        'PASS: Query returns 1 row with tag details. FAIL: Query returns 0 rows (tag not found).',
        true,
        'system',
        'Basic tag existence check. Uses parametric query with :tag_name placeholder.'
    ),
    (
        'CRS_TAG_PROPERTY_EXISTS',
        'Check if tag property value is defined',
        'property_missing',
        'Comment indicates a property value is missing for a tag',
        'SELECT pv.id, pv.property_id, p.name, pv.property_value FROM project_core.property_value pv JOIN ontology_core.property p ON p.id = pv.property_id WHERE pv.tag_id = (SELECT id FROM project_core.tag WHERE tag_name = :tag_name LIMIT 1) AND p.code = :property_code',
        'PASS: Property exists. FAIL: Property row not found or tag not found.',
        true,
        'system',
        'Multi-parameter query: requires :tag_name and :property_code.'
    ),
    (
        'CRS_DEFECT_IN_VALIDATION_RULES',
        'Check if defect pattern appears in validation results',
        'defect_pattern',
        'Comment describes a data quality defect that should be caught by validation rules',
        'SELECT rule_code, COUNT(*) as violation_count FROM audit_core.validation_result WHERE rule_code LIKE ''%DEFECT%'' AND object_status = ''Active'' GROUP BY rule_code ORDER BY violation_count DESC LIMIT 10',
        'PASS: Returns defect rules. FAIL: No defect rules found (system may not be checking for this defect).',
        true,
        'system',
        'Checks validation rule violations for defect patterns. Non-parametric aggregation query.'
    ),
    (
        'CRS_DOCUMENT_ACTIVE',
        'Check if referenced document is active',
        'document_inactive',
        'Comment references a document that is marked inactive or deleted',
        'SELECT doc_number, title, status, object_status FROM project_core.document WHERE doc_number = :doc_number',
        'PASS: Document exists and object_status=Active. FAIL: Document not found or inactive.',
        true,
        'system',
        'Validates document existence and status.'
    )
ON CONFLICT (query_code) DO NOTHING;


-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm)
-- =============================================================================
/*
-- Check tables created:
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'audit_core' AND table_name LIKE 'crs_%'
ORDER BY table_name;

-- Check crs_comment columns:
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'audit_core' AND table_name = 'crs_comment'
ORDER BY ordinal_position;

-- Check seed queries:
SELECT query_code, query_name, category FROM audit_core.crs_validation_query ORDER BY category;

-- Test parametric query (manual):
-- SELECT * FROM audit_core.crs_validation_query WHERE query_code = 'CRS_TAG_EXISTS';
*/
