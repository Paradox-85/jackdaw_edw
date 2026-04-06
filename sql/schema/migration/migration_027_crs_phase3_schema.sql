/*
Purpose : CRS Phase 3 — Recreate audit_core.crs_validation_query with 3 new
          Phase 3 columns (evaluation_strategy, group_by_field, response_template).
          Reformat query_code to 3-digit zero-padded form matching
          crs_comment_template.category (CRS-C001 … CRS-C229).
          Also folds in migration_024 (check_type normalisation on
          crs_comment_template) which was never applied to the live DB.

Safe to run because:
  - crs_comment_validation has 0 rows (confirmed 2026-04-06 via MCP)
  - crs_comment.category_code has 0 non-NULL values
  - crs_comment_validation has no FK constraint on crs_validation_query

Changes :
  2026-04-06  Initial creation (migration_027).
*/

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Save existing data before DROP
--    (used by migration_027_crs_phase3_seed.sql to reconstruct Group A rows)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS audit_core._crs_vq_backup;

CREATE TABLE audit_core._crs_vq_backup AS
    SELECT
        query_code,
        query_name,
        description,
        category,
        category_description,
        sql_query,
        expected_result,
        has_parameters,
        parameter_names,
        notes
    FROM audit_core.crs_validation_query;

-- ---------------------------------------------------------------------------
-- 1. Drop old table (CASCADE drops the two associated indexes)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS audit_core.crs_validation_query CASCADE;

-- ---------------------------------------------------------------------------
-- 2. Create new table — 19 columns
--    16 original + 3 Phase 3 additions (evaluation_strategy, group_by_field,
--    response_template). check_type removed; pass_condition deferred to Phase 4.
-- ---------------------------------------------------------------------------
CREATE TABLE audit_core.crs_validation_query (
    id                   UUID        NOT NULL DEFAULT gen_random_uuid(),
    query_code           TEXT        NOT NULL,
    query_name           TEXT        NOT NULL,
    description          TEXT        NULL,
    category             TEXT        NOT NULL,
    category_description TEXT        NULL,
    sql_query            TEXT        NOT NULL,
    expected_result      TEXT        NULL,
    has_parameters       BOOLEAN     NOT NULL DEFAULT FALSE,
    parameter_names      TEXT[]      NULL,
    is_active            BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP   NOT NULL DEFAULT now(),
    updated_at           TIMESTAMP   NOT NULL DEFAULT now(),
    created_by           TEXT        NULL,
    notes                TEXT        NULL,
    object_status        TEXT        NOT NULL DEFAULT 'Active',
    -- Phase 3 additions ---------------------------------------------------
    evaluation_strategy  TEXT        NULL,   -- NOT_NULL|FK_RESOLVED|VALUE_MATCH|REGEX|
                                             -- COUNT_ZERO|AGGREGATE|SEMANTIC|DEFERRED
    group_by_field       TEXT        NULL,   -- secondary UI grouping (e.g. 'property_name')
    response_template    TEXT        NULL,   -- formal-response pre-fill with placeholders
    CONSTRAINT crs_validation_query_pkey        PRIMARY KEY (id),
    CONSTRAINT crs_validation_query_code_key    UNIQUE      (query_code)
);

COMMENT ON COLUMN audit_core.crs_validation_query.evaluation_strategy IS
    'Cascade Evaluator (R-0→R-3) executor instruction. '
    'Values: NOT_NULL | FK_RESOLVED | VALUE_MATCH | REGEX | '
    'COUNT_ZERO | AGGREGATE | SEMANTIC | DEFERRED';

COMMENT ON COLUMN audit_core.crs_validation_query.group_by_field IS
    'Optional secondary grouping field for UI result display (e.g. property_name, tag_class).';

COMMENT ON COLUMN audit_core.crs_validation_query.response_template IS
    'Pre-fill template for formal CRS response. Supports {tag_name}, {actual_value} placeholders.';

-- ---------------------------------------------------------------------------
-- 3. Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX idx_crs_query_is_active
    ON audit_core.crs_validation_query (is_active);

CREATE INDEX idx_crs_query_category
    ON audit_core.crs_validation_query (category);

CREATE INDEX idx_crs_query_evaluation_strategy
    ON audit_core.crs_validation_query (evaluation_strategy)
    WHERE evaluation_strategy IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 4. Resolution report view
