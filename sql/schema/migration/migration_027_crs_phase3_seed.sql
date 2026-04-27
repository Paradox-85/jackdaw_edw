/*
Purpose : CRS Phase 3 — Seed audit_core.crs_validation_query with 229 rows.

Strategy:
  Group A (CRS-C001..C050, 50 rows) — hardcoded from original migration_018 data.
      Codes zero-padded: CRS-C01→CRS-C001, CRS-C10→CRS-C010, etc.
      evaluation_strategy = 'COUNT_ZERO' (empty result = pass).
      Source: migration_018_crs_categories_seed_CANDIDATE_FOR_DELETION.sql

  Group B (CRS-C168, 1 row) — PO code missing on tag.
      evaluation_strategy = 'NOT_NULL', is_active = true, has_parameters = true.

  Group C (CRS-C051..C229 except CRS-C168, 178 rows) — generated from
      audit_core.crs_comment_template via SELECT DISTINCT category.
      evaluation_strategy = 'DEFERRED', is_active = false.
      SQL body: zero-result stub (no checks executed).

Pre-condition : migration_027_crs_phase3_schema.sql must have been applied first
                (table recreated with 3 new Phase 3 columns).

Changes :
  2026-04-06  Initial creation.
  2026-04-07  Rewritten: Group A now hardcoded (no _crs_vq_backup dependency).
  2026-04-07  Bug fixes: C005 UNION removed, C007/C009 NA check added,
              C028 logic corrected, C037 empty string check, C039 object_key
              fixed, C043 deferred due to code conflict, C044 tech_id aligned.
  2026-04-07  Iteration 2: C005 empty array removed, C016/C050 contract
              columns added, C028 impossible NULL fixed, C044 param
              removed, C046 filter added, C048 rewritten to UOM-RDL check.
  2026-04-07  Iteration 3: C028 logic fixed (active tags with equip_no),
              C046 rewritten to doc-inactive check per validation_queries,
              C050 sort fixed (depth DESC not TEXT), C037 TRIM(date) removed,
              C049 notes updated (not covered in vq reference).
  2026-04-07  Iteration 4: C028 tautology fixed (blank tag_name check),
              C016/C039 TEXT sort fixed (COUNT(*) DESC),
              C022 empty-value gap closed (property_value != ''),
              C046 is_resolved simplified to literal FALSE.
  2026-04-07  Iteration 5: C028 logic rewritten (dead-code removed, equip inactive/null check),
              C037 po_date::TEXT cast added, C038 NULL::TEXT explicit cast,
              C045 UNION ALL column alias unified, C046 STRING_AGG NULL guard,
              C043/C049 notes clarified per VQ coverage gaps.
  2026-04-07  Iteration 6: C038 po_code alias (ORDER BY fix), C050 ORDER BY
              depth→actual_value, C003 ORDER BY expression, C017/C018/C019
              object_key contract aligned, C039 ORDER BY stabilized,
              C049 ARRAY_AGG→COUNT TEXT.
  2026-04-07  Iteration 7: C038 po_code alias verified/re-applied,
              C049 ORDER BY cnt→actual_value::BIGINT, C017 ORDER BY numeric cast,
              C037 GROUP BY tautology removed + COALESCE(po_date::TEXT,'NULL'),
              C046 actual_value bracket format for clarity.
  2026-04-07  Iteration 8: Added Group D — promotes ~120 DEFERRED stubs to active.
              D1 aliases (39 codes) reuse Group A SQL via UPDATE...FROM.
              D2 unique codes (72 codes) use canonical SQL from
              crs_phase3_validation_queries.sql with DO UPDATE SET.
              Genuinely DEFERRED remain: SEMANTIC/LLM (~9), external DMS (~30),
              process-only/advisory (~14), no EDW data (C053/C055/C056),
              C043 (alias-conflict semantic mismatch), C114 (not in reference file).
*/

BEGIN;

-- ---------------------------------------------------------------------------
-- Group A — 50 CRS-C001..C050 rows from original migration_018 data
--           evaluation_strategy = 'COUNT_ZERO' (empty result = pass)
-- ---------------------------------------------------------------------------

-- CRS-C001 — Missing mandatory fields (general)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C001',
    'Missing mandatory fields (general)',
    'Tags with empty mandatory fields: TAG_CLASS, DESCRIPTION, PROCESS_UNIT, SAFETY_CRITICAL_ITEM',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c001$
SELECT
    t.tag_name,
    t.plant_raw,
    CASE WHEN t.class_id IS NULL                                  THEN 'TAG_CLASS missing'       END AS issue_class,
    CASE WHEN t.description IS NULL OR t.description = ''         THEN 'DESCRIPTION missing'     END AS issue_desc,
    CASE WHEN t.process_unit_id IS NULL                           THEN 'PROCESS_UNIT missing'    END AS issue_pu,
    CASE WHEN t.safety_critical_item IS NULL
          OR TRIM(t.safety_critical_item) = ''                    THEN 'SAFETY_CRITICAL missing' END AS issue_sc
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (
      t.class_id IS NULL
      OR t.description IS NULL OR t.description = ''
      OR t.process_unit_id IS NULL
      OR t.safety_critical_item IS NULL OR TRIM(t.safety_critical_item) = ''
  )
ORDER BY t.tag_name;
    $sql_c001$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 001/003/004. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C002 — TAG_DESCRIPTION missing
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C002',
    'TAG_DESCRIPTION missing',
    'Active tags where description is NULL or empty',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c002$
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)   AS tag_class,
    COALESCE(pl.code, t.plant_raw)      AS plant_code
FROM project_core.tag t
LEFT JOIN ontology_core.class  c  ON c.id  = t.class_id
LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
WHERE t.object_status = 'Active'
  AND (t.description IS NULL OR TRIM(t.description) = '')
ORDER BY t.tag_name;
    $sql_c002$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C003 — TAG_DESCRIPTION exceeds 255 characters
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C003',
    'TAG_DESCRIPTION exceeds 255 characters',
    'Tags where description length exceeds 255 characters',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c003$
SELECT
    t.tag_name,
    LENGTH(t.description)            AS desc_length,
    LEFT(t.description, 80) || '...' AS desc_preview
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.description IS NOT NULL
  AND LENGTH(t.description) > 255
ORDER BY LENGTH(t.description) DESC;
    $sql_c003$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C004 — TAG_CLASS not in ISM / RDL
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C004',
    'TAG_CLASS not in ISM / RDL',
    'Tags where class_id is NULL but tag_class_raw is provided (unresolved FK)',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c004$
SELECT
    t.tag_name,
    t.tag_class_raw   AS submitted_class,
    'NOT RESOLVED IN RDL' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.class_id IS NULL
  AND t.tag_class_raw IS NOT NULL AND t.tag_class_raw != ''
ORDER BY t.tag_class_raw, t.tag_name;
    $sql_c004$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C005 — Tag Naming Convention (TNC) violated
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C005',
    'Tag Naming Convention (TNC) violated',
    'Tags not starting with JDA-, containing commas, or pipe-tags ending with dash',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c005$
SELECT
  t.tag_name AS object_key,
  'tag_name_pattern' AS check_field,
  t.tag_name AS actual_value,
  (t.tag_name LIKE 'JDA-%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name NOT LIKE 'JDA-%'
ORDER BY t.tag_name;
    $sql_c005$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003/004. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C006 — AREA_CODE blank
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C006',
    'AREA_CODE blank',
    'Active tags where area_id is NULL (recommended field)',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c006$
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)     AS tag_class,
    COALESCE(pu.code, t.process_unit_raw) AS process_unit
FROM project_core.tag t
LEFT JOIN ontology_core.class         c  ON c.id  = t.class_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE t.object_status = 'Active'
  AND t.area_id IS NULL
ORDER BY t.tag_name;
    $sql_c006$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C007 — AREA_CODE invalid or literal NA
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C007',
    'AREA_CODE invalid or literal NA',
    'Tags where area_code_raw provided but FK not resolved, or literal NA value',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c007$
SELECT
    t.tag_name,
    t.area_code_raw       AS submitted_area_code,
    'NOT IN AREA REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (
      (t.area_code_raw IS NOT NULL AND t.area_code_raw != ''
       AND t.area_id IS NULL)
      OR (t.area_code_raw IS NOT NULL
          AND UPPER(TRIM(t.area_code_raw)) = 'NA')
      OR (t.area_code_raw IS NOT NULL
          AND t.area_code_raw LIKE '%,%')
  )
ORDER BY t.area_code_raw;
    $sql_c007$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 001/003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C008 — PROCESS_UNIT_CODE missing
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C008',
    'PROCESS_UNIT_CODE missing',
    'Active tags where process_unit_id is NULL',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c008$
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw) AS tag_class,
    COALESCE(pl.code, t.plant_raw)    AS plant_code
FROM project_core.tag t
LEFT JOIN ontology_core.class  c  ON c.id  = t.class_id
LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
WHERE t.object_status = 'Active'
  AND t.process_unit_id IS NULL
ORDER BY t.tag_name;
    $sql_c008$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C009 — PROCESS_UNIT_CODE not in register
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C009',
    'PROCESS_UNIT_CODE not in register',
    'Tags where process_unit_raw provided but FK not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c009$
SELECT
    t.tag_name,
    t.process_unit_raw        AS submitted_pu_code,
    'NOT IN PROCESS_UNIT REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (
      (t.process_unit_raw IS NOT NULL AND t.process_unit_raw != ''
       AND t.process_unit_id IS NULL)
      OR (t.process_unit_raw IS NOT NULL
          AND UPPER(TRIM(t.process_unit_raw)) = 'NA')
  )
ORDER BY t.process_unit_raw;
    $sql_c009$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003/018. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C010 — PARENT_TAG missing for physical tags
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C010',
    'PARENT_TAG missing for physical tags',
    'Physical tags (valve, transmitter, pipe, pump, motor, sensor) without parent_tag',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c010$
SELECT
    t.tag_name,
    c.name AS tag_class
FROM project_core.tag t
JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.parent_tag_id IS NULL
  AND t.parent_tag_raw IS NULL
  AND c.name ILIKE ANY (ARRAY['%valve%','%transmitter%','%pipe%','%pump%','%motor%','%sensor%'])
ORDER BY c.name, t.tag_name;
    $sql_c010$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C011 — PARENT_TAG not in MTR
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C011',
    'PARENT_TAG not in MTR',
    'Tags where parent_tag_raw provided but parent_tag_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c011$
SELECT
    t.tag_name,
    t.parent_tag_raw     AS declared_parent,
    'PARENT NOT IN MTR'  AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.parent_tag_raw IS NOT NULL AND t.parent_tag_raw != ''
  AND t.parent_tag_id IS NULL
ORDER BY t.parent_tag_raw;
    $sql_c011$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C012 — PARENT_TAG pipe-to-pipe reference
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C012',
    'PARENT_TAG pipe-to-pipe reference',
    'Pipe tags whose parent tag is also a pipe tag',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c012$
SELECT
    child.tag_name  AS child_tag,
    parent.tag_name AS parent_tag,
    cc.name         AS child_class,
    pc.name         AS parent_class
