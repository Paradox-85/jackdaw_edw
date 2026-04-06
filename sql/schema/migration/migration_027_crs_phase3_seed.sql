/*
Purpose : CRS Phase 3 — Seed audit_core.crs_validation_query with 229 rows.

Strategy:
  Group A (CRS-C001..C050, 50 rows) — migrated from audit_core._crs_vq_backup
      created by migration_027_crs_phase3_schema.sql in the same session.
      Codes reformatted: CRS-C1→CRS-C001, CRS-C10→CRS-C010, etc.
      evaluation_strategy = 'COUNT_ZERO' (all existing queries return violating
      rows; empty result = pass).

  Group B (CRS-C168, 1 row) — PO code missing on tag.
      evaluation_strategy = 'NOT_NULL', is_active = true, has_parameters = true.

  Group C (CRS-C051..C229 except CRS-C168, 178 rows) — generated from
      audit_core.crs_comment_template via SELECT DISTINCT category.
      evaluation_strategy = 'DEFERRED', is_active = false.
      SQL body: zero-result stub (no checks executed).
      Cleaned up: audit_core._crs_vq_backup dropped at end.

Pre-condition : migration_027_crs_phase3_schema.sql must have been run in the
                SAME session so that audit_core._crs_vq_backup exists.

Changes :
  2026-04-06  Initial creation.
*/

BEGIN;

-- ---------------------------------------------------------------------------
-- Group A — Restore existing 50 CRS-C01..C50 rows with zero-padded codes
--           evaluation_strategy = 'COUNT_ZERO' (empty result = pass)
-- ---------------------------------------------------------------------------
INSERT INTO audit_core.crs_validation_query (
    query_code,
    query_name,
    description,
    category,
    category_description,
    sql_query,
    expected_result,
    has_parameters,
    parameter_names,
    notes,
    is_active,
    evaluation_strategy
)
SELECT
    -- Reformat: 'CRS-C1' → 'CRS-C001', 'CRS-C10' → 'CRS-C010'
    'CRS-C' || LPAD(
        REGEXP_REPLACE(b.query_code, '^CRS-C', ''),
        3,
        '0'
    )                       AS query_code,
    b.query_name,
    b.description,
    b.category,
    b.category_description,
    b.sql_query,
    b.expected_result,
    b.has_parameters,
    b.parameter_names,
    b.notes,
    TRUE                    AS is_active,
    'COUNT_ZERO'            AS evaluation_strategy
FROM audit_core._crs_vq_backup b
WHERE b.query_code ~ '^CRS-C\d+$'
ON CONFLICT (query_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Group B — CRS-C168: PO code missing on tag
--           is_active = true, evaluation_strategy = 'NOT_NULL'
-- ---------------------------------------------------------------------------
INSERT INTO audit_core.crs_validation_query (
    query_code,
    query_name,
    description,
    category,
    category_description,
    sql_query,
    expected_result,
    has_parameters,
    parameter_names,
    is_active,
    evaluation_strategy,
    response_template
)
VALUES (
    'CRS-C168',
    'PO_CODE missing on tag',
    'Active tags where po_id is NULL (PO code provided but not resolved, or not submitted at all).',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $sql$
SELECT
    t.tag_name                                          AS object_key,
    'po_id'                                             AS check_field,
    COALESCE(po.code, t.po_code_raw, 'NULL')            AS actual_value,
    (t.po_id IS NOT NULL)                               AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql$,
    'is_resolved = true for all rows',
    TRUE,
    ARRAY['tag_names'],
    TRUE,
    'NOT_NULL',
    '{tag_name} — Purchase Order code confirmed: {actual_value}'
)
ON CONFLICT (query_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Group C — CRS-C051..C229 (except CRS-C168): DEFERRED stub rows
--           Generated from crs_comment_template to ensure full coverage.
--           is_active = false until real SQL is implemented.
-- ---------------------------------------------------------------------------
INSERT INTO audit_core.crs_validation_query (
    query_code,
    query_name,
    description,
    category,
    category_description,
    sql_query,
    expected_result,
    has_parameters,
    is_active,
    evaluation_strategy
)
SELECT DISTINCT
    ct.category                     AS query_code,
    ct.category || ' — deferred check'
                                    AS query_name,
    'Deferred: no automated EDW check implemented for this CRS category yet.'
                                    AS description,
    -- Map crs_comment_template.check_type → category grouping vocabulary
    CASE ct.check_type
        WHEN 'tag'                  THEN 'TAG_DATA'
        WHEN 'equipment'            THEN 'EQUIPMENT'
        WHEN 'equipment_property'   THEN 'PROPERTY'
        WHEN 'tag_property'         THEN 'PROPERTY'
        WHEN 'document'             THEN 'DOCUMENT'
        WHEN 'area'                 THEN 'REFERENCE'
        WHEN 'process_unit'         THEN 'REFERENCE'
        WHEN 'purchase_order'       THEN 'REFERENCE'
        WHEN 'tag_connection'       THEN 'TOPOLOGY'
        WHEN 'tag_class_property'   THEN 'REFERENCE'
        WHEN 'model_part'           THEN 'REFERENCE'
        ELSE                             'OTHER'
    END                             AS category,
    NULL                            AS category_description,
    -- Zero-result stub — safe to execute, returns no rows
    $deferred$
SELECT 'NO_CHECK'::TEXT AS object_key,
       'deferred'::TEXT  AS check_field,
       'DEFERRED'::TEXT  AS actual_value,
       FALSE::BOOLEAN    AS is_resolved
WHERE FALSE;
    $deferred$                      AS sql_query,
    'deferred — not evaluated'      AS expected_result,
    FALSE                           AS has_parameters,
    FALSE                           AS is_active,
    'DEFERRED'                      AS evaluation_strategy
FROM audit_core.crs_comment_template ct
WHERE ct.object_status = 'Active'
  -- Exclude codes covered by Group A (CRS-C001..C050 after zero-padding)
  AND ct.category NOT IN (
      SELECT 'CRS-C' || LPAD(REGEXP_REPLACE(b.query_code, '^CRS-C', ''), 3, '0')
      FROM audit_core._crs_vq_backup b
      WHERE b.query_code ~ '^CRS-C\d+$'
  )
  -- Exclude CRS-C168 (Group B — already inserted)
  AND ct.category != 'CRS-C168'
ON CONFLICT (query_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Cleanup — drop the backup table now that seed is complete
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS audit_core._crs_vq_backup;

-- ---------------------------------------------------------------------------
-- Verification summary
-- ---------------------------------------------------------------------------
SELECT
    evaluation_strategy,
    is_active,
    COUNT(*)   AS row_count
FROM audit_core.crs_validation_query
GROUP BY evaluation_strategy, is_active
ORDER BY evaluation_strategy, is_active;

COMMIT;
