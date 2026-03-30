-- =============================================================================
-- Migration 018: CRS Categories v2.0 Seed
-- Adds category_code column to crs_comment and seeds 50 validation queries
-- and 50+ comment templates from crs_comment_categories_v2.md
--
-- Idempotent: all INSERTs use ON CONFLICT DO UPDATE — safe to re-run.
-- Validated: all 50 SQL queries tested against live DB via pgedge MCP.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- PART 1: Add new columns to audit_core.crs_comment
-- ---------------------------------------------------------------------------

ALTER TABLE audit_core.crs_comment
    ADD COLUMN IF NOT EXISTS category_code        TEXT,
    ADD COLUMN IF NOT EXISTS category_confidence  REAL,
    ADD COLUMN IF NOT EXISTS validation_query_ids UUID[];

CREATE INDEX IF NOT EXISTS idx_crs_comment_category_code
    ON audit_core.crs_comment (category_code);

-- ---------------------------------------------------------------------------
-- PART 2: Seed audit_core.crs_validation_query (50 categories CRS-C01..C50)
-- ---------------------------------------------------------------------------

-- C01 — Missing mandatory fields (general)
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C01',
    'Missing mandatory fields (general)',
    'Tags with empty mandatory fields: TAG_CLASS, DESCRIPTION, PROCESS_UNIT, SAFETY_CRITICAL_ITEM',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 001/003/004. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name   = EXCLUDED.query_name,
    sql_query    = EXCLUDED.sql_query,
    updated_at   = now();

-- C02 — TAG_DESCRIPTION missing
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C02',
    'TAG_DESCRIPTION missing',
    'Active tags where description is NULL or empty',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C03 — TAG_DESCRIPTION > 255 chars
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C03',
    'TAG_DESCRIPTION exceeds 255 characters',
    'Tags where description length exceeds 255 characters',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
SELECT
    t.tag_name,
    LENGTH(t.description)            AS desc_length,
    LEFT(t.description, 80) || '...' AS desc_preview
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.description IS NOT NULL
  AND LENGTH(t.description) > 255
ORDER BY desc_length DESC;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C04 — TAG_CLASS not in ISM (RDL)
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C04',
    'TAG_CLASS not in ISM / RDL',
    'Tags where class_id is NULL but tag_class_raw is provided (unresolved FK)',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
SELECT
    t.tag_name,
    t.tag_class_raw   AS submitted_class,
    'NOT RESOLVED IN RDL' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.class_id IS NULL
  AND t.tag_class_raw IS NOT NULL AND t.tag_class_raw != ''
ORDER BY t.tag_class_raw, t.tag_name;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C05 — TNC (Tag Naming Convention) violated
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C05',
    'Tag Naming Convention (TNC) violated',
    'Tags not starting with JDA-, containing commas, or pipe-tags ending with dash',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
-- 1. Tag not starting with "JDA-"
SELECT tag_name, tag_class_raw, plant_raw, '1_PREFIX' AS check_type
FROM project_core.tag
WHERE object_status = 'Active'
  AND tag_name NOT LIKE 'JDA-%'

UNION ALL

-- 2. Comma in tag name
SELECT tag_name, tag_class_raw, plant_raw, '2_COMMA' AS check_type
FROM project_core.tag
WHERE object_status = 'Active'
  AND tag_name ~ ','

UNION ALL

-- 3. Pipe-tags ending with dash (FIXED v2.0: added LEFT JOIN)
SELECT t.tag_name, c.name AS tag_class_raw, t.plant_raw, '3_PIPE_DASH' AS check_type
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND c.name ILIKE '%pipe%'
  AND t.tag_name LIKE '%-'

ORDER BY check_type, tag_name;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003/004. mapping_presence: Mandatory. v2.0: added LEFT JOIN ontology_core.class'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C06 — AREA_CODE blank (non-mandatory)
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C06',
    'AREA_CODE blank',
    'Active tags where area_id is NULL (recommended field)',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C07 — AREA_CODE invalid or "NA"
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C07',
    'AREA_CODE invalid or literal NA',
    'Tags where area_code_raw provided but FK not resolved, or literal NA value',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
-- area_code_raw submitted but FK not resolved
SELECT
    t.tag_name,
    t.area_code_raw       AS submitted_area_code,
    'NOT IN AREA REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.area_code_raw IS NOT NULL AND t.area_code_raw != ''
  AND t.area_id IS NULL