FROM project_core.tag child
JOIN project_core.tag  parent ON parent.id = child.parent_tag_id
JOIN ontology_core.class cc    ON cc.id    = child.class_id
JOIN ontology_core.class pc    ON pc.id    = parent.class_id
WHERE child.object_status  = 'Active'
  AND parent.object_status = 'Active'
  AND cc.name ILIKE '%pipe%'
  AND pc.name ILIKE '%pipe%'
ORDER BY child.tag_name;
    $sql_c012$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C013 — SAFETY_CRITICAL_ITEM blank or invalid
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C013',
    'SAFETY_CRITICAL_ITEM blank or invalid',
    'Active tags with NULL, empty, or non-YES/NO safety_critical_item',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c013$
SELECT
    t.tag_name,
    t.safety_critical_item,
    COALESCE(c.name, t.tag_class_raw) AS tag_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND (
      t.safety_critical_item IS NULL
      OR TRIM(t.safety_critical_item) = ''
      OR UPPER(TRIM(t.safety_critical_item)) NOT IN ('YES','NO','Y','N')
  )
ORDER BY t.tag_name;
    $sql_c013$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C014 — SAFETY_CRITICAL_REASON missing for SECE tags
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C014',
    'SAFETY_CRITICAL_REASON missing for SECE tags',
    'Safety-critical tags (YES/Y) without safety_critical_item_reason_awarded',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c014$
SELECT
    t.tag_name,
    t.safety_critical_item,
    t.safety_critical_item_reason_awarded
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND (t.safety_critical_item_reason_awarded IS NULL OR TRIM(t.safety_critical_item_reason_awarded) = '')
ORDER BY t.tag_name;
    $sql_c014$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C015 — PRODUCTION_CRITICAL_ITEM blank
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C015',
    'PRODUCTION_CRITICAL_ITEM blank',
    'Active tags with NULL or empty production_critical_item',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c015$
SELECT
    t.tag_name,
    t.production_critical_item,
    COALESCE(c.name, t.tag_class_raw) AS tag_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND (t.production_critical_item IS NULL OR TRIM(t.production_critical_item) = '')
ORDER BY t.tag_name;
    $sql_c015$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C016 — Duplicate tags
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C016',
    'Duplicate tags',
    'Active tags with duplicate tag_name values',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c016$
SELECT
  tag_name         AS object_key,
  'tag_name_uniqueness' AS check_field,
  COUNT(*)::TEXT   AS actual_value,
  (COUNT(*) = 1)   AS is_resolved
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_name
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC, object_key;
    $sql_c016$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C017 — Tag Property: tag not in MTR
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C017',
    'Tag Property: tag not in MTR',
    'Property values referencing tags that do not exist or are inactive',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c017$
SELECT
    pv.tag_name_raw                           AS object_key,
    COALESCE(t.object_status, 'NOT_IN_MTR')   AS actual_value,
    COUNT(pv.id)::TEXT                        AS property_rows
FROM project_core.property_value pv
LEFT JOIN project_core.tag t ON t.id = pv.tag_id
WHERE pv.object_status = 'Active'
  AND (
      t.id IS NULL
      OR t.object_status != 'Active'
  )
GROUP BY pv.tag_name_raw, t.object_status
ORDER BY property_rows::BIGINT DESC;
    $sql_c017$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 010. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C018 — PROPERTY_VALUE = NA with non-empty UOM
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C018',
    'PROPERTY_VALUE = NA with non-empty UOM',
    'Property values with NA/N/A but non-empty property_uom_raw',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c018$
SELECT
    pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
    'uom_when_na'                                   AS check_field,
    pv.property_value || ' | ' || pv.property_uom_raw AS actual_value,
    FALSE                                           AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.id = pv.tag_id
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(pv.property_value,''))) IN ('NA','N/A')
  AND pv.property_uom_raw IS NOT NULL
  AND TRIM(pv.property_uom_raw) != ''
ORDER BY t.tag_name, pv.property_code_raw;
    $sql_c018$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 010/011', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C019 — PROPERTY_VALUE = 0 (zero value)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C019',
    'PROPERTY_VALUE = 0 (zero value)',
    'Property values with exact string "0"',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c019$
SELECT
    pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
    'property_value_zero'                           AS check_field,
    COALESCE(pv.property_value, 'NULL')             AS actual_value,
    FALSE                                           AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.id = pv.tag_id
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND TRIM(COALESCE(pv.property_value,'')) = '0'
ORDER BY t.tag_name, pv.property_code_raw;
    $sql_c019$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 010/011', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C020 — Property class mapping mismatch
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C020',
    'Property class mapping mismatch',
    'Property values where property_code is not in the allowed set for the tag class',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c020$
SELECT
    t.tag_name,
    c.name                         AS tag_class,
    pv.property_code_raw           AS property_code,
    'PROPERTY NOT IN CLASS SCOPE'  AS issue
FROM project_core.property_value pv
JOIN project_core.tag t    ON t.id  = pv.tag_id
JOIN ontology_core.class c ON c.id  = t.class_id
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND NOT EXISTS (
      SELECT 1
      FROM ontology_core.class_property cp
      JOIN ontology_core.property p ON p.id = cp.property_id
      WHERE cp.class_id = t.class_id
        AND p.code = pv.property_code_raw
        AND cp.mapping_status = 'Active'
  )
ORDER BY t.tag_name, pv.property_code_raw;
    $sql_c020$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 010. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C021 — Tag without any property in Property CSV
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C021',
    'Tag without any property in Property CSV',
    'Active tags with no property_value records',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c021$
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)     AS tag_class,
    COALESCE(pu.code, t.process_unit_raw) AS process_unit
FROM project_core.tag t
LEFT JOIN ontology_core.class         c  ON c.id  = t.class_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE t.object_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM project_core.property_value pv
      WHERE pv.tag_id = t.id AND pv.object_status = 'Active'
  )
ORDER BY t.tag_name;
    $sql_c021$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 010. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C022 — Mandatory ISM properties not submitted
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C022',
    'Mandatory ISM properties not submitted',
    'Tags missing properties with mapping_presence = Mandatory per RDL',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c022$
SELECT
    t.tag_name,
    c.name                       AS tag_class,
    p.code                       AS required_property,
    'MISSING MANDATORY PROPERTY' AS issue
FROM project_core.tag t
JOIN ontology_core.class          c  ON c.id  = t.class_id
JOIN ontology_core.class_property cp ON cp.class_id = c.id
JOIN ontology_core.property       p  ON p.id  = cp.property_id
WHERE t.object_status  = 'Active'
  AND cp.mapping_presence = 'Mandatory'
  AND cp.mapping_status   = 'Active'
  AND NOT EXISTS (
      SELECT 1
      FROM project_core.property_value pv
      WHERE pv.tag_id = t.id
        AND pv.property_code_raw = p.code
        AND pv.object_status = 'Active'
        AND pv.property_value IS NOT NULL
        AND TRIM(pv.property_value) != ''
  )
ORDER BY t.tag_name, p.code;
    $sql_c022$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 010/011', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C023 — EQUIPMENT_CLASS not in RDL
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C023',
    'EQUIPMENT_CLASS not in RDL',
    'Equipment tags where class_id is NULL but tag_class_raw is provided',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c023$
SELECT
    t.equip_no          AS equipment_number,
    t.tag_name,
    t.tag_class_raw     AS submitted_class,
    'CLASS NOT IN RDL'  AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.class_id IS NULL
  AND t.tag_class_raw IS NOT NULL AND t.tag_class_raw != ''
ORDER BY t.tag_class_raw;
    $sql_c023$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 004. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C024 — EQUIPMENT_DESCRIPTION blank
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C024',
    'EQUIPMENT_DESCRIPTION blank',
    'Equipment tags with NULL or empty description',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c024$
SELECT
    t.equip_no AS equipment_number,
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND (t.description IS NULL OR TRIM(t.description) = '')
ORDER BY t.tag_name;
    $sql_c024$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 004. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C025 — MANUFACTURER_SERIAL_NUMBER blank or NA
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C025',
    'MANUFACTURER_SERIAL_NUMBER blank or NA',
    'Equipment tags with NULL, empty, or NA serial_no',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c025$
SELECT
    t.equip_no   AS equipment_number,
    t.tag_name,
    t.serial_no,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND (
      t.serial_no IS NULL
      OR TRIM(t.serial_no) = ''
      OR UPPER(TRIM(t.serial_no)) = 'NA'
  )
ORDER BY t.tag_name;
    $sql_c025$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 004. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C026 — MODEL_PART_NAME blank
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C026',
    'MODEL_PART_NAME blank',
    'Equipment tags with unresolved model_id and empty model_part_raw',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c026$
SELECT
    t.equip_no          AS equipment_number,
    t.tag_name,
    t.model_part_raw    AS submitted_model_part,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.model_id IS NULL
  AND (t.model_part_raw IS NULL OR TRIM(t.model_part_raw) = '')
ORDER BY t.tag_name;
    $sql_c026$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 004. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C027 — MANUFACTURER_COMPANY blank
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C027',
    'MANUFACTURER_COMPANY blank',
    'Equipment tags with unresolved manufacturer_id and empty manufacturer_company_raw',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c027$
SELECT
    t.equip_no                        AS equipment_number,
    t.tag_name,
    t.manufacturer_company_raw,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.manufacturer_id IS NULL
  AND (t.manufacturer_company_raw IS NULL OR TRIM(t.manufacturer_company_raw) = '')
ORDER BY t.tag_name;
    $sql_c027$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 004. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C028 — Equipment: TAG_NAME not in MTR
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C028',
    'Equipment: TAG_NAME not in MTR',
    'Equipment records with equip_no but no corresponding active tag',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c028$
SELECT
    t.equip_no          AS object_key,
    'tag_name_in_mtr'   AS check_field,
    COALESCE(t.tag_name, 'NULL') AS actual_value,
    FALSE               AS is_resolved
FROM project_core.tag t
WHERE t.equip_no IS NOT NULL
  AND (
      t.object_status != 'Active'
      OR t.tag_name IS NULL
      OR TRIM(t.tag_name) = ''
  )
ORDER BY t.equip_no;
    $sql_c028$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 004. CRS-C028/CRS-C106: equipment rows with equip_no that are
inactive or have no tag_name. Count_zero = clean dataset.', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C029 — PLANT_CODE invalid or missing
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C029',
    'PLANT_CODE invalid or missing',
    'Tags where plant_raw provided but plant_id not resolved',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c029$
SELECT
    t.tag_name,
    t.plant_raw             AS submitted_plant_code,
    'PLANT NOT IN REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.plant_raw IS NOT NULL AND t.plant_raw != ''
  AND t.plant_id IS NULL
ORDER BY t.plant_raw;
    $sql_c029$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003/004. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C030 — Document not in DocMaster or NYI/CAN status
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C030',
    'Document not in DocMaster or NYI/CAN status',
    'Active documents with NULL status or NYI/CAN (not yet issued / cancelled)',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c030$
SELECT
    doc.doc_number,
    doc.title,
    doc.status,
    doc.rev,
    doc.object_status