--    JOIN: crs_comment → crs_comment_validation → crs_validation_query
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW audit_core.v_crs_resolution_report AS
SELECT
    -- Comment identity
    cc.id                        AS comment_id,
    cc.comment_id                AS comment_ref,
    cc.revision,
    cc.tag_name,
    cc.status                    AS comment_status,
    cc.category_code,
    cc.classification_tier,
    cc.deferred_reason,
    cc.formal_response,
    cc.response_author,
    cc.response_approval_date,
    -- Validation run result
    cv.validation_status,
    cv.validation_result_json,
    cv.validation_error,
    cv.validation_timestamp,
    cv.run_id                    AS validation_run_id,
    -- Diagnostic query metadata
    vq.query_code,
    vq.query_name,
    vq.category                  AS query_category,
    vq.evaluation_strategy,
    vq.response_template,
    vq.group_by_field
FROM audit_core.crs_comment cc
LEFT JOIN audit_core.crs_comment_validation cv
       ON cv.comment_id = cc.id
LEFT JOIN audit_core.crs_validation_query   vq
       ON vq.id = cv.validation_query_id
WHERE cc.object_status = 'Active';

-- ---------------------------------------------------------------------------
-- 5. Fold migration_024 — normalise crs_comment_template.check_type
--    (these UPDATE statements were never applied to the live DB)
-- ---------------------------------------------------------------------------

-- Normalise stale legacy values
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag'
WHERE  check_type IN ('tagdata', 'tag_register')
  AND  object_status = 'Active';

UPDATE audit_core.crs_comment_template
SET    check_type = 'equipment'
WHERE  check_type IN ('equipment_register')
  AND  object_status = 'Active';

UPDATE audit_core.crs_comment_template
SET    check_type = 'document'
WHERE  check_type IN ('doc', 'docs', 'doc_ref')
  AND  object_status = 'Active';

-- model_part  (EIS 209 — Model Part Register, seq -005-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'model_part'
WHERE  category IN ('CRS-C26')
  AND  object_status = 'Active';

-- tag_connection  (EIS 212 — Tag Physical Connections, seq -006-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag_connection'
WHERE  category IN ('CRS-C39', 'CRS-C45')
  AND  object_status = 'Active';

-- purchase_order  (EIS 214 — Purchase Order, seq -008-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'purchase_order'
WHERE  category IN ('CRS-C36', 'CRS-C37', 'CRS-C38')
  AND  object_status = 'Active';

-- tag_class_property  (EIS 307 — Tag Class Properties schema, seq -009-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag_class_property'
WHERE  category IN ('CRS-C04')
  AND  object_status = 'Active';

-- tag_property  (EIS 303 — Tag Property Values, seq -010-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag_property'
WHERE  category IN (
    'CRS-C17', 'CRS-C18', 'CRS-C19', 'CRS-C20',
    'CRS-C21', 'CRS-C22', 'CRS-C48'
  )
  AND  object_status = 'Active';

-- equipment_property  (EIS 301 — Equipment Property Values, seq -011-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'equipment_property'
WHERE  category IN (
    'CRS-C23', 'CRS-C24', 'CRS-C25', 'CRS-C27', 'CRS-C28'
  )
  AND  object_status = 'Active';

-- area  (EIS 203 — Area register, seq -001-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'area'
WHERE  category IN ('CRS-C06', 'CRS-C07')
  AND  object_status = 'Active';

-- process_unit  (EIS 204 — ProcessUnit register, seq -002-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'process_unit'
WHERE  category IN ('CRS-C08', 'CRS-C09')
  AND  object_status = 'Active';

-- document  (all Doc cross-refs)
UPDATE audit_core.crs_comment_template
SET    check_type = 'document'
WHERE  category IN (
    'CRS-C30', 'CRS-C31', 'CRS-C32', 'CRS-C33',
    'CRS-C34', 'CRS-C35', 'CRS-C40', 'CRS-C46', 'CRS-C47'
  )
  AND  object_status = 'Active';

-- ---------------------------------------------------------------------------
-- 6. Verification query (informational — runs but produces no side effects)
-- ---------------------------------------------------------------------------
SELECT check_type,
       COUNT(*)                                         AS template_count,
       STRING_AGG(category, ', ' ORDER BY category)    AS categories
FROM   audit_core.crs_comment_template
WHERE  object_status = 'Active'
GROUP  BY check_type
ORDER  BY check_type;

COMMIT;