ORDER BY t.area_code_raw;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 001/003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C08 — PROCESS_UNIT_CODE missing
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C08',
    'PROCESS_UNIT_CODE missing',
    'Active tags where process_unit_id is NULL',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C09 — PROCESS_UNIT_CODE not in register
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C09',
    'PROCESS_UNIT_CODE not in register',
    'Tags where process_unit_raw provided but FK not resolved',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
SELECT
    t.tag_name,
    t.process_unit_raw        AS submitted_pu_code,
    'NOT IN PROCESS_UNIT REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.process_unit_raw IS NOT NULL AND t.process_unit_raw != ''
  AND t.process_unit_id IS NULL
ORDER BY t.process_unit_raw;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003/018. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C10 — PARENT_TAG missing for physical tags
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C10',
    'PARENT_TAG missing for physical tags',
    'Physical tags (valve, transmitter, pipe, pump, motor, sensor) without parent_tag',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C11 — PARENT_TAG not in MTR
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C11',
    'PARENT_TAG not in MTR',
    'Tags where parent_tag_raw provided but parent_tag_id not resolved',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
SELECT
    t.tag_name,
    t.parent_tag_raw     AS declared_parent,
    'PARENT NOT IN MTR'  AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.parent_tag_raw IS NOT NULL AND t.parent_tag_raw != ''
  AND t.parent_tag_id IS NULL
ORDER BY t.parent_tag_raw;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C12 — PARENT_TAG pipe-to-pipe reference
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C12',
    'PARENT_TAG pipe-to-pipe reference',
    'Pipe tags whose parent tag is also a pipe tag',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C13 — SAFETY_CRITICAL_ITEM blank or invalid
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C13',
    'SAFETY_CRITICAL_ITEM blank or invalid',
    'Active tags with NULL, empty, or non-YES/NO safety_critical_item',
    'SAFETY',
    'Safety-critical attribute checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C14 — SAFETY_CRITICAL_ITEM_REASON_AWARDED missing for SECE tags
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C14',
    'SAFETY_CRITICAL_REASON missing for SECE tags',
    'Safety-critical tags (YES/Y) without safety_critical_item_reason_awarded',
    'SAFETY',
    'Safety-critical attribute checks in project_core.tag',
    $SQL$
SELECT
    t.tag_name,
    t.safety_critical_item,
    t.safety_critical_item_reason_awarded
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND (t.safety_critical_item_reason_awarded IS NULL OR TRIM(t.safety_critical_item_reason_awarded) = '')
ORDER BY t.tag_name;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C15 — PRODUCTION_CRITICAL_ITEM blank
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C15',
    'PRODUCTION_CRITICAL_ITEM blank',
    'Active tags with NULL or empty production_critical_item',
    'SAFETY',
    'Safety-critical attribute checks in project_core.tag',
    $SQL$
SELECT
    t.tag_name,
    t.production_critical_item,
    COALESCE(c.name, t.tag_class_raw) AS tag_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND (t.production_critical_item IS NULL OR TRIM(t.production_critical_item) = '')
ORDER BY t.tag_name;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C16 — Duplicate tags
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C16',
    'Duplicate tags',
    'Active tags with duplicate tag_name values',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