FROM project_core.document doc
WHERE doc.object_status = 'Active'
  AND (
      doc.status IS NULL
      OR UPPER(TRIM(doc.status)) IN ('NYI','CAN')
  )
ORDER BY doc.doc_number;
    $sql_c030$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 014/016. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C031 — Tag without document reference
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C031',
    'Tag without document reference',
    'Active tags with no active entries in mapping.tag_document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c031$
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)     AS tag_class,
    COALESCE(pu.code, t.process_unit_raw) AS process_unit
FROM project_core.tag t
LEFT JOIN ontology_core.class         c  ON c.id  = t.class_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE t.object_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM mapping.tag_document td
      WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  )
ORDER BY t.tag_name;
    $sql_c031$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 016. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C032 — Doc in Tag-Doc mapping but not in DocMaster
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C032',
    'Doc in Tag-Doc mapping but not in DocMaster',
    'Document numbers referenced in tag_document but absent from project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c032$
SELECT
    td.doc_number_raw               AS referenced_doc,
    COUNT(DISTINCT td.tag_id)       AS tag_count,
    'NOT IN DOCUMENT MASTER'        AS issue
FROM mapping.tag_document td
WHERE td.mapping_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM project_core.document doc
      WHERE doc.doc_number = td.doc_number_raw
        AND doc.object_status = 'Active'
  )
GROUP BY td.doc_number_raw
ORDER BY tag_count DESC;
    $sql_c032$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 016. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C033 — Tag in Tag-Doc mapping but not in MTR
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C033',
    'Tag in Tag-Doc mapping but not in MTR',
    'Tag names referenced in tag_document but absent from project_core.tag',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c033$
SELECT
    td.tag_name_raw           AS referenced_tag,
    COUNT(DISTINCT td.document_id) AS doc_count,
    'NOT IN MTR (Active)'     AS issue
FROM mapping.tag_document td
WHERE td.mapping_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM project_core.tag t
      WHERE t.tag_name = td.tag_name_raw
        AND t.object_status = 'Active'
  )
GROUP BY td.tag_name_raw
ORDER BY doc_count DESC;
    $sql_c033$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 016. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C034 — Doc-Area: AREA_CODE missing
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C034',
    'Doc-Area: AREA_CODE missing',
    'Documents linked to tags without area_id (seq 017 export will have empty AREA_CODE)',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c034$
SELECT
    d.doc_number,
    COUNT(DISTINCT t.id) AS tags_without_area
FROM mapping.tag_document td
JOIN project_core.document d ON d.id = td.document_id
JOIN project_core.tag      t ON t.id = td.tag_id
WHERE td.mapping_status = 'Active'
  AND d.object_status   = 'Active'
  AND t.object_status   = 'Active'
  AND t.area_id IS NULL
GROUP BY d.doc_number
ORDER BY tags_without_area DESC;
    $sql_c034$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 017. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C035 — Doc-PU: PROCESS_UNIT_CODE missing
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C035',
    'Doc-PU: PROCESS_UNIT_CODE missing',
    'Documents linked to tags without process_unit_id (seq 018 export will be empty)',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c035$
SELECT
    d.doc_number,
    COUNT(DISTINCT t.id) AS tags_without_pu
FROM mapping.tag_document td
JOIN project_core.document d ON d.id = td.document_id
JOIN project_core.tag      t ON t.id = td.tag_id
WHERE td.mapping_status = 'Active'
  AND d.object_status   = 'Active'
  AND t.object_status   = 'Active'
  AND t.process_unit_id IS NULL
GROUP BY d.doc_number
ORDER BY tags_without_pu DESC;
    $sql_c035$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 018. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C036 — PO_CODE not in PO Register
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C036',
    'PO_CODE not in PO Register',
    'Tags where po_code_raw provided but po_id not resolved',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c036$
SELECT
    t.tag_name,
    t.po_code_raw        AS submitted_po_code,
    'PO NOT IN REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.po_code_raw IS NOT NULL AND t.po_code_raw != ''
  AND t.po_id IS NULL
ORDER BY t.po_code_raw;
    $sql_c036$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 008/022. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C037 — PO_DATE missing
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C037',
    'PO_DATE missing',
    'Active purchase orders without po_date',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c037$
SELECT
    po.code                              AS po_code,
    COALESCE(po.po_date::TEXT, 'NULL')   AS po_date,
    COUNT(t.id)                          AS tags_linked
FROM reference_core.purchase_order po
LEFT JOIN project_core.tag t ON t.po_id = po.id AND t.object_status = 'Active'
WHERE po.object_status = 'Active'
  AND po.po_date IS NULL
GROUP BY po.code
ORDER BY tags_linked DESC;
    $sql_c037$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 008. mapping_presence: Mandatory', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C038 — COMPANY_NAME missing or invalid
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C038',
    'COMPANY_NAME missing or invalid',
    'POs without issuer company, or equipment without manufacturer',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c038$
SELECT po.code AS po_code, NULL::TEXT AS tag_name, 'ISSUER COMPANY MISSING' AS issue
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active' AND po.issuer_id IS NULL

UNION ALL

SELECT NULL::TEXT AS po_code, t.tag_name, 'NO MANUFACTURER COMPANY' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.manufacturer_id IS NULL
  AND (t.manufacturer_company_raw IS NULL OR TRIM(t.manufacturer_company_raw) = '')

ORDER BY issue, po_code, tag_name;
    $sql_c038$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 007/022. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C039 — Duplicate physical connections
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C039',
    'Duplicate physical connections',
    'Duplicate from_tag_raw/to_tag_raw pairs among active tags',
    'TOPOLOGY', 'Topology and physical connection checks',
    $sql_c039$
SELECT
  from_tag_raw || '->' || to_tag_raw AS object_key,
  'connection_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.tag
WHERE object_status = 'Active'
  AND from_tag_raw IS NOT NULL
  AND to_tag_raw IS NOT NULL
GROUP BY from_tag_raw, to_tag_raw
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC, object_key;
    $sql_c039$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 006', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C040 — Equipment without Doc-Equipment mapping
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C040',
    'Equipment without Doc-Equipment mapping',
    'Equipment tags with no document reference in mapping.tag_document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c040$
SELECT
    t.equip_no    AS equipment_number,
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class,
    'NO DOC-EQUIPMENT MAPPING' AS issue
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM mapping.tag_document td
      WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  )
ORDER BY t.tag_name;
    $sql_c040$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 019. mapping_presence: Recommended', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C041 — EX_CLASS / IP_GRADE missing for E&I tags
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C041',
    'EX_CLASS / IP_GRADE missing for E&I tags',
    'Instrument/sensor/detector tags without ex_class and ip_grade',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c041$
SELECT
    t.tag_name,
    t.tag_class_raw,
    t.area_code_raw,
    t.ex_class,
    t.ip_grade
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.ex_class IS NULL
  AND t.ip_grade IS NULL
  AND t.tag_class_raw ~* '(transmitter|sensor|junction.box|control.station|detector|analyser)'
ORDER BY t.tag_class_raw, t.tag_name;
    $sql_c041$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C042 — MC_PACKAGE_CODE missing
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C042',
    'MC_PACKAGE_CODE missing',
    'Valve/instrument/electrical/mechanical tags without mc_package_code',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c042$
SELECT
    t.tag_name,
    t.tag_class_raw,
    t.process_unit_raw,
    t.mc_package_code
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (t.mc_package_code IS NULL OR TRIM(t.mc_package_code) = '')
  AND t.tag_class_raw ~* '(valve|instrument|electrical|mechanical)'
ORDER BY t.tag_class_raw, t.tag_name;
    $sql_c042$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C043 — ALIAS conflicts with another tag
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C043',
    'ALIAS conflicts with another tag',
    'Alias values shared by multiple tags, or alias matching another tag''s tag_name',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c043$
SELECT
    alias,
    ARRAY_AGG(tag_name ORDER BY tag_name) AS conflicting_tags,
    COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
  AND alias IS NOT NULL AND TRIM(alias) != ''
GROUP BY alias
HAVING COUNT(*) > 1
ORDER BY cnt DESC;
    $sql_c043$,
    'No violating rows (empty result = pass)', false,
    'DEFERRED: validation_queries maps CRS-C043 AND CRS-C044 to tech_id field check.
Current seed stores alias-conflict logic which is different semantics.
Do NOT activate until analyst confirms correct mapping.
Ref: crs_phase3_validation_queries.sql CRS-C043/CRS-C044 block.',
    false, 'DEFERRED'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C044 — TECH_ID missing for instrument tags
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C044',
    'TECH_ID missing for instrument tags',
    'Instrument/loop/signal/transmitter tags without tech_id',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c044$
SELECT
    t.tag_name,
    t.tech_id,
    t.tag_class_raw
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (t.tech_id IS NULL OR TRIM(t.tech_id) = '')
  AND t.tag_class_raw ~* '(instrument|transmitter|sensor|detector)'
ORDER BY t.tag_class_raw, t.tag_name;
    $sql_c044$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C045 — FROM_TAG / TO_TAG not in MTR
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C045',
    'FROM_TAG / TO_TAG not in MTR',
    'Tags with from_tag_raw or to_tag_raw that could not be resolved to a tag FK',
    'TOPOLOGY', 'Topology and physical connection checks',
    $sql_c045$
SELECT
    t.tag_name,
    t.from_tag_raw    AS unresolved_raw_ref,
    'FROM_TAG NOT IN MTR' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.from_tag_raw IS NOT NULL AND TRIM(t.from_tag_raw) != ''
  AND t.from_tag_id IS NULL

UNION ALL

SELECT
    t.tag_name,
    t.to_tag_raw      AS unresolved_raw_ref,
    'TO_TAG NOT IN MTR' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.to_tag_raw IS NOT NULL AND TRIM(t.to_tag_raw) != ''
  AND t.to_tag_id IS NULL

ORDER BY issue, tag_name;
    $sql_c045$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 006', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C046 — Tag linked to inactive document
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C046',
    'Tag linked to inactive document',
    'Active tags referencing documents where object_status != Active in mapping.tag_document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c046$
SELECT
  t.tag_name               AS object_key,
  'doc_is_active'          AS check_field,
  COALESCE(
    STRING_AGG(
      COALESCE(d.doc_number,'?') || ' [' || COALESCE(d.object_status,'NULL') || ']',
      '; ' ORDER BY d.doc_number
    ),
    'NULL'
  )                        AS actual_value,
  FALSE                    AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id
  AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND EXISTS (
    SELECT 1 FROM mapping.tag_document td3
    JOIN project_core.document d3 ON d3.id = td3.document_id
    WHERE td3.tag_id = t.id
      AND td3.mapping_status = 'Active'
      AND d3.object_status != 'Active'
  )
GROUP BY t.id, t.tag_name
ORDER BY t.tag_name;
    $sql_c046$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 016. Validation: tag linked to inactive document (object_status != Active).', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C047 — Safety critical tag without SECE mapping
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C047',
    'Safety critical tag without SECE mapping',
    'Tags with safety_critical_item=YES/Y but no active entry in mapping.tag_sece',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c047$
SELECT
    t.tag_name,
    t.safety_critical_item,
    t.safety_critical_item_reason_awarded
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND NOT EXISTS (
      SELECT 1 FROM mapping.tag_sece ts
      WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active'
  )
