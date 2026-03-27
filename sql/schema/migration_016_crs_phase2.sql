-- =============================================================================
-- migration_016_crs_phase2.sql
--
-- Purpose:
--   Phase 2 CRS Cascade Classifier — infrastructure setup.
--   1. Two separate views for LLM SQL verification (prevents Cartesian explosion)
--   2. Seed 5 validation queries into audit_core.crs_validation_query
--   3. CHECK constraint on crs_validation_query.category
--
-- Applies after: migration_015_crs_add_from_to_tag.sql
-- =============================================================================

BEGIN;

-- =============================================================================
-- Part A: Views for Tier 3 SQL verification
-- =============================================================================

-- View 1: tag + document links only (no properties JOIN — prevents Cartesian)
CREATE OR REPLACE VIEW project_core.v_tag_with_docs AS
SELECT
    t.id,
    t.tag_name,
    t.tag_status,
    t.object_status,
    d.id          AS document_id,
    d.doc_number
FROM project_core.tag t
LEFT JOIN mapping.tag_document td
    ON td.tag_id = t.id
   AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d
    ON d.id = td.document_id
   AND d.object_status = 'Active'
WHERE t.object_status = 'Active';

COMMENT ON VIEW project_core.v_tag_with_docs IS
    'Active tags with their linked documents. Excludes properties to prevent '
    'Cartesian product with v_tag_properties. Used by Tier 3 LLM verifier.';

-- View 2: tag + property values only (no documents JOIN)
CREATE OR REPLACE VIEW project_core.v_tag_properties AS
SELECT
    t.id,
    t.tag_name,
    t.tag_status,
    t.object_status,
    p.code         AS property_code,
    p.name         AS property_name,
    pv.property_value,
    pv.property_uom_raw
FROM project_core.tag t
LEFT JOIN project_core.property_value pv
    ON pv.tag_id = t.id
   AND pv.object_status = 'Active'
LEFT JOIN ontology_core.property p
    ON p.id = pv.property_id
WHERE t.object_status = 'Active';

COMMENT ON VIEW project_core.v_tag_properties IS
    'Active tags with their property values. Excludes document links to prevent '
    'Cartesian product with v_tag_with_docs. Used by Tier 3 LLM verifier.';


-- =============================================================================
-- Part B: CHECK constraint on crs_validation_query.category
-- =============================================================================

-- Drop constraint if it exists (idempotent re-run)
ALTER TABLE audit_core.crs_validation_query
    DROP CONSTRAINT IF EXISTS chk_crs_vq_category;

ALTER TABLE audit_core.crs_validation_query
    ADD CONSTRAINT chk_crs_vq_category
    CHECK (category IN (
        'tag_existence',
        'document_link',
        'property_check',
        'tag_relationship',
        'bulk_check',
        'custom'
    ));


-- =============================================================================
-- Part C: Seed 5 validation queries (ON CONFLICT DO UPDATE — idempotent)
-- =============================================================================

INSERT INTO audit_core.crs_validation_query
    (id, query_code, query_name, description, category, sql_query,
     expected_result, has_parameters, parameter_names, is_active,
     created_at, updated_at, created_by, object_status)
VALUES
-- 1. TAG_EXISTS: Check if a tag exists with Active status
(
    gen_random_uuid(),
    'TAG_EXISTS',
    'Tag Exists in EDW',
    'Verify that a tag with the given tag_name exists in project_core.tag with Active status.',
    'tag_existence',
    'SELECT id, tag_name, tag_status, object_status
     FROM project_core.tag
     WHERE tag_name = :tag_name
       AND object_status = ''Active''
     LIMIT 1',
    'One row if tag exists and is active; zero rows if not found or inactive.',
    true,
    ARRAY['tag_name'],
    true,
    now(), now(), 'migration_016', 'Active'
),

-- 2. TAG_HAS_DOCUMENT: Check if a tag is linked to at least one document
(
    gen_random_uuid(),
    'TAG_HAS_DOCUMENT',
    'Tag Has Document Link',
    'Verify that a tag has at least one active document link in mapping.tag_document.',
    'document_link',
    'SELECT t.tag_name, d.doc_number, td.mapping_status
     FROM project_core.tag t
     JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = ''Active''
     JOIN project_core.document d ON d.id = td.document_id AND d.object_status = ''Active''
     WHERE t.tag_name = :tag_name
       AND t.object_status = ''Active''
     LIMIT 10',
    'Rows if tag has document links; empty if no documents linked.',
    true,
    ARRAY['tag_name'],
    true,
    now(), now(), 'migration_016', 'Active'
),

-- 3. TAG_HAS_PROPERTY: Check if a tag has a specific property value
(
    gen_random_uuid(),
    'TAG_HAS_PROPERTY',
    'Tag Has Property Value',
    'Verify that a tag has a specific property defined (non-empty value).',
    'property_check',
    'SELECT t.tag_name, p.code AS property_code, p.name AS property_name,
            pv.property_value, pv.property_uom_raw
     FROM project_core.tag t
     JOIN project_core.property_value pv ON pv.tag_id = t.id AND pv.object_status = ''Active''
     JOIN ontology_core.property p ON p.id = pv.property_id
     WHERE t.tag_name = :tag_name
       AND t.object_status = ''Active''
       AND (p.code = :property_code OR p.name ILIKE :property_name)
     LIMIT 5',
    'Rows with property value if set; empty if property is missing or blank.',
    true,
    ARRAY['tag_name', 'property_code', 'property_name'],
    true,
    now(), now(), 'migration_016', 'Active'
),

-- 4. TAG_FROM_TO_LINK: Check FROM/TO tag directional relationship
(
    gen_random_uuid(),
    'TAG_FROM_TO_LINK',
    'Tag FROM/TO Directional Link',
    'Verify that FROM_TAG and TO_TAG both exist and are active tags in EDW.',
    'tag_relationship',
    'SELECT
         ft.tag_name AS from_tag, ft.tag_status AS from_status,
         tt.tag_name AS to_tag,   tt.tag_status AS to_status
     FROM project_core.tag ft
     CROSS JOIN project_core.tag tt
     WHERE ft.tag_name = :from_tag
       AND tt.tag_name = :to_tag
       AND ft.object_status = ''Active''
       AND tt.object_status = ''Active''',
    'One row if both tags exist and are active; empty if either is missing.',
    true,
    ARRAY['from_tag', 'to_tag'],
    true,
    now(), now(), 'migration_016', 'Active'
),

-- 5. TAGS_WITHOUT_PROPERTIES: Count of active tags that have zero properties
(
    gen_random_uuid(),
    'TAGS_WITHOUT_PROPERTIES',
    'Tags Without Any Properties',
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
    false,
    ARRAY[]::text[],
    true,
    now(), now(), 'migration_016', 'Active'
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
-- VERIFICATION QUERIES (run manually after applying)
-- =============================================================================

/*
-- 1. Views created:
SELECT table_schema, table_name, table_type
FROM information_schema.views
WHERE table_schema = 'project_core'
  AND table_name IN ('v_tag_with_docs', 'v_tag_properties');

-- 2. Validation queries seeded:
SELECT query_code, category, has_parameters, is_active
FROM audit_core.crs_validation_query
ORDER BY query_code;

-- 3. CHECK constraint exists:
SELECT conname, contype FROM pg_constraint
WHERE conname = 'chk_crs_vq_category';
*/