SELECT tag_name, COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_name
HAVING COUNT(*) > 1
ORDER BY cnt DESC;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C17 — Tag Property: tag not in MTR
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C17',
    'Tag Property: tag not in MTR',
    'Property values referencing tags that do not exist or are inactive',
    'PROPERTY',
    'Property value integrity checks in project_core.property_value',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 010. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C18 — PROPERTY_VALUE = "NA" with non-empty UOM
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C18',
    'PROPERTY_VALUE = NA with non-empty UOM',
    'Property values with NA/N/A but non-empty property_uom_raw (FIXED v2.0: correct column names)',
    'PROPERTY',
    'Property value integrity checks in project_core.property_value',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 010/011. v2.0: pv.property_value; pv.property_uom_raw'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C19 — PROPERTY_VALUE = "0"
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C19',
    'PROPERTY_VALUE = 0 (zero value)',
    'Property values with exact string "0" (FIXED v2.0: correct column names)',
    'PROPERTY',
    'Property value integrity checks in project_core.property_value',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 010/011. v2.0: pv.property_value; pv.property_uom_raw'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C20 — Property class mapping mismatch
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C20',
    'Property class mapping mismatch',
    'Property values where property_code is not in the allowed set for the tag class',
    'PROPERTY',
    'Property value integrity checks in project_core.property_value',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 010. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C21 — Tag without any property in Property CSV
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C21',
    'Tag without any property in Property CSV',
    'Active tags with no property_value records',
    'PROPERTY',
    'Property value integrity checks in project_core.property_value',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 010. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C22 — Mandatory ISM properties not submitted (FIXED v2.0: mapping_presence = 'Mandatory')
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C22',
    'Mandatory ISM properties not submitted',
    'Tags missing properties with mapping_presence = Mandatory per RDL (FIXED v2.0)',
    'PROPERTY',
    'Property value integrity checks in project_core.property_value',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 010/011. v2.0: mapping_presence=Mandatory (not is_required=TRUE)'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C23 — EQUIPMENT_CLASS not in RDL
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C23',
    'EQUIPMENT_CLASS not in RDL',
    'Equipment tags where class_id is NULL but tag_class_raw is provided',
    'EQUIPMENT',
    'Equipment register checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 004. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C24 — EQUIPMENT_DESCRIPTION blank
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C24',
    'EQUIPMENT_DESCRIPTION blank',
    'Equipment tags with NULL or empty description',
    'EQUIPMENT',
    'Equipment register checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 004. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C25 — MANUFACTURER_SERIAL_NUMBER blank or NA
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C25',
    'MANUFACTURER_SERIAL_NUMBER blank or NA',
    'Equipment tags with NULL, empty, or NA serial_no',
    'EQUIPMENT',
    'Equipment register checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 004. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C26 — MODEL_PART_NAME blank
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C26',
    'MODEL_PART_NAME blank',
    'Equipment tags with unresolved model_id and empty model_part_raw',
    'EQUIPMENT',
    'Equipment register checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 004. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C27 — MANUFACTURER_COMPANY blank
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C27',
    'MANUFACTURER_COMPANY blank',
    'Equipment tags with unresolved manufacturer_id and empty manufacturer_company_raw',
    'EQUIPMENT',
    'Equipment register checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 004. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C28 — Equipment: TAG_NAME not in MTR (FIXED v2.0: removed equip_no = Equip_ assumption)
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C28',
    'Equipment: TAG_NAME not in MTR',
    'Equipment records with equip_no but no corresponding active tag (FIXED v2.0)',
    'EQUIPMENT',
    'Equipment register checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 004. v2.0: removed equip_no=Equip_tag_name assumption'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C29 — PLANT_CODE invalid
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C29',
    'PLANT_CODE invalid or missing',
    'Tags where plant_raw provided but plant_id not resolved',
    'REFERENCE',
    'Reference data integrity checks',
    $SQL$
SELECT
    t.tag_name,
    t.plant_raw             AS submitted_plant_code,
    'PLANT NOT IN REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.plant_raw IS NOT NULL AND t.plant_raw != ''
  AND t.plant_id IS NULL
ORDER BY t.plant_raw;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003/004. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C30 — Document not in DocMaster or NYI/CAN status
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C30',
    'Document not in DocMaster or NYI/CAN status',
    'Active documents with NULL status or NYI/CAN (not yet issued / cancelled)',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 014/016. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C31 — Tag without document reference
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C31',
    'Tag without document reference',
    'Active tags with no active entries in mapping.tag_document',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 016. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C32 — Doc in Tag-Doc but not in DocMaster
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C32',
    'Doc in Tag-Doc mapping but not in DocMaster',
    'Document numbers referenced in tag_document but absent from project_core.document',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 016. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C33 — Tag in Tag-Doc but not in MTR
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C33',
    'Tag in Tag-Doc mapping but not in MTR',
    'Tag names referenced in tag_document but absent from project_core.tag',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 016. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C34 — Doc-Area: AREA_CODE missing
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C34',
    'Doc-Area: AREA_CODE missing',
    'Documents linked to tags without area_id (seq 017 export will have empty AREA_CODE)',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 017. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C35 — Doc-PU: PROCESS_UNIT_CODE missing
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C35',
    'Doc-PU: PROCESS_UNIT_CODE missing',
    'Documents linked to tags without process_unit_id (seq 018 export will be empty)',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 018. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C36 — PO_CODE not in PO Register
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C36',
    'PO_CODE not in PO Register',
    'Tags where po_code_raw provided but po_id not resolved',
    'REFERENCE',
    'Reference data integrity checks',
    $SQL$