ORDER BY t.tag_name;
    $sql_c047$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C048 — Property UOM not in RDL
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C048',
    'Property UOM not in RDL (ontology_core.uom)',
    'Property values where property_uom_raw is not found
  in ontology_core.uom by code or symbol',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c048$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'uom_in_rdl'                                    AS check_field,
  COALESCE(pv.property_uom_raw, 'NULL')           AS actual_value,
  (pv.property_uom_raw IS NULL
   OR EXISTS (
     SELECT 1 FROM ontology_core.uom u
     WHERE UPPER(u.code)   = UPPER(pv.property_uom_raw)
        OR UPPER(u.symbol) = UPPER(pv.property_uom_raw)
   )) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.property_uom_raw IS NOT NULL
  AND TRIM(pv.property_uom_raw) != ''
  AND NOT EXISTS (
    SELECT 1 FROM ontology_core.uom u
    WHERE UPPER(u.code)   = UPPER(pv.property_uom_raw)
       OR UPPER(u.symbol) = UPPER(pv.property_uom_raw)
  )
ORDER BY pv.tag_name_raw, pv.property_code_raw;
    $sql_c048$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 010/011', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C049 — Duplicate doc_number in Document
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C049',
    'Duplicate doc_number in Document',
    'Multiple active rows for the same doc_number in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c049$
SELECT
    doc_number                  AS object_key,
    'doc_number_unique'         AS check_field,
    COUNT(*)::TEXT              AS actual_value,
    (COUNT(*) = 1)              AS is_resolved
FROM project_core.document
WHERE object_status = 'Active'
GROUP BY doc_number
HAVING COUNT(*) > 1
ORDER BY actual_value::BIGINT DESC;
    $sql_c049$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 014. NOT COVERED in crs_phase3_validation_queries.sql.
Closest VQ equivalent: CRS-C079 (doc_number_unique, COUNT_ZERO, document domain).
Analyst confirmation required before this check can be considered canonical.', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

-- CRS-C050 — Circular parent tag hierarchy
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C050',
    'Circular parent tag hierarchy',
    'Tags participating in circular parent_tag_id chains (ISO 15926 Part 2 violation)',
    'TOPOLOGY', 'Topology and physical connection checks',
    $sql_c050$
WITH RECURSIVE tag_hierarchy AS (
    SELECT
        id,
        tag_name,
        parent_tag_id,
        1                AS depth,
        ARRAY[id]        AS path,
        FALSE            AS is_cycle
    FROM project_core.tag
    WHERE object_status = 'Active'
      AND parent_tag_id IS NOT NULL

    UNION ALL

    SELECT
        t.id,
        t.tag_name,
        t.parent_tag_id,
        th.depth + 1,
        th.path || t.id,
        t.id = ANY(th.path)
    FROM project_core.tag t
    JOIN tag_hierarchy th ON t.id = th.parent_tag_id
    WHERE NOT th.is_cycle
      AND th.depth < 10
)
SELECT DISTINCT
    tag_name               AS object_key,
    'parent_tag_cycle'     AS check_field,
    depth::TEXT            AS actual_value,
    FALSE                  AS is_resolved
FROM tag_hierarchy
WHERE is_cycle = TRUE
ORDER BY actual_value DESC, object_key;
    $sql_c050$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. WARNING: real cycles found (JDA-P-46001A/B)', true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO NOTHING;

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
    $sql_c168$
SELECT
    t.tag_name                                          AS object_key,
    'po_id'                                             AS check_field,
    COALESCE(po.code, t.po_code_raw, 'NULL')            AS actual_value,
    (t.po_id IS NOT NULL)                               AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c168$,
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
    ct.category_code                AS query_code,
    ct.category_code || ' — deferred check'
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
  -- Exclude codes covered by Group A (CRS-C001..CRS-C050)
  AND ct.category_code NOT IN (
      'CRS-C001','CRS-C002','CRS-C003','CRS-C004','CRS-C005',
      'CRS-C006','CRS-C007','CRS-C008','CRS-C009','CRS-C010',
      'CRS-C011','CRS-C012','CRS-C013','CRS-C014','CRS-C015',
      'CRS-C016','CRS-C017','CRS-C018','CRS-C019','CRS-C020',
      'CRS-C021','CRS-C022','CRS-C023','CRS-C024','CRS-C025',
      'CRS-C026','CRS-C027','CRS-C028','CRS-C029','CRS-C030',
      'CRS-C031','CRS-C032','CRS-C033','CRS-C034','CRS-C035',
      'CRS-C036','CRS-C037','CRS-C038','CRS-C039','CRS-C040',
      'CRS-C041','CRS-C042','CRS-C043','CRS-C044','CRS-C045',
      'CRS-C046','CRS-C047','CRS-C048','CRS-C049','CRS-C050'
  )
  -- Exclude CRS-C168 (Group B — already inserted)
  AND ct.category_code != 'CRS-C168'
