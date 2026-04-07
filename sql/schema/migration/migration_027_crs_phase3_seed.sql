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
ORDER BY desc_length DESC;
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
SELECT tag_name, tag_class_raw, plant_raw, '1_PREFIX' AS check_type
FROM project_core.tag
WHERE object_status = 'Active'
  AND tag_name NOT LIKE 'JDA-%'

UNION ALL

SELECT tag_name, tag_class_raw, plant_raw, '2_COMMA' AS check_type
FROM project_core.tag
WHERE object_status = 'Active'
  AND tag_name ~ ','

UNION ALL

SELECT t.tag_name, c.name AS tag_class_raw, t.plant_raw, '3_PIPE_DASH' AS check_type
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND c.name ILIKE '%pipe%'
  AND t.tag_name LIKE '%-'

ORDER BY check_type, tag_name;
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
  AND t.area_code_raw IS NOT NULL AND t.area_code_raw != ''
  AND t.area_id IS NULL
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
  AND t.process_unit_raw IS NOT NULL AND t.process_unit_raw != ''
  AND t.process_unit_id IS NULL
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
SELECT tag_name, COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_name
HAVING COUNT(*) > 1
ORDER BY cnt DESC;
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
    pv.tag_name_raw,
    t.object_status,
    COUNT(pv.id) AS property_rows
FROM project_core.property_value pv
LEFT JOIN project_core.tag t ON t.id = pv.tag_id
WHERE pv.object_status = 'Active'
  AND (
      t.id IS NULL
      OR t.object_status != 'Active'
  )
GROUP BY pv.tag_name_raw, t.object_status
ORDER BY property_rows DESC;
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
    t.tag_name,
    pv.property_code_raw   AS property_code,
    pv.property_value,
    pv.property_uom_raw    AS uom
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
    t.tag_name,
    pv.property_code_raw AS property_code,
    pv.property_value,
    pv.property_uom_raw  AS uom
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
    t.equip_no      AS equipment_number,
    t.tag_name,
    t.source_id,
    t.object_status AS tag_object_status
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM project_core.tag ref
      WHERE ref.tag_name = t.tag_name
        AND ref.object_status = 'Active'
        AND ref.equip_no IS NULL
  )
ORDER BY t.equip_no;
    $sql_c028$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 004', true, 'COUNT_ZERO'
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
    po.code     AS po_code,
    po.po_date,
    COUNT(t.id) AS tags_linked
FROM reference_core.purchase_order po
LEFT JOIN project_core.tag t ON t.po_id = po.id AND t.object_status = 'Active'
WHERE po.object_status = 'Active'
  AND po.po_date IS NULL
GROUP BY po.code, po.po_date
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
SELECT po.code AS po_code, NULL AS tag_name, 'ISSUER COMPANY MISSING' AS issue
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active' AND po.issuer_id IS NULL

UNION ALL

SELECT NULL AS po_code, t.tag_name, 'NO MANUFACTURER COMPANY' AS issue
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
    from_tag_raw,
    to_tag_raw,
    COUNT(*) AS duplicate_count
FROM project_core.tag
WHERE object_status = 'Active'
  AND from_tag_raw IS NOT NULL
  AND to_tag_raw IS NOT NULL
GROUP BY from_tag_raw, to_tag_raw
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
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
    'EIS-file: 003', true, 'COUNT_ZERO'
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
  AND t.tag_class_raw ~* '(instrument|loop|signal|transmitter)'
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
    t.from_tag_raw    AS declared_from,
    'FROM_TAG NOT IN MTR' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.from_tag_raw IS NOT NULL AND TRIM(t.from_tag_raw) != ''
  AND t.from_tag_id IS NULL

UNION ALL

SELECT
    t.tag_name,
    t.to_tag_raw      AS declared_to,
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

-- CRS-C046 — TAG_STATUS outside allowed vocabulary
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C046',
    'TAG_STATUS outside allowed vocabulary',
    'Tags with tag_status values not in EIS-allowed set (ADR-011: actual values are ACTIVE/VOID/ASB/AFC/Future)',
    'TAG_DATA', 'Tag attribute completeness checks in project_core.tag',
    $sql_c046$
SELECT
    COALESCE(tag_status, '(NULL)') AS tag_status,
    COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_status
ORDER BY cnt DESC;
    $sql_c046$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 003. ADR-011: actual values ACTIVE/VOID/ASB/AFC/Future', true, 'COUNT_ZERO'
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

-- CRS-C048 — property_code_raw not in ontology
INSERT INTO audit_core.crs_validation_query (
    query_code, query_name, description, category, category_description,
    sql_query, expected_result, has_parameters, notes, is_active, evaluation_strategy
) VALUES (
    'CRS-C048',
    'property_code_raw not in ontology',
    'Property values where property_id is NULL (code not found in ontology_core.property)',
    'PROPERTY', 'Property value integrity checks in project_core.property_value',
    $sql_c048$
SELECT
    pv.property_code_raw,
    COUNT(DISTINCT pv.tag_id) AS affected_tags,
    'UNKNOWN PROPERTY CODE'   AS issue
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.property_id IS NULL
  AND pv.property_code_raw IS NOT NULL AND pv.property_code_raw != ''
GROUP BY pv.property_code_raw
ORDER BY affected_tags DESC;
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
    doc_number,
    ARRAY_AGG(rev ORDER BY rev) AS revisions,
    COUNT(*)                    AS cnt
FROM project_core.document
WHERE object_status = 'Active'
GROUP BY doc_number
HAVING COUNT(*) > 1
ORDER BY cnt DESC;
    $sql_c049$,
    'No violating rows (empty result = pass)', false,
    'EIS-file: 014', true, 'COUNT_ZERO'
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
    tag_name,
    depth AS cycle_detected_at_depth
FROM tag_hierarchy
WHERE is_cycle = TRUE
ORDER BY cycle_detected_at_depth DESC, tag_name;
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
  -- Exclude codes covered by Group A (CRS-C001..CRS-C050)
  AND ct.category NOT IN (
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
  AND ct.category != 'CRS-C168'
ON CONFLICT (query_code) DO NOTHING;

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