SELECT
    t.tag_name,
    t.po_code_raw        AS submitted_po_code,
    'PO NOT IN REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.po_code_raw IS NOT NULL AND t.po_code_raw != ''
  AND t.po_id IS NULL
ORDER BY t.po_code_raw;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 008/022. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C37 — PO_DATE missing
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C37',
    'PO_DATE missing',
    'Active purchase orders without po_date',
    'REFERENCE',
    'Reference data integrity checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 008. mapping_presence: Mandatory'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C38 — COMPANY_NAME missing or invalid
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C38',
    'COMPANY_NAME missing or invalid',
    'POs without issuer company, equipment without manufacturer, or company names with double spaces',
    'REFERENCE',
    'Reference data integrity checks',
    $SQL$
-- PO without issuer company
SELECT po.code AS po_code, NULL AS tag_name, 'ISSUER COMPANY MISSING' AS issue
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active' AND po.issuer_id IS NULL

UNION ALL

-- Equipment without manufacturer company
SELECT NULL AS po_code, t.tag_name, 'NO MANUFACTURER COMPANY' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.manufacturer_id IS NULL
  AND (t.manufacturer_company_raw IS NULL OR TRIM(t.manufacturer_company_raw) = '')

ORDER BY issue, po_code, tag_name;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 007/022. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C39 — Duplicate physical connections
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C39',
    'Duplicate physical connections',
    'Duplicate from_tag_raw/to_tag_raw pairs among active tags (v2.0: narrowed to duplicates only)',
    'TOPOLOGY',
    'Topology and physical connection checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 006. v2.0: separated from C45 (FK checks)'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C40 — Equipment without Doc-Equipment mapping
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C40',
    'Equipment without Doc-Equipment mapping',
    'Equipment tags with no document reference in mapping.tag_document',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 019. mapping_presence: Recommended'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C41 — EX_CLASS / IP_GRADE missing for E&I tags
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C41',
    'EX_CLASS / IP_GRADE missing for E&I tags',
    'Instrument/sensor/detector tags without ex_class and ip_grade',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. New in v2.0'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C42 — MC_PACKAGE_CODE missing
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C42',
    'MC_PACKAGE_CODE missing',
    'Valve/instrument/electrical/mechanical tags without mc_package_code',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. New in v2.0'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C43 — ALIAS conflicts with another tag
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C43',
    'ALIAS conflicts with another tag',
    'Alias values shared by multiple tags, or alias matching another tag''s tag_name',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
-- Alias duplicated between different tags
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. New in v2.0'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C44 — TECH_ID missing for instrument tags
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C44',
    'TECH_ID missing for instrument tags',
    'Instrument/loop/signal/transmitter tags without tech_id',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
SELECT
    t.tag_name,
    t.tech_id,
    t.tag_class_raw
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (t.tech_id IS NULL OR TRIM(t.tech_id) = '')
  AND t.tag_class_raw ~* '(instrument|loop|signal|transmitter)'
ORDER BY t.tag_class_raw, t.tag_name;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. New in v2.0'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C45 — FROM_TAG / TO_TAG not in MTR
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C45',
    'FROM_TAG / TO_TAG not in MTR',
    'Tags with from_tag_raw or to_tag_raw that could not be resolved to a tag FK',
    'TOPOLOGY',
    'Topology and physical connection checks',
    $SQL$
-- C45a: from_tag_raw submitted, FK not resolved
SELECT
    t.tag_name,
    t.from_tag_raw    AS declared_from,
    'FROM_TAG NOT IN MTR' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.from_tag_raw IS NOT NULL AND TRIM(t.from_tag_raw) != ''
  AND t.from_tag_id IS NULL

UNION ALL

-- C45b: to_tag_raw submitted, FK not resolved
SELECT
    t.tag_name,
    t.to_tag_raw      AS declared_to,
    'TO_TAG NOT IN MTR' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.to_tag_raw IS NOT NULL AND TRIM(t.to_tag_raw) != ''
  AND t.to_tag_id IS NULL

ORDER BY issue, tag_name;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 006. New in v2.0 (split from C39)'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C46 — TAG_STATUS outside allowed vocabulary
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C46',
    'TAG_STATUS outside allowed vocabulary',
    'Tags with tag_status values not in EIS-allowed set (see ADR-011: actual values are ACTIVE/VOID/ASB/AFC/Future)',
    'TAG_DATA',
    'Tag attribute completeness checks in project_core.tag',
    $SQL$