ON CONFLICT (query_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Group D — Promote DEFERRED stubs to active (idempotent on every re-run)
-- Source: crs_phase3_validation_queries.sql
-- Strategy:
--   Part D1 — Alias codes: reuse Group A SQL via UPDATE...FROM (39 codes).
--             evaluation_strategy = COUNT_ZERO, has_parameters = false.
--   Part D2 — Unique codes: canonical 4-column-contract SQL via INSERT...DO UPDATE (72 codes).
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- Part D1 — Alias codes: reuse Group A SQL (batch UPDATE per source code)
-- ---------------------------------------------------------------------------

-- D1.01: CRS-C051, CRS-C052, CRS-C177 → CRS-C007 (area_code FK/NA check)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C007: area_code_raw invalid, literal NA, or contains comma',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C007'
  AND d.query_code IN ('CRS-C051', 'CRS-C052', 'CRS-C177');

-- D1.02: CRS-C060 → CRS-C034 (doc-area code missing)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C034: documents linked to tags without area_id',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C034'
  AND d.query_code = 'CRS-C060';

-- D1.03: CRS-C062, CRS-C080 → CRS-C040 (equipment without doc mapping)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C040: equipment tags with no active tag_document mapping',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C040'
  AND d.query_code IN ('CRS-C062', 'CRS-C080');

-- D1.04: CRS-C071 → CRS-C035 (doc-PU missing)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C035: documents linked to tags without process_unit_id',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C035'
  AND d.query_code = 'CRS-C071';

-- D1.05: CRS-C074 → CRS-C032 (doc in mapping not in DocMaster)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C032: doc_number_raw in tag_document not found in project_core.document',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C032'
  AND d.query_code = 'CRS-C074';

-- D1.06: CRS-C075 → CRS-C033 (tag in mapping not in MTR)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C033: tag_name_raw in tag_document not found in project_core.tag',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C033'
  AND d.query_code = 'CRS-C075';

-- D1.07: CRS-C077, CRS-C078 → CRS-C030 (doc NYI/CAN status)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C030: document with NYI/CAN status or NULL status',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C030'
  AND d.query_code IN ('CRS-C077', 'CRS-C078');

-- D1.08: CRS-C086 → CRS-C031 (tag without doc reference)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C031: active tag with no active entry in mapping.tag_document',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C031'
  AND d.query_code = 'CRS-C086';

-- D1.09: CRS-C091, CRS-C092 → CRS-C023 (equipment class not in RDL)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C023: equipment class_id NULL but tag_class_raw provided',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C023'
  AND d.query_code IN ('CRS-C091', 'CRS-C092');

-- D1.10: CRS-C096 → CRS-C024 (equipment description blank)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C024: equipment tag with NULL or empty description',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C024'
  AND d.query_code = 'CRS-C096';

-- D1.11: CRS-C106 → CRS-C028 (equipment tag_name not in MTR)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C028: equipment row with equip_no that is inactive or has no tag_name',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C028'
  AND d.query_code = 'CRS-C106';

-- D1.12: CRS-C110 → CRS-C025 (manufacturer serial blank/NA)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C025: manufacturer serial_no blank, NULL, or literal NA',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C025'
  AND d.query_code = 'CRS-C110';

-- D1.13: CRS-C112 → CRS-C027 (manufacturer company blank)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C027: manufacturer_id NULL and manufacturer_company_raw blank',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C027'
  AND d.query_code = 'CRS-C112';

-- D1.14: CRS-C126, CRS-C127 → CRS-C026 (model part blank)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C026: model_id NULL and model_part_raw blank',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C026'
  AND d.query_code IN ('CRS-C126', 'CRS-C127');

-- D1.15: CRS-C138 → CRS-C036 (PO code not in register)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C036: po_code_raw provided but po_id not resolved',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C036'
  AND d.query_code = 'CRS-C138';

-- D1.16: CRS-C139 → CRS-C037 (PO date missing)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C037: active purchase orders without po_date',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C037'
  AND d.query_code = 'CRS-C139';

-- D1.17: CRS-C141 → CRS-C038 (company name missing for PO / receiver company missing)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C038: PO without issuer company or equipment without manufacturer',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C038'
  AND d.query_code = 'CRS-C141';

-- D1.18: CRS-C163 → CRS-C010 (parent tag missing for physical)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C010: physical tags (valve/pipe/pump/…) without parent_tag',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C010'
  AND d.query_code = 'CRS-C163';

-- D1.19: CRS-C164 → CRS-C011 (parent tag not in MTR)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C011: parent_tag_raw provided but parent_tag_id not resolved',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C011'
  AND d.query_code = 'CRS-C164';

-- D1.20: CRS-C166 → CRS-C012 (pipe parent is pipe)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C012: pipe tag with pipe parent (both class names contain ''pipe'')',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C012'
  AND d.query_code = 'CRS-C166';

-- D1.21: CRS-C170 → CRS-C015 (production critical blank)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C015: production_critical_item NULL or blank',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C015'
  AND d.query_code = 'CRS-C170';

-- D1.22: CRS-C171 → CRS-C013 (safety critical invalid)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C013: safety_critical_item blank or not in (YES/NO/Y/N)',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C013'
  AND d.query_code = 'CRS-C171';

-- D1.23: CRS-C174 → CRS-C014 (safety critical reason missing)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C014: SECE/YES tags without safety_critical_item_reason_awarded',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C014'
  AND d.query_code = 'CRS-C174';

-- D1.24: CRS-C176 → CRS-C006 (area code blank)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C006: area_id is NULL (area code blank or not submitted)',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C006'
  AND d.query_code = 'CRS-C176';

-- D1.25: CRS-C178, CRS-C180 → CRS-C004 (tag class not in ISM/RDL)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C004: class_id NULL while tag_class_raw provided — not in ontology_core.class',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C004'
  AND d.query_code IN ('CRS-C178', 'CRS-C180');

-- D1.26: CRS-C182 → CRS-C002 (tag description blank)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C002: active tags with NULL or empty description',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C002'
  AND d.query_code = 'CRS-C182';

-- D1.27: CRS-C184 → CRS-C003 (tag description too long > 255 chars)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C003: tag description length > 255 characters',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C003'
  AND d.query_code = 'CRS-C184';

-- D1.28: CRS-C196 → CRS-C029 (plant code invalid)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C029: plant_raw provided but plant_id not resolved',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C029'
  AND d.query_code = 'CRS-C196';

-- D1.29: CRS-C197, CRS-C199 → CRS-C009 (process unit not in register or is NA)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C009: process_unit_raw provided but not resolved or is literal NA',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C009'
  AND d.query_code IN ('CRS-C197', 'CRS-C199');

-- D1.30: CRS-C198 → CRS-C008 (process unit missing)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C008: process_unit_id is NULL (mandatory field not submitted)',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C008'
  AND d.query_code = 'CRS-C198';

-- D1.31: CRS-C202 → CRS-C005 (TNC violated)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C005: tag name not starting with JDA- (TNC violation)',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C005'
  AND d.query_code = 'CRS-C202';

-- D1.32: CRS-C206 → CRS-C039 (duplicate physical connections)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C039: duplicate from_tag_raw/to_tag_raw connection pairs',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C039'
  AND d.query_code = 'CRS-C206';

-- D1.33: CRS-C208 → CRS-C045 (FROM/TO tag not in MTR)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C045: from_tag_raw or to_tag_raw not resolved to tag FK',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C045'
  AND d.query_code = 'CRS-C208';

-- D1.34: CRS-C221 → CRS-C017 (tag property orphan — property rows with inactive/missing tag)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C017: property_value rows referencing tags that are inactive or missing',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C017'
  AND d.query_code = 'CRS-C221';

-- D1.35: CRS-C222 → CRS-C022 (mandatory property missing)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C022: mandatory class properties not submitted per RDL class_property',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C022'
  AND d.query_code = 'CRS-C222';

-- D1.36: CRS-C223 → CRS-C020 (property class mapping mismatch)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C020: property_code_raw not in allowed set for tag class',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C020'
  AND d.query_code = 'CRS-C223';

-- D1.37: CRS-C224 → CRS-C021 (tag without any properties)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C021: active tags with no property_value records',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C021'
  AND d.query_code = 'CRS-C224';

-- D1.38: CRS-C227 → CRS-C019 (property value is zero)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C019: property value is exact string "0"',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C019'
  AND d.query_code = 'CRS-C227';

-- D1.39: CRS-C229 → CRS-C018 (property UOM present when value is NA)
UPDATE audit_core.crs_validation_query d
SET sql_query           = a.sql_query,
    is_active           = true,
    evaluation_strategy = 'COUNT_ZERO',
    has_parameters      = false,
    parameter_names     = NULL,
    notes               = 'Alias for CRS-C018: property value is NA/N/A but property_uom_raw is non-empty',
    updated_at          = now()
FROM audit_core.crs_validation_query a
WHERE a.query_code = 'CRS-C018'
  AND d.query_code = 'CRS-C229';

-- ---------------------------------------------------------------------------
-- Part D2 — Unique codes: canonical SQL from crs_phase3_validation_queries.sql
-- Output contract: object_key TEXT, check_field TEXT, actual_value TEXT, is_resolved BOOL
-- ---------------------------------------------------------------------------

-- ── TAG DOMAIN ──────────────────────────────────────────────────────────────

-- CRS-C142: abstract tag class used (is_abstract = TRUE)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C142',
    'Abstract tag class used',
    'Tags whose assigned class has is_abstract = TRUE in ontology_core.class',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c142$
SELECT
  t.tag_name AS object_key,
  'class_is_abstract' AS check_field,
  COALESCE(c.name || ' (abstract=' || c.is_abstract::TEXT || ')', 'NULL') AS actual_value,
  (c.is_abstract IS NULL OR c.is_abstract = FALSE) AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c142$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. Abstract ontology classes must not be used on physical tags.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C144: comma instead of point in tag name
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C144',
    'Comma in tag_name',
    'Tag names containing a comma character (should use period/dot as separator)',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c144$
SELECT
  t.tag_name AS object_key,
  'tag_name_comma' AS check_field,
  t.tag_name AS actual_value,
  (t.tag_name NOT LIKE '%,%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c144$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. Tag name must not contain commas.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C145: design company FK not resolved (designed_by_company_name)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C145',
    'DESIGNED_BY_COMPANY not in register',
    'Tags where design_company_name_raw provided but design_company_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c145$
SELECT
  t.tag_name AS object_key,
  'design_company' AS check_field,
  COALESCE(co.name, t.design_company_name_raw, 'NULL') AS actual_value,
  (t.design_company_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.design_company_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c145$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. design_company_name_raw must resolve to reference_core.company.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C146: same check — design company FK (broader category scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C146',
    'DESIGNED_BY_COMPANY not in register (C146)',
    'Tags where design_company_name_raw provided but design_company_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c146$
SELECT
  t.tag_name AS object_key,
  'design_company' AS check_field,
  COALESCE(co.name, t.design_company_name_raw, 'NULL') AS actual_value,
  (t.design_company_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.design_company_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c146$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C145. EIS-file: 003.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C147: same check — design company FK
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C147',
    'DESIGNED_BY_COMPANY not in register (C147)',
    'Tags where design_company_name_raw provided but design_company_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c147$
SELECT
  t.tag_name AS object_key,
  'design_company' AS check_field,
  COALESCE(co.name, t.design_company_name_raw, 'NULL') AS actual_value,
  (t.design_company_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.design_company_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c147$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C145. EIS-file: 003.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C148: same check — design company FK
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C148',
    'DESIGNED_BY_COMPANY not in register (C148)',
    'Tags where design_company_name_raw provided but design_company_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c148$
SELECT
  t.tag_name AS object_key,
  'design_company' AS check_field,
  COALESCE(co.name, t.design_company_name_raw, 'NULL') AS actual_value,
  (t.design_company_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.design_company_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c148$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C145. EIS-file: 003.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C149: same check — design company FK
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C149',
    'DESIGNED_BY_COMPANY not in register (C149)',
    'Tags where design_company_name_raw provided but design_company_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c149$
SELECT
  t.tag_name AS object_key,
  'design_company' AS check_field,
  COALESCE(co.name, t.design_company_name_raw, 'NULL') AS actual_value,
  (t.design_company_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.design_company_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c149$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C145. EIS-file: 003.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C150: control panel CP prefix in tag name (TNC)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C150',
    'CP prefix in tag name (TNC)',
    'Tag names containing -CP- or -cp- pattern (control panel prefix check)',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c150$
SELECT
  t.tag_name AS object_key,
  'tag_name_cp_pattern' AS check_field,
  t.tag_name AS actual_value,
  (t.tag_name NOT SIMILAR TO '%-(CP|cp)-%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c150$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. Control panel CP pattern must conform to TNC.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C152: same check — design company FK (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C152',
    'DESIGNED_BY_COMPANY not in register (C152)',
    'Tags where design_company_name_raw provided but design_company_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c152$
SELECT
  t.tag_name AS object_key,
  'design_company' AS check_field,
  COALESCE(co.name, t.design_company_name_raw, 'NULL') AS actual_value,
  (t.design_company_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.design_company_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c152$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C145. EIS-file: 003.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C154: SECE mapping missing for safety-critical (YES) tags
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C154',
    'SECE mapping missing for safety-critical tags',
    'Safety-critical (YES/Y) tags without active entry in mapping.tag_sece',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c154$
SELECT
  t.tag_name AS object_key,
  'sece_mapping' AS check_field,
  (SELECT STRING_AGG(s.code, '; ')
   FROM mapping.tag_sece ts
   JOIN reference_core.sece s ON s.id = ts.sece_id
   WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_sece ts
    WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND t.tag_name = ANY(:tag_names);
    $sql_c154$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. SECE/YES tags must have at least one active SECE mapping.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C157: same SECE EXISTS check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C157',
    'SECE mapping missing for safety-critical tags (C157)',
    'Safety-critical (YES/Y) tags without active entry in mapping.tag_sece',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c157$
SELECT
  t.tag_name AS object_key,
  'sece_mapping' AS check_field,
  (SELECT STRING_AGG(s.code, '; ')
   FROM mapping.tag_sece ts
   JOIN reference_core.sece s ON s.id = ts.sece_id
   WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_sece ts
    WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND t.tag_name = ANY(:tag_names);
    $sql_c157$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C154. EIS-file: 003.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C158: multiple SECE groups assigned (> 1 SECE per tag)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C158',
    'Multiple SECE groups on one tag',
    'Tags with more than one active SECE mapping (COUNT > 1)',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c158$
SELECT
  t.tag_name AS object_key,
  'sece_count' AS check_field,
  COUNT(ts.id)::TEXT AS actual_value,
  (COUNT(ts.id) <= 1) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_sece ts ON ts.tag_id = t.id AND ts.mapping_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.tag_name;
    $sql_c158$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. A tag must not belong to more than one SECE group.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C167: pipe tag description missing FROM-TO reference
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C167',
    'Pipe tag description missing FROM-TO',
    'Pipe-class tags whose description does not contain FROM/TO or dash routing reference',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c167$
SELECT
  t.tag_name AS object_key,
  'description_from_to' AS check_field,
  LEFT(COALESCE(t.description,''), 100) AS actual_value,
  (t.description ILIKE '%from%' OR t.description ILIKE '%to%'
   OR t.description ILIKE '%-%') AS is_resolved
FROM project_core.tag t
JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND c.name ILIKE '%pipe%'
  AND t.tag_name = ANY(:tag_names);
    $sql_c167$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. Pipe tag descriptions should include from/to routing.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C172: same SECE EXISTS check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C172',
    'SECE mapping missing for safety-critical tags (C172)',
    'Safety-critical (YES/Y) tags without active entry in mapping.tag_sece',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c172$
SELECT
  t.tag_name AS object_key,
  'sece_mapping' AS check_field,
  (SELECT STRING_AGG(s.code, '; ')
   FROM mapping.tag_sece ts
   JOIN reference_core.sece s ON s.id = ts.sece_id
   WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_sece ts
    WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND t.tag_name = ANY(:tag_names);
    $sql_c172$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C154. EIS-file: 003.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C173: same SECE EXISTS check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C173',
    'SECE mapping missing for safety-critical tags (C173)',
    'Safety-critical (YES/Y) tags without active entry in mapping.tag_sece',
    'SAFETY', 'Safety-critical attribute checks in project_core.tag',
    $sql_c173$
SELECT
  t.tag_name AS object_key,
  'sece_mapping' AS check_field,
  (SELECT STRING_AGG(s.code, '; ')
   FROM mapping.tag_sece ts
   JOIN reference_core.sece s ON s.id = ts.sece_id
   WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_sece ts
    WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND t.tag_name = ANY(:tag_names);
    $sql_c173$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C154. EIS-file: 003.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C175: supplier/vendor company not in register
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C175',
    'Vendor/supplier company not in register',
    'Tags where vendor_company_raw provided but vendor_id not resolved',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c175$
SELECT
  t.tag_name AS object_key,
  'vendor_company' AS check_field,
  COALESCE(co.name, t.vendor_company_raw, 'NULL') AS actual_value,
  (t.vendor_id IS NOT NULL OR t.vendor_company_raw IS NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.vendor_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c175$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. vendor_company_raw must resolve to reference_core.company.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C183: description format issues (starts/ends with dash or has NA suffix)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C183',
    'Description format issue (dash/NA pattern)',
    'Tags where description starts with dash, ends with dash, or ends with ", NA"',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c183$
SELECT
  t.tag_name AS object_key,
  'description_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NOT NULL
    AND NOT TRIM(t.description) ~ '^-'
    AND NOT TRIM(t.description) ~ '-$'
    AND NOT t.description ILIKE '%, NA'
    AND t.tag_name NOT LIKE '%-') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c183$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. Description must not start/end with dash or use NA suffix format.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C185: double spaces in description
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C185',
    'Double spaces in description',
    'Tags where description contains two or more consecutive spaces',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c185$
SELECT
  t.tag_name AS object_key,
  'description_spaces' AS check_field,
  LEFT(COALESCE(t.description,''), 80) AS actual_value,
  (t.description IS NULL OR t.description NOT LIKE '%  %') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c185$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. Description must not contain consecutive double spaces.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C189: same description format check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C189',
    'Description format issue (dash/NA pattern) (C189)',
    'Tags where description starts with dash, ends with dash, or ends with ", NA"',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c189$
SELECT
  t.tag_name AS object_key,
  'description_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NOT NULL
    AND NOT TRIM(t.description) ~ '^-'
    AND NOT TRIM(t.description) ~ '-$'
    AND NOT t.description ILIKE '%, NA'
    AND t.tag_name NOT LIKE '%-') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c189$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C183. EIS-file: 003.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C191: same description format check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C191',
    'Description format issue (dash/NA pattern) (C191)',
    'Tags where description starts with dash, ends with dash, or ends with ", NA"',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c191$
SELECT
  t.tag_name AS object_key,
  'description_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NOT NULL
    AND NOT TRIM(t.description) ~ '^-'
    AND NOT TRIM(t.description) ~ '-$'
    AND NOT t.description ILIKE '%, NA'
    AND t.tag_name NOT LIKE '%-') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c191$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C183. EIS-file: 003.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C193: tag is its own parent (self-referential parent_tag_id)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C193',
    'Tag is own parent (self-loop)',
    'Tags where parent_tag_id = id (self-referential parent)',
    'TOPOLOGY', 'Topology and physical connection checks',
    $sql_c193$
SELECT
  t.tag_name AS object_key,
  'self_parent' AS check_field,
  COALESCE(t.parent_tag_raw, 'NULL') AS actual_value,
  (t.parent_tag_id IS NULL OR t.parent_tag_id != t.id) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c193$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003. A tag must not reference itself as parent.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C194: same description format check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C194',
    'Description format issue (dash/NA pattern) (C194)',
    'Tags where description starts with dash, ends with dash, or ends with ", NA"',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c194$
SELECT
  t.tag_name AS object_key,
  'description_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NOT NULL
    AND NOT TRIM(t.description) ~ '^-'
    AND NOT TRIM(t.description) ~ '-$'
    AND NOT t.description ILIKE '%, NA'
    AND t.tag_name NOT LIKE '%-') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c194$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C183. EIS-file: 003.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C200: tag not matched with any doc-tag mapping
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C200',
    'Tag not matched with doc-tag reference',
    'Active tags with no active document link in mapping.tag_document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c200$
SELECT
  t.tag_name AS object_key,
  'doc_tag_mapping_exists' AS check_field,
  COALESCE(STRING_AGG(d.doc_number, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.tag_name;
    $sql_c200$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 016. Every active tag should have at least one document link.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- ── TAG_PROPERTY DOMAIN ─────────────────────────────────────────────────────

-- CRS-C215: property value has invalid format (digit-G-digit or double-space pattern)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C215',
    'Property value invalid format (encoding/spacing)',
    'Property values matching digit-G-digit pattern or containing double spaces',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c215$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'property_value_format' AS check_field,
  COALESCE(pv.property_value,'NULL') AS actual_value,
  (pv.property_value IS NULL
   OR (pv.property_value NOT SIMILAR TO '.*[0-9]+G[0-9]+.*'
       AND pv.property_value NOT SIMILAR TO '.*\s{2,}.*')) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c215$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 010/011. Property values must not contain encoding artefacts or double spaces.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C217: duplicate tag property entries (AGGREGATE — no params)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C217',
    'Duplicate tag property entries',
    'Property rows with duplicate (tag_name_raw, property_code_raw) combinations',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c217$
SELECT
  tag_name_raw || '.' || property_code_raw AS object_key,
  'property_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.property_value
WHERE object_status = 'Active'
GROUP BY tag_name_raw, property_code_raw
HAVING COUNT(*) > 1;
    $sql_c217$,
    'No violating rows (empty result = pass)', false, NULL,
    'EIS-file: 010. AGGREGATE check — no :tag_names filter needed.',
    true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C218: same property value format check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C218',
    'Property value invalid format (encoding/spacing) (C218)',
    'Property values matching digit-G-digit pattern or containing double spaces',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c218$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'property_value_format' AS check_field,
  COALESCE(pv.property_value,'NULL') AS actual_value,
  (pv.property_value IS NULL
   OR (pv.property_value NOT SIMILAR TO '.*[0-9]+G[0-9]+.*'
       AND pv.property_value NOT SIMILAR TO '.*\s{2,}.*')) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c218$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C215. EIS-file: 010/011.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C226: property value blank
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C226',
    'Property value blank',
    'Property rows where property_value is NULL or empty string',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c226$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'property_value_blank' AS check_field,
  COALESCE(pv.property_value, 'NULL') AS actual_value,
  (pv.property_value IS NOT NULL AND TRIM(pv.property_value) != '') AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c226$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 010/011. Property value must not be NULL or blank.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C228: UOM missing for numeric property value
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C228',
    'UOM missing for numeric property value',
    'Property rows where value starts with a digit but property_uom_raw is NULL or blank',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c228$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'uom_for_numeric' AS check_field,
  COALESCE(pv.property_uom_raw, 'NULL') AS actual_value,
  (pv.property_value IS NULL
   OR NOT pv.property_value ~ '^[0-9]'
   OR (pv.property_uom_raw IS NOT NULL AND TRIM(pv.property_uom_raw) != '')) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c228$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 010/011. Numeric property values must have a unit of measure.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- ── EQUIPMENT DOMAIN ─────────────────────────────────────────────────────────

-- CRS-C094: equipment description duplicated (AGGREGATE — no params)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C094',
    'Duplicate equipment descriptions',
    'Multiple equipment tags sharing identical description text',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c094$
SELECT
  t.description AS object_key,
  'description_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.description IS NOT NULL
  AND t.description != ''
GROUP BY t.description
HAVING COUNT(*) > 1;
    $sql_c094$,
    'No violating rows (empty result = pass)', false, NULL,
    'EIS-file: 004. AGGREGATE check — no :tag_names filter.',
    true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C095: equipment description starts or ends with dash
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C095',
    'Equipment description starts/ends with dash',
    'Equipment tags where TRIM(description) starts or ends with a dash character',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c095$
SELECT
  t.equip_no AS object_key,
  'description_dash_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NULL
   OR (NOT TRIM(t.description) ~ '^-' AND NOT TRIM(t.description) ~ '-$')) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c095$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004. Equipment descriptions must not start or end with a dash.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C098: same dash check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C098',
    'Equipment description starts/ends with dash (C098)',
    'Equipment tags where TRIM(description) starts or ends with a dash character',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c098$
SELECT
  t.equip_no AS object_key,
  'description_dash_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NULL
   OR (NOT TRIM(t.description) ~ '^-' AND NOT TRIM(t.description) ~ '-$')) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c098$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C095. EIS-file: 004.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C100: equipment has no document references
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C100',
    'Equipment has no document references',
    'Equipment tags with no active entry in mapping.tag_document',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c100$
SELECT
  t.equip_no AS object_key,
  'equip_doc_mapping' AS check_field,
  COALESCE(STRING_AGG(d.doc_number, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.equip_no;
    $sql_c100$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 019. Every equipment tag should have at least one document link.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C101: equipment is its own parent (self-loop)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C101',
    'Equipment is own parent (self-loop)',
    'Equipment tags where parent_tag_id = id (self-referential)',
    'TOPOLOGY', 'Topology and physical connection checks',
    $sql_c101$
SELECT
  t.equip_no AS object_key,
  'self_parent_equip' AS check_field,
  COALESCE(t.parent_tag_raw, 'NULL') AS actual_value,
  (t.parent_tag_id IS NULL OR t.parent_tag_id != t.id) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c101$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004. Equipment must not reference itself as parent tag.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C103: equipment number missing plant code prefix
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C103',
    'Equipment number missing plant prefix',
    'Equipment tags where equip_no does not start with Equip_ or JDA',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c103$
SELECT
  t.equip_no AS object_key,
  'equip_no_prefix' AS check_field,
  COALESCE(t.equip_no, 'NULL') AS actual_value,
  (t.equip_no LIKE 'Equip_%' OR t.equip_no LIKE 'JDA%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c103$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004. equip_no must start with Equip_ or plant prefix JDA.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C105: equipment plant code not in register
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C105',
    'Equipment plant code not in register',
    'Equipment tags where plant_id is NULL (not resolved to reference_core.plant)',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c105$
SELECT
  t.equip_no AS object_key,
  'plant_id_equip' AS check_field,
  COALESCE(pl.code, t.plant_raw, 'NULL') AS actual_value,
  (t.plant_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c105$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004. plant_raw must resolve to reference_core.plant.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C107: equipment TNC non-compliance
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C107',
    'Equipment TNC non-compliance',
    'Equipment tags where equip_no does not match pattern Equip_JDA-',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c107$
SELECT
  t.equip_no AS object_key,
  'equip_no_tnc' AS check_field,
  COALESCE(t.equip_no, 'NULL') AS actual_value,
  (t.equip_no LIKE 'Equip_JDA-%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c107$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004. equip_no must follow pattern Equip_JDA-<tag_name>.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C111: manufacturer serial number is literal NA
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C111',
    'Serial number is literal NA',
    'Equipment tags where serial_no is "NA", "N/A", or "NOT APPLICABLE"',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c111$
SELECT
  t.equip_no AS object_key,
  'serial_no_not_na' AS check_field,
  COALESCE(t.serial_no, 'NULL') AS actual_value,
  (t.serial_no IS NULL
   OR UPPER(TRIM(t.serial_no)) NOT IN ('NA','N/A','NOT APPLICABLE')) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c111$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004. Serial number must not be a pseudo-null NA value.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C113: model part FK not resolved
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C113',
    'Model part FK not resolved',
    'Equipment tags where model_id is NULL (model_part_raw provided but not resolved)',
    'EQUIPMENT', 'Equipment register checks in project_core.tag',
    $sql_c113$
SELECT
  t.equip_no AS object_key,
  'model_part' AS check_field,
  COALESCE(mp.name, t.model_part_raw, 'NULL') AS actual_value,
  (t.model_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.model_part mp ON mp.id = t.model_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c113$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004/005. model_part_raw must resolve to reference_core.model_part.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- ── EQUIPMENT_PROPERTY DOMAIN ────────────────────────────────────────────────

-- CRS-C115: duplicate equipment property entries (filtered AGGREGATE)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C115',
    'Duplicate equipment property entries',
    'Equipment property rows with duplicate (tag_name_raw, property_code_raw) combinations',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c115$
SELECT
  tag_name_raw || '.' || property_code_raw AS object_key,
  'equip_property_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.property_value
WHERE object_status = 'Active'
  AND tag_name_raw = ANY(:tag_names)
GROUP BY tag_name_raw, property_code_raw
HAVING COUNT(*) > 1;
    $sql_c115$,
    'No violating rows (empty result = pass)', true, ARRAY['tag_names'],
    'EIS-file: 011. Filtered aggregate — duplicate property entries per equipment.',
    true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C116: equipment class-property mapping mismatch
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C116',
    'Equipment property not in class scope',
    'Equipment property values where property_id or mapping_id is not resolved',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c116$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'equip_property_class_scope' AS check_field,
  COALESCE(pv.property_code_raw,'NULL') AS actual_value,
  (pv.property_id IS NOT NULL AND pv.mapping_id IS NOT NULL) AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c116$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 011. Equipment property must exist in class_property mapping.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C117: equipment has no properties (filtered COUNT_ZERO)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C117',
    'Equipment has no property values',
    'Equipment tags with no active property_value records',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c117$
SELECT
  t.equip_no AS object_key,
  'equip_has_properties' AS check_field,
  COUNT(pv.id)::TEXT AS actual_value,
  EXISTS (
    SELECT 1 FROM project_core.property_value pv2
    WHERE pv2.tag_id = t.id AND pv2.object_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN project_core.property_value pv ON pv.tag_id = t.id AND pv.object_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.equip_no;
    $sql_c117$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 011. Every equipment tag should have at least one property record.',
    true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C118: equipment property register orphan
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C118',
    'Equipment property orphan (tag not in register)',
    'Property rows for tags that have no equip_no or are not in project_core.tag',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c118$
SELECT
  pv.tag_name_raw AS object_key,
  'equip_in_register' AS check_field,
  COALESCE(t.equip_no, 'NOT_IN_REGISTER') AS actual_value,
  (t.id IS NOT NULL AND t.equip_no IS NOT NULL) AS is_resolved
FROM project_core.property_value pv
LEFT JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c118$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 011. Equipment property rows must reference a tag with equip_no.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C119: same equipment property orphan check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C119',
    'Equipment property orphan (tag not in register) (C119)',
    'Property rows for tags that have no equip_no or are not in project_core.tag',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c119$
SELECT
  pv.tag_name_raw AS object_key,
  'equip_in_register' AS check_field,
  COALESCE(t.equip_no, 'NOT_IN_REGISTER') AS actual_value,
  (t.id IS NOT NULL AND t.equip_no IS NOT NULL) AS is_resolved
FROM project_core.property_value pv
LEFT JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c119$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C118. EIS-file: 011.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C121: equipment property value issues (blank/zero/NA+UOM)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C121',
    'Equipment property value issue (blank/zero/NA+UOM)',
    'Equipment property rows where value is blank, zero, or NA with non-empty UOM',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c121$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'equip_property_value' AS check_field,
  COALESCE(pv.property_value,'NULL') || ' | ' || COALESCE(pv.property_uom_raw,'') AS actual_value,
  (pv.property_value IS NOT NULL
   AND TRIM(pv.property_value) != ''
   AND TRIM(COALESCE(pv.property_value,'')) != '0'
   AND NOT (UPPER(TRIM(COALESCE(pv.property_value,''))) IN ('NA','N/A')
            AND pv.property_uom_raw IS NOT NULL
            AND TRIM(pv.property_uom_raw) != '')) AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c121$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 011. Equipment property value must be non-blank, non-zero, and not NA with UOM.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C122: same equipment property value check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C122',
    'Equipment property value issue (blank/zero/NA+UOM) (C122)',
    'Equipment property rows where value is blank, zero, or NA with non-empty UOM',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c122$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'equip_property_value' AS check_field,
  COALESCE(pv.property_value,'NULL') || ' | ' || COALESCE(pv.property_uom_raw,'') AS actual_value,
  (pv.property_value IS NOT NULL
   AND TRIM(pv.property_value) != ''
   AND TRIM(COALESCE(pv.property_value,'')) != '0'
   AND NOT (UPPER(TRIM(COALESCE(pv.property_value,''))) IN ('NA','N/A')
            AND pv.property_uom_raw IS NOT NULL
            AND TRIM(pv.property_uom_raw) != '')) AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c122$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C121. EIS-file: 011.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C123: same equipment class-property scope check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C123',
    'Equipment property not in class scope (C123)',
    'Equipment property values where property_id or mapping_id is not resolved',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c123$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'equip_property_class_scope' AS check_field,
  COALESCE(pv.property_code_raw,'NULL') AS actual_value,
  (pv.property_id IS NOT NULL AND pv.mapping_id IS NOT NULL) AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c123$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C116. EIS-file: 011.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C124: same equipment property value check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C124',
    'Equipment property value issue (blank/zero/NA+UOM) (C124)',
    'Equipment property rows where value is blank, zero, or NA with non-empty UOM',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c124$
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'equip_property_value' AS check_field,
  COALESCE(pv.property_value,'NULL') || ' | ' || COALESCE(pv.property_uom_raw,'') AS actual_value,
  (pv.property_value IS NOT NULL
   AND TRIM(pv.property_value) != ''
   AND TRIM(COALESCE(pv.property_value,'')) != '0'
   AND NOT (UPPER(TRIM(COALESCE(pv.property_value,''))) IN ('NA','N/A')
            AND pv.property_uom_raw IS NOT NULL
            AND TRIM(pv.property_uom_raw) != '')) AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND pv.tag_name_raw = ANY(:tag_names);
    $sql_c124$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C121. EIS-file: 011.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- ── DOCUMENT DOMAIN ──────────────────────────────────────────────────────────

-- CRS-C058: PO company (issuer) in doc-PO not in company register
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C058',
    'Doc-PO issuer company not in register',
    'Documents where the PO issuer company is not found in reference_core.company',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c058$
SELECT
  d.doc_number AS object_key,
  'po_company_in_register' AS check_field,
  COALESCE(co.name, 'NOT_IN_REGISTER') AS actual_value,
  (co.id IS NOT NULL) AS is_resolved
FROM project_core.document d
JOIN mapping.document_po dpo ON dpo.document_id = d.id AND dpo.mapping_status = 'Active'
JOIN reference_core.purchase_order po ON po.id = dpo.po_id
LEFT JOIN reference_core.company co ON co.id = po.issuer_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers);
    $sql_c058$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'EIS-file: 022. PO issuer must resolve to reference_core.company.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C059: doc in docmaster (active status)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C059',
    'Document not active in DocMaster',
    'Documents where object_status != Active in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c059$
SELECT
  d.doc_number AS object_key,
  'doc_in_docmaster' AS check_field,
  d.doc_number AS actual_value,
  (d.object_status = 'Active') AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
    $sql_c059$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'EIS-file: 014. Document must be active in project_core.document.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C061: same doc active status check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C061',
    'Document not active in DocMaster (C061)',
    'Documents where object_status != Active in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c061$
SELECT
  d.doc_number AS object_key,
  'doc_in_docmaster' AS check_field,
  d.doc_number AS actual_value,
  (d.object_status = 'Active') AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
    $sql_c061$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'Alias scope of CRS-C059. EIS-file: 014.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C065: same doc active status check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C065',
    'Document not active in DocMaster (C065)',
    'Documents where object_status != Active in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c065$
SELECT
  d.doc_number AS object_key,
  'doc_in_docmaster' AS check_field,
  d.doc_number AS actual_value,
  (d.object_status = 'Active') AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
    $sql_c065$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'Alias scope of CRS-C059. EIS-file: 014.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C066: PO in doc-PO mapping is void or inactive
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C066',
    'Doc-PO link to void/inactive PO',
    'Documents linked to PO records that are not active or not found',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c066$
SELECT
  d.doc_number AS object_key,
  'doc_po_link' AS check_field,
  COALESCE(STRING_AGG(po.code, '; '), 'NULL') AS actual_value,
  NOT EXISTS (
    SELECT 1 FROM mapping.document_po dpo
    JOIN reference_core.purchase_order po2 ON po2.id = dpo.po_id
    WHERE dpo.document_id = d.id
      AND dpo.mapping_status = 'Active'
      AND (po2.id IS NULL OR po2.object_status != 'Active')
  ) AS is_resolved
FROM project_core.document d
LEFT JOIN mapping.document_po dpo ON dpo.document_id = d.id AND dpo.mapping_status = 'Active'
LEFT JOIN reference_core.purchase_order po ON po.id = dpo.po_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers)
GROUP BY d.id, d.doc_number;
    $sql_c066$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'EIS-file: 022. All POs linked to documents must be active.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C067: same doc active status check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C067',
    'Document not active in DocMaster (C067)',
    'Documents where object_status != Active in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c067$
SELECT
  d.doc_number AS object_key,
  'doc_in_docmaster' AS check_field,
  d.doc_number AS actual_value,
  (d.object_status = 'Active') AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
    $sql_c067$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'Alias scope of CRS-C059. EIS-file: 014.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C068: same doc active status check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C068',
    'Document not active in DocMaster (C068)',
    'Documents where object_status != Active in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c068$
SELECT
  d.doc_number AS object_key,
  'doc_in_docmaster' AS check_field,
  d.doc_number AS actual_value,
  (d.object_status = 'Active') AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
    $sql_c068$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'Alias scope of CRS-C059. EIS-file: 014.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C069: document plant code not in register
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C069',
    'Document plant code not in register',
    'Documents where plant_id is NULL (not resolved to reference_core.plant)',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c069$
SELECT
  d.doc_number AS object_key,
  'doc_plant_id' AS check_field,
  COALESCE(pl.code, 'NULL') AS actual_value,
  (d.plant_id IS NOT NULL) AS is_resolved
FROM project_core.document d
LEFT JOIN reference_core.plant pl ON pl.id = d.plant_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers);
    $sql_c069$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'EIS-file: 023. Document must reference a valid plant.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C070: document process unit not in register (via linked tags)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C070',
    'Document process unit not in register',
    'Documents where no linked tag has a resolved process_unit_id',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c070$
SELECT
  d.doc_number AS object_key,
  'doc_pu_in_register' AS check_field,
  COALESCE(STRING_AGG(DISTINCT pu.code, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    JOIN project_core.tag t ON t.id = td.tag_id
    JOIN reference_core.process_unit pu2 ON pu2.id = t.process_unit_id
    WHERE td.document_id = d.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.document d
LEFT JOIN mapping.tag_document td ON td.document_id = d.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.tag t ON t.id = td.tag_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers)
GROUP BY d.id, d.doc_number;
    $sql_c070$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'EIS-file: 018. Document must link to at least one tag with a process unit.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C073: same doc active status check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C073',
    'Document not active in DocMaster (C073)',
    'Documents where object_status != Active in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c073$
SELECT
  d.doc_number AS object_key,
  'doc_in_docmaster' AS check_field,
  d.doc_number AS actual_value,
  (d.object_status = 'Active') AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
    $sql_c073$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'Alias scope of CRS-C059. EIS-file: 014.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C079: duplicate document records (AGGREGATE — no params)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C079',
    'Duplicate document records',
    'Multiple active rows for the same doc_number in project_core.document',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c079$
SELECT
  doc_number AS object_key,
  'doc_number_unique' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.document
WHERE object_status = 'Active'
GROUP BY doc_number
HAVING COUNT(*) > 1;
    $sql_c079$,
    'No violating rows (empty result = pass)', false, NULL,
    'EIS-file: 014. AGGREGATE check — no :doc_numbers filter.',
    true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C087: same doc-PO link to void/inactive PO (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C087',
    'Doc-PO link to void/inactive PO (C087)',
    'Documents linked to PO records that are not active or not found',
    'DOCUMENT', 'Document master and cross-reference checks',
    $sql_c087$
SELECT
  d.doc_number AS object_key,
  'doc_po_link' AS check_field,
  COALESCE(STRING_AGG(po.code, '; '), 'NULL') AS actual_value,
  NOT EXISTS (
    SELECT 1 FROM mapping.document_po dpo
    JOIN reference_core.purchase_order po2 ON po2.id = dpo.po_id
    WHERE dpo.document_id = d.id
      AND dpo.mapping_status = 'Active'
      AND (po2.id IS NULL OR po2.object_status != 'Active')
  ) AS is_resolved
FROM project_core.document d
LEFT JOIN mapping.document_po dpo ON dpo.document_id = d.id AND dpo.mapping_status = 'Active'
LEFT JOIN reference_core.purchase_order po ON po.id = dpo.po_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers)
GROUP BY d.id, d.doc_number;
    $sql_c087$,
    'is_resolved = true for all rows', true, ARRAY['doc_numbers'],
    'Alias scope of CRS-C066. EIS-file: 022.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- ── PURCHASE_ORDER DOMAIN ───────────────────────────────────────────────────

-- CRS-C128: model part code has invalid characters (model_part domain)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C128',
    'Model part code has invalid characters',
    'Model part codes containing special characters: < > = & " '' %',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c128$
SELECT
  mp.code AS object_key,
  'model_part_code_chars' AS check_field,
  mp.code AS actual_value,
  (mp.code NOT SIMILAR TO '.*[<>=&"''%].*') AS is_resolved
FROM reference_core.model_part mp
WHERE mp.object_status = 'Active'
  AND mp.code = ANY(:tag_names);
    $sql_c128$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 005. model_part.code must not contain special characters.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C130: process unit description blank
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C130',
    'Process unit description blank',
    'Process unit records where name is NULL or empty',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c130$
SELECT
  pu.code AS object_key,
  'pu_name' AS check_field,
  COALESCE(pu.name, 'NULL') AS actual_value,
  (pu.name IS NOT NULL AND TRIM(pu.name) != '') AS is_resolved
FROM reference_core.process_unit pu
WHERE pu.object_status = 'Active'
  AND pu.code = ANY(:tag_names);
    $sql_c130$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 018. Process unit must have a non-blank name.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C132: process unit plant FK not resolved
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C132',
    'Process unit plant FK not resolved',
    'Process units where plant_id is NULL or plant is not in reference_core.plant',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c132$
SELECT
  pu.code AS object_key,
  'pu_plant_match' AS check_field,
  COALESCE(pl.code, 'NULL') AS actual_value,
  (pu.plant_id IS NOT NULL AND pl.id IS NOT NULL) AS is_resolved
FROM reference_core.process_unit pu
LEFT JOIN reference_core.plant pl ON pl.id = pu.plant_id
WHERE pu.object_status = 'Active'
  AND pu.code = ANY(:tag_names);
    $sql_c132$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 018. Process unit must reference a valid plant.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C134: process unit plant code not in standard list
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C134',
    'Process unit plant not in standard list',
    'Process units where plant_id is NULL (not linked to any registered plant)',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c134$
SELECT
  pu.code AS object_key,
  'pu_plant_in_register' AS check_field,
  COALESCE(pl.code, 'NULL') AS actual_value,
  (pu.plant_id IS NOT NULL) AS is_resolved
FROM reference_core.process_unit pu
LEFT JOIN reference_core.plant pl ON pl.id = pu.plant_id
WHERE pu.object_status = 'Active'
  AND pu.code = ANY(:tag_names);
    $sql_c134$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 018. Process unit must be assigned to a plant in reference_core.plant.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C135: multiple PO codes for same equipment
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C135',
    'Multiple PO codes for same equipment',
    'Equipment tags sharing equip_no but linked to different purchase orders',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c135$
SELECT
  t.equip_no AS object_key,
  'po_count_per_equip' AS check_field,
  COUNT(DISTINCT t.po_id)::TEXT AS actual_value,
  (COUNT(DISTINCT t.po_id) <= 1) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.equip_no;
    $sql_c135$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 004/008. An equipment must not be linked to multiple POs.',
    true, 'COUNT_ZERO'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C136: PO code is void
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C136',
    'PO code is void',
    'Tags where po_code_raw contains -VOID or VOID- pattern',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c136$
SELECT
  t.tag_name AS object_key,
  'po_not_void' AS check_field,
  COALESCE(t.po_code_raw, po.code, 'NULL') AS actual_value,
  (t.po_code_raw IS NULL
   OR (t.po_code_raw NOT ILIKE '%-VOID%'
       AND t.po_code_raw NOT ILIKE '%VOID-%')) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c136$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003/008. Tags must not reference void PO codes.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C137: PO code missing for physical tags
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C137',
    'PO code missing for physical tags',
    'Physical-concept tags where po_id is NULL',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c137$
SELECT
  t.tag_name AS object_key,
  'po_for_physical_tag' AS check_field,
  COALESCE(po.code, t.po_code_raw, 'NULL') AS actual_value,
  (t.po_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND c.concept ILIKE '%Physical%'
  AND t.tag_name = ANY(:tag_names);
    $sql_c137$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 003/008. Physical concept tags must have a PO code.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C140: PO description contains invalid characters
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C140',
    'PO description contains invalid characters',
    'Purchase orders where name contains commas or double-quotes',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c140$
SELECT
  po.code AS object_key,
  'po_name_characters' AS check_field,
  COALESCE(po.name, 'NULL') AS actual_value,
  (po.name IS NULL
   OR (po.name NOT LIKE '%,%' AND po.name NOT LIKE '%""%')) AS is_resolved
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active'
  AND po.code = ANY(:po_codes);
    $sql_c140$,
    'is_resolved = true for all rows', true, ARRAY['po_codes'],
    'EIS-file: 008. PO name must not contain commas or double-quotes. Param: :po_codes.',
    true, 'REGEX'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- ── TAG_CONNECTION DOMAIN ────────────────────────────────────────────────────

-- CRS-C207: from_tag equals to_tag (self-loop connection)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C207',
    'FROM_TAG equals TO_TAG (self-loop)',
    'Tags where from_tag_raw = to_tag_raw (cable loops back to same tag)',
    'TOPOLOGY', 'Topology and physical connection checks',
    $sql_c207$
SELECT
  t.tag_name AS object_key,
  'from_to_not_equal' AS check_field,
  COALESCE(t.from_tag_raw,'') || '->' || COALESCE(t.to_tag_raw,'') AS actual_value,
  (t.from_tag_raw IS NULL
   OR t.to_tag_raw IS NULL
   OR t.from_tag_raw != t.to_tag_raw) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
    $sql_c207$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 006. A connection must not have FROM_TAG = TO_TAG.',
    true, 'VALUE_MATCH'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C213: TO_TAG not in MTR
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C213',
    'TO_TAG not in MTR',
    'Tags with to_tag_raw that could not be resolved to a tag FK',
    'TOPOLOGY', 'Topology and physical connection checks',
    $sql_c213$
SELECT
  t.tag_name AS object_key,
  'to_tag_in_mtr' AS check_field,
  COALESCE(t.to_tag_raw, 'NULL') AS actual_value,
  (t.to_tag_raw IS NULL
   OR t.to_tag_raw = ''
   OR t.to_tag_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.to_tag_raw IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
    $sql_c213$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 006. to_tag_raw must resolve to a tag in project_core.tag.',
    true, 'FK_RESOLVED'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- ── TAG_CLASS_PROPERTY DOMAIN ────────────────────────────────────────────────

-- CRS-C203: tag class properties ISM coverage check
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C203',
    'Tag class has no ISM properties',
    'Classes in ontology_core.class with no active class_property mappings',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c203$
SELECT
  c.name AS object_key,
  'class_property_coverage' AS check_field,
  COUNT(cp.id)::TEXT AS actual_value,
  (COUNT(cp.id) > 0) AS is_resolved
FROM ontology_core.class c
LEFT JOIN ontology_core.class_property cp
  ON cp.class_id = c.id AND cp.mapping_status = 'Active'
WHERE c.object_status = 'Active'
  AND c.name = ANY(:tag_names)
GROUP BY c.id, c.name;
    $sql_c203$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'EIS-file: 009. Every active class must have at least one property mapping.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C204: same class property coverage check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C204',
    'Tag class has no ISM properties (C204)',
    'Classes in ontology_core.class with no active class_property mappings',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c204$
SELECT
  c.name AS object_key,
  'class_property_coverage' AS check_field,
  COUNT(cp.id)::TEXT AS actual_value,
  (COUNT(cp.id) > 0) AS is_resolved
FROM ontology_core.class c
LEFT JOIN ontology_core.class_property cp
  ON cp.class_id = c.id AND cp.mapping_status = 'Active'
WHERE c.object_status = 'Active'
  AND c.name = ANY(:tag_names)
GROUP BY c.id, c.name;
    $sql_c204$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C203. EIS-file: 009.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

-- CRS-C205: same class property coverage check (broader scope)
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, parameter_names,
    notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C205',
    'Tag class has no ISM properties (C205)',
    'Classes in ontology_core.class with no active class_property mappings',
    'REFERENCE', 'Reference data integrity checks',
    $sql_c205$
SELECT
  c.name AS object_key,
  'class_property_coverage' AS check_field,
  COUNT(cp.id)::TEXT AS actual_value,
  (COUNT(cp.id) > 0) AS is_resolved
FROM ontology_core.class c
LEFT JOIN ontology_core.class_property cp
  ON cp.class_id = c.id AND cp.mapping_status = 'Active'
WHERE c.object_status = 'Active'
  AND c.name = ANY(:tag_names)
GROUP BY c.id, c.name;
    $sql_c205$,
    'is_resolved = true for all rows', true, ARRAY['tag_names'],
    'Alias scope of CRS-C203. EIS-file: 009.',
    true, 'NOT_NULL'
) ON CONFLICT (query_code) DO UPDATE SET
    sql_query = EXCLUDED.sql_query, is_active = EXCLUDED.is_active,
    evaluation_strategy = EXCLUDED.evaluation_strategy,
    has_parameters = EXCLUDED.has_parameters, parameter_names = EXCLUDED.parameter_names,
    notes = EXCLUDED.notes, updated_at = now();

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