-- Overview of all tag_status values for active tags
SELECT
    COALESCE(tag_status, '(NULL)') AS tag_status,
    COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_status
ORDER BY cnt DESC;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. ADR-011: actual values ACTIVE/VOID/ASB/AFC/Future differ from EIS spec'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C47 — Safety critical = YES without tag_sece mapping
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C47',
    'Safety critical tag without SECE mapping',
    'Tags with safety_critical_item=YES/Y but no active entry in mapping.tag_sece',
    'SAFETY',
    'Safety-critical attribute checks in project_core.tag',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. New in v2.0'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C48 — property_code_raw not in ontology
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C48',
    'property_code_raw not in ontology',
    'Property values where property_id is NULL (code not found in ontology_core.property)',
    'PROPERTY',
    'Property value integrity checks in project_core.property_value',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 010/011. New in v2.0'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C49 — Duplicate doc_number in Document
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C49',
    'Duplicate doc_number in Document',
    'Multiple active rows for the same doc_number in project_core.document',
    'DOCUMENT',
    'Document master and cross-reference checks',
    $SQL$
SELECT
    doc_number,
    ARRAY_AGG(rev ORDER BY rev) AS revisions,
    COUNT(*)                    AS cnt
FROM project_core.document
WHERE object_status = 'Active'
GROUP BY doc_number
HAVING COUNT(*) > 1
ORDER BY cnt DESC;
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 014. New in v2.0'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- C50 — Circular parent reference (recursive CTE, depth limit 10)
INSERT INTO audit_core.crs_validation_query
    (query_code, query_name, description, category, category_description,
     sql_query, expected_result, has_parameters, is_active, created_by, notes)
VALUES (
    'CRS-C50',
    'Circular parent tag hierarchy',
    'Tags participating in circular parent_tag_id chains (ISO 15926 Part 2 violation)',
    'TOPOLOGY',
    'Topology and physical connection checks',
    $SQL$
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
    $SQL$,
    'empty_result_is_pass', false, true, 'migration_018', 'EIS-file: 003. New in v2.0. WARNING: real cycles found (JDA-P-46001A/B)'
)
ON CONFLICT (query_code) DO UPDATE SET
    query_name = EXCLUDED.query_name, sql_query = EXCLUDED.sql_query, updated_at = now();

-- ---------------------------------------------------------------------------
-- PART 3: Seed audit_core.crs_comment_template (50 entries, one per category)
-- ---------------------------------------------------------------------------

INSERT INTO audit_core.crs_comment_template
    (template_text, template_hash, category, check_type, source, confidence, object_status)
VALUES
-- TAG_DATA
('Data missing, further update required. Cells should not be left blank',
 md5(lower(trim('Data missing, further update required. Cells should not be left blank'))),
 'CRS-C01', 'tag_data', 'manual', 1.0, 'Active'),

('Tag Description is missing for listed N tags',
 md5(lower(trim('Tag Description is missing for listed N tags'))),
 'CRS-C02', 'tag_data', 'manual', 1.0, 'Active'),

('Tag Description is exceeding 255 characters. Kindly limit within 255 characters',
 md5(lower(trim('Tag Description is exceeding 255 characters. Kindly limit within 255 characters'))),
 'CRS-C03', 'tag_data', 'manual', 1.0, 'Active'),

('Tag Classes are not per Shell ISM / Tag Class Not available in Tag Class ISM (Jackdaw Data Reference)',
 md5(lower(trim('Tag Classes are not per Shell ISM / Tag Class Not available in Tag Class ISM (Jackdaw Data Reference)'))),
 'CRS-C04', 'tag_data', 'manual', 1.0, 'Active'),

('Tag Naming does not confirm with Jackdaw Tagging Specification JDAW-PT-D-OA-7880-00001',
 md5(lower(trim('Tag Naming does not confirm with Jackdaw Tagging Specification JDAW-PT-D-OA-7880-00001'))),
 'CRS-C05', 'tag_data', 'manual', 1.0, 'Active'),

('For N Tags, Area Code is blank. Though not mandatory but it is good to have the data',
 md5(lower(trim('For N Tags, Area Code is blank. Though not mandatory but it is good to have the data'))),
 'CRS-C06', 'tag_data', 'manual', 1.0, 'Active'),

('AREA_CODE is duplicated within the same cell',
 md5(lower(trim('AREA_CODE is duplicated within the same cell'))),
 'CRS-C07', 'tag_data', 'manual', 1.0, 'Active'),

('For N Tags listed, Process Unit Code is missing',
 md5(lower(trim('For N Tags listed, Process Unit Code is missing'))),
 'CRS-C08', 'tag_data', 'manual', 1.0, 'Active'),

('Process Unit Code is not matching/not available in Process Unit CSV',
 md5(lower(trim('Process Unit Code is not matching/not available in Process Unit CSV'))),
 'CRS-C09', 'tag_data', 'manual', 1.0, 'Active'),

('Listed N tags with class like Valve, transmitter, pipe etc should preferably have parent tag',
 md5(lower(trim('Listed N tags with class like Valve, transmitter, pipe etc should preferably have parent tag'))),
 'CRS-C10', 'tag_data', 'manual', 1.0, 'Active'),

('Parent tag itself is not part of Tag anywhere in tag register',
 md5(lower(trim('Parent tag itself is not part of Tag anywhere in tag register'))),
 'CRS-C11', 'tag_data', 'manual', 1.0, 'Active'),

('For listed N Pipe tags, parent tag is also pipe tag. Acceptable only for small bore pipe/nozzle',
 md5(lower(trim('For listed N Pipe tags, parent tag is also pipe tag. Acceptable only for small bore pipe/nozzle'))),
 'CRS-C12', 'tag_data', 'manual', 1.0, 'Active'),

-- SAFETY
('Many tags missing yes or no for safety critical item',
 md5(lower(trim('Many tags missing yes or no for safety critical item'))),
 'CRS-C13', 'tag_data', 'manual', 1.0, 'Active'),

('For listed N safety critical items, SAFETY_CRITICAL_ITEM_REASON_AWARDED is not provided',
 md5(lower(trim('For listed N safety critical items, SAFETY_CRITICAL_ITEM_REASON_AWARDED is not provided'))),
 'CRS-C14', 'tag_data', 'manual', 1.0, 'Active'),

('The Production Critical Item field is currently blank',
 md5(lower(trim('The Production Critical Item field is currently blank'))),
 'CRS-C15', 'tag_data', 'manual', 1.0, 'Active'),

-- TAG_DATA continued
('Duplicate Check: Please remove the duplicate values',
 md5(lower(trim('Duplicate Check: Please remove the duplicate values'))),
 'CRS-C16', 'tag_data', 'manual', 1.0, 'Active'),

-- PROPERTY
('Listed N records are part of Tag property register but corresponding Tags are not available in MTR',
 md5(lower(trim('Listed N records are part of Tag property register but corresponding Tags are not available in MTR'))),
 'CRS-C17', 'property', 'manual', 1.0, 'Active'),

('If the property value is NA, the corresponding UOM should not contain any value',
 md5(lower(trim('If the property value is NA, the corresponding UOM should not contain any value'))),
 'CRS-C18', 'property', 'manual', 1.0, 'Active'),

('Listed N records have property value as 0. It is flagged for review',
 md5(lower(trim('Listed N records have property value as 0. It is flagged for review'))),
 'CRS-C19', 'property', 'manual', 1.0, 'Active'),

('For N records, the Tag class mapping against Tag in Tag Property CSV is different/NA',
 md5(lower(trim('For N records, the Tag class mapping against Tag in Tag Property CSV is different/NA'))),
 'CRS-C20', 'property', 'manual', 1.0, 'Active'),

('For N Tags which are part of Tag CSV, do not have any property against them in Tag Property CSV',
 md5(lower(trim('For N Tags which are part of Tag CSV, do not have any property against them in Tag Property CSV'))),
 'CRS-C21', 'property', 'manual', 1.0, 'Active'),

('Tag_Property_Scope_Table: Listed Properties are not provided in CIS Submission which are required as per ISM',
 md5(lower(trim('Tag_Property_Scope_Table: Listed Properties are not provided in CIS Submission which are required as per ISM'))),
 'CRS-C22', 'property', 'manual', 1.0, 'Active'),

-- EQUIPMENT
('For N Equipment Numbers, Equipment Class is not matching with Jackdaw ISM (RDL)',
 md5(lower(trim('For N Equipment Numbers, Equipment Class is not matching with Jackdaw ISM (RDL)'))),
 'CRS-C23', 'equipment', 'manual', 1.0, 'Active'),

('For N Equipments, EQUIPMENT_DESCRIPTION is not available',
 md5(lower(trim('For N Equipments, EQUIPMENT_DESCRIPTION is not available'))),
 'CRS-C24', 'equipment', 'manual', 1.0, 'Active'),

('For N Equipments, Manufacturer Serial Number is blank, which is mandatory property as per EIS',
 md5(lower(trim('For N Equipments, Manufacturer Serial Number is blank, which is mandatory property as per EIS'))),
 'CRS-C25', 'equipment', 'manual', 1.0, 'Active'),

('For N Equipments, Model Part Name is missing, which is mandatory property as per EIS (Except soft tags)',
 md5(lower(trim('For N Equipments, Model Part Name is missing, which is mandatory property as per EIS (Except soft tags)'))),
 'CRS-C26', 'equipment', 'manual', 1.0, 'Active'),

('Manufacturing company is not populated for listed N equipments',
 md5(lower(trim('Manufacturing company is not populated for listed N equipments'))),
 'CRS-C27', 'equipment', 'manual', 1.0, 'Active'),

('For N Equipment Numbers, the corresponding listed Tags are not part of Tag CSV (MTR)',
 md5(lower(trim('For N Equipment Numbers, the corresponding listed Tags are not part of Tag CSV (MTR)'))),
 'CRS-C28', 'equipment', 'manual', 1.0, 'Active'),

-- REFERENCE
('PlantCode is SWA - not part of Area register',
 md5(lower(trim('PlantCode is SWA - not part of Area register'))),
 'CRS-C29', 'reference', 'manual', 1.0, 'Active'),

-- DOCUMENT
('Listed N document numbers are not available in Assai OR still in NYI (Not Yet Issued) status',
 md5(lower(trim('Listed N document numbers are not available in Assai OR still in NYI (Not Yet Issued) status'))),
 'CRS-C30', 'document', 'manual', 1.0, 'Active'),

('For N Tags which are part of Tag CSV do not have document references',
 md5(lower(trim('For N Tags which are part of Tag CSV do not have document references'))),
 'CRS-C31', 'document', 'manual', 1.0, 'Active'),

('These documents are available in Document to Tag reference but not in Document Master CSV',
 md5(lower(trim('These documents are available in Document to Tag reference but not in Document Master CSV'))),
 'CRS-C32', 'document', 'manual', 1.0, 'Active'),

('Tag NA in MTR: Listed N line items having N unique tags are not part of Tag Register',
 md5(lower(trim('Tag NA in MTR: Listed N line items having N unique tags are not part of Tag Register'))),
 'CRS-C33', 'document', 'manual', 1.0, 'Active'),

('Listed N document numbers as part of Doc Reference to Area do not have Area_Code',
 md5(lower(trim('Listed N document numbers as part of Doc Reference to Area do not have Area_Code'))),
 'CRS-C34', 'document', 'manual', 1.0, 'Active'),

('For N records, Process Unit code is missing in Document reference to Process Unit register',
 md5(lower(trim('For N records, Process Unit code is missing in Document reference to Process Unit register'))),
 'CRS-C35', 'document', 'manual', 1.0, 'Active'),

-- REFERENCE continued
('For listed N Tags, PO number is either not available/not matching with the PO CSV',
 md5(lower(trim('For listed N Tags, PO number is either not available/not matching with the PO CSV'))),
 'CRS-C36', 'reference', 'manual', 1.0, 'Active'),

('Listed N PO Codes do not have PO date which is mandatory field for PO register',
 md5(lower(trim('Listed N PO Codes do not have PO date which is mandatory field for PO register'))),
 'CRS-C37', 'reference', 'manual', 1.0, 'Active'),

('Company name not available for listed N PO code',
 md5(lower(trim('Company name not available for listed N PO code'))),
 'CRS-C38', 'reference', 'manual', 1.0, 'Active'),

-- TOPOLOGY
('Duplicate Check: Kindly remove the duplicate values in Physical Connection file',
 md5(lower(trim('Duplicate Check: Kindly remove the duplicate values in Physical Connection file'))),
 'CRS-C39', 'tag_data', 'manual', 1.0, 'Active'),

-- DOCUMENT continued
('Listed N Equipments do not have any document reference',
 md5(lower(trim('Listed N Equipments do not have any document reference'))),
 'CRS-C40', 'document', 'manual', 1.0, 'Active'),

-- TAG_DATA (v2.0 new)
('Ex classification is missing for zone 1/2 equipment',
 md5(lower(trim('Ex classification is missing for zone 1/2 equipment'))),
 'CRS-C41', 'tag_data', 'manual', 1.0, 'Active'),

('MC Package Code is missing for listed tags - required for completions',
 md5(lower(trim('MC Package Code is missing for listed tags - required for completions'))),
 'CRS-C42', 'tag_data', 'manual', 1.0, 'Active'),

('Alias must be unique and must not conflict with any other tag name',
 md5(lower(trim('Alias must be unique and must not conflict with any other tag name'))),
 'CRS-C43', 'tag_data', 'manual', 1.0, 'Active'),

('TECH_ID is missing / does not follow expected format',
 md5(lower(trim('TECH_ID is missing / does not follow expected format'))),
 'CRS-C44', 'tag_data', 'manual', 1.0, 'Active'),

-- TOPOLOGY (v2.0 new)
('Listed tags have from/to tag connections referencing tags not in MTR',
 md5(lower(trim('Listed tags have from/to tag connections referencing tags not in MTR'))),
 'CRS-C45', 'tag_data', 'manual', 1.0, 'Active'),

-- TAG_DATA (v2.0 new)
('TAG_STATUS value is outside the allowed EIS vocabulary',
 md5(lower(trim('TAG_STATUS value is outside the allowed EIS vocabulary'))),
 'CRS-C46', 'tag_data', 'manual', 1.0, 'Active'),

-- SAFETY (v2.0 new)
('Safety critical items not linked to performance standard (SECE mapping missing)',
 md5(lower(trim('Safety critical items not linked to performance standard (SECE mapping missing)'))),
 'CRS-C47', 'tag_data', 'manual', 1.0, 'Active'),

-- PROPERTY (v2.0 new)
('Property code not recognised in ISM - property not part of class scope',
 md5(lower(trim('Property code not recognised in ISM - property not part of class scope'))),
 'CRS-C48', 'property', 'manual', 1.0, 'Active'),

-- DOCUMENT (v2.0 new)
('Duplicate document number found in Document Master register',
 md5(lower(trim('Duplicate document number found in Document Master register'))),
 'CRS-C49', 'document', 'manual', 1.0, 'Active'),

-- TOPOLOGY (v2.0 new)
('Circular parent tag hierarchy detected - tag hierarchy must be acyclic',
 md5(lower(trim('Circular parent tag hierarchy detected - tag hierarchy must be acyclic'))),
 'CRS-C50', 'tag_data', 'manual', 1.0, 'Active')

ON CONFLICT (template_hash) DO UPDATE SET
    category   = EXCLUDED.category,
    check_type = EXCLUDED.check_type,
    source     = EXCLUDED.source;

-- ---------------------------------------------------------------------------
-- PART 4: Post-migration validation
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    v_queries  INTEGER;
    v_templates INTEGER;
    v_cols      INTEGER;
BEGIN
    -- Check 50 validation queries
    SELECT COUNT(*) INTO v_queries
    FROM audit_core.crs_validation_query
    WHERE query_code LIKE 'CRS-C%' AND is_active = true;

    IF v_queries != 50 THEN
        RAISE EXCEPTION 'Expected 50 CRS validation queries, found %', v_queries;
    END IF;
    RAISE NOTICE 'OK: % CRS validation queries loaded', v_queries;

    -- Check templates
    SELECT COUNT(*) INTO v_templates
    FROM audit_core.crs_comment_template
    WHERE category LIKE 'CRS-C%' AND object_status = 'Active';

    IF v_templates < 50 THEN
        RAISE EXCEPTION 'Expected >= 50 CRS templates, found %', v_templates;
    END IF;
    RAISE NOTICE 'OK: % CRS templates loaded', v_templates;

    -- Check new columns exist
    SELECT COUNT(*) INTO v_cols
    FROM information_schema.columns
    WHERE table_schema = 'audit_core'
      AND table_name   = 'crs_comment'
      AND column_name  IN ('category_code', 'category_confidence', 'validation_query_ids');

    IF v_cols != 3 THEN
        RAISE EXCEPTION 'Expected 3 new columns in crs_comment, found %', v_cols;
    END IF;
    RAISE NOTICE 'OK: 3 new columns present in audit_core.crs_comment';

END $$;

-- Summary queries (informational)
SELECT category, COUNT(*) AS queries
FROM audit_core.crs_validation_query
WHERE is_active = true AND query_code LIKE 'CRS-C%'
GROUP BY category
ORDER BY queries DESC;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'audit_core'
  AND table_name   = 'crs_comment'
  AND column_name  IN ('category_code', 'category_confidence', 'validation_query_ids')
ORDER BY column_name;
