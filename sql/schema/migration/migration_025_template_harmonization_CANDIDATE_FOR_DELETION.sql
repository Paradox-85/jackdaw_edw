-- =============================================================================
-- Migration 025: CRS Template Harmonization — Complete Reload with CRS-C51..C230
-- =============================================================================
-- Purpose: Delete all rows from crs_comment_template and reload from JSON
--          This ensures category, category_code, check_type, domain are all in sync
--
-- Problem:
--   - Table has 229 rows with inconsistent category/category_code/check_type/domain
--   - 179 rows have category NOT in CRS-C01..CRS-C50 format
--   - Old categories: TAG_DATA (53), DOCUMENT (32), PROPERTY (29),
--                 EQUIPMENT_DATA (24), TAG_CONNECTION (9), SAFETY (8),
--                 OTHER (8), PURCHASE_ORDER (7), PROCESS_UNIT (6),
--                 MODEL_PART (3)
--   - Tier 3 LLM classifier only accepts CRS-C01..CRS-C50 (_VALID_CATEGORIES)
--   - Other categories map to "OTHER", making LLM classification useless
--
-- Solution:
--   - Generate unique CRS-Cxx code for EACH record (not per category)
--   - Total 179 new codes: CRS-C51..CRS-C230
--   - Update JSON file with new codes
--   - Update Python code: extend _VALID_CATEGORIES to CRS-C01..CRS-C230
--   - DELETE all rows and reload from JSON
--
-- Dependencies: migration_024_crs_check_type_domain_update.sql
-- Idempotent: Yes (DELETE + INSERT)
-- =============================================================================

BEGIN;

-- =============================================================================
-- Part A: Delete existing rows owned by this migration
-- =============================================================================
-- All rows seeded from JSON have source='manual' and category_code IS NOT NULL
-- This allows safe re-run of the migration
DELETE FROM audit_core.crs_comment_template
WHERE source = 'manual' AND category_code IS NOT NULL;

-- =============================================================================
-- Part B: Reload from JSON file (requires updated JSON)
-- =============================================================================
-- Before running this migration, update prompts/crs_comment_template.json:
--
-- 1. Run script: python scripts/fix_crs_template_categories.py
--    This script generates unique CRS-Cxx codes for each record:
--
--    Category         | Count  | New CRS-Cxx codes
--    ----------------|--------|---------------------
--    TAG_DATA         | 53     | CRS-C51..CRS-C103
--    DOCUMENT          | 32     | CRS-C104..CRS-C135
--    PROPERTY          | 29     | CRS-C136..CRS-C164
--    EQUIPMENT_DATA    | 24     | CRS-C165..CRS-C188
--    TAG_CONNECTION    | 9      | CRS-C189..CRS-C197
--    SAFETY           | 8      | CRS-C198..CRS-C205
--    OTHER            | 8      | CRS-C206..CRS-C213
--    PURCHASE_ORDER    | 7      | CRS-C214..CRS-C220
--    PROCESS_UNIT      | 6      | CRS-C221..CRS-C226
--    MODEL_PART       | 3      | CRS-C227..CRS-C229
--
-- 2. Update etl/tasks/crs_tier3_llm_classifier.py:
--    Change _VALID_CATEGORIES: range(1, 51) → range(1, 231)
--    Format: f"CRS-C{i:03d}" to support CRS-C001..CRS-C999
--
-- 3. After JSON update, execute:
--    python scripts/load_crs_templates_from_json.py

-- =============================================================================
-- Part C: Add comments documenting unused columns
-- =============================================================================

COMMENT ON COLUMN audit_core.crs_comment_template.domain IS
  'Domain label (tag, document, equipment, area, process_unit, model_part, '
  'tag_property, equipment_property, tag_connection, purchase_order, other) '
  'for filtering templates by domain in Tier 3 LLM classifier. '
  'Used by _build_categories_line() in crs_tier3_llm_classifier.py.';

COMMENT ON COLUMN audit_core.crs_comment_template.category_code IS
  'Category code (CRS-C001..CRS-C999) — human-readable template identifier. '
  'Matches category field value. Used as primary key for template lookups.';

COMMENT ON COLUMN audit_core.crs_comment_template.response_template IS
  'Reserved for future use. Currently empty — LLM generates response text at runtime. '
  'If populated, would provide canned responses for specific templates.';

COMMENT ON COLUMN audit_core.crs_comment_template.check_type IS
  'Check type / domain value for routing templates by category in Tier 3 LLM classifier. '
  'Values: tag, document, equipment, area, process_unit, model_part, '
  'tag_property, equipment_property, tag_connection, purchase_order, other. '
  'Used by _build_categories_line() for domain filtering: '
  'domain.lower() IN check_type.lower().';

-- =============================================================================
-- Part D: Verification queries (run after loading JSON)
-- =============================================================================

-- 1. Verify all categories are in CRS-C001..CRS-C999 format
/*
SELECT category, COUNT(*) AS cnt
FROM audit_core.crs_comment_template
WHERE category NOT SIMILAR TO 'CRS-C[0-9]{2,3}'
GROUP BY category
ORDER BY cnt DESC;
-- Expected: 0 rows
*/

-- 2. Verify category_code = category for all records
/*
SELECT id, category, category_code, check_type, domain
FROM audit_core.crs_comment_template
WHERE category != category_code OR category_code IS NULL
LIMIT 20;
-- Expected: 0 rows
*/

-- 3. Verify domain = check_type for all records
/*
SELECT id, category, check_type, domain
FROM audit_core.crs_comment_template
WHERE check_type IS NULL OR domain IS NULL OR domain != check_type
LIMIT 20;
-- Expected: 0 rows
*/

-- 4. Summary of templates by domain (should match 11 check_type values)
/*
SELECT
    check_type,
    COUNT(*) AS template_count,
    COUNT(DISTINCT category) AS unique_categories
FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
GROUP BY check_type
ORDER BY check_type;
-- Expected: 11 check_type values (area, process_unit, tag, equipment,
--                           model_part, tag_connection, purchase_order,
--                           tag_class_property, tag_property, equipment_property,
--                           document, other)
*/

-- 5. Verify no duplicate template_hash values
/*
SELECT template_hash, COUNT(*) AS cnt
FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
GROUP BY template_hash HAVING COUNT(*) > 1;
-- Expected: 0 rows
*/

-- 6. Total count verification
/*
SELECT COUNT(*) AS total_active_templates
FROM audit_core.crs_comment_template
WHERE object_status = 'Active';
-- Expected: 229
*/

-- 7. Verify category distribution (CRS-C01..C50 vs CRS-C51..C229)
/*
SELECT
    CASE
        WHEN category SIMILAR TO 'CRS-C[0-4][0-9]' THEN 'CRS-C01..C50'
        WHEN category SIMILAR TO 'CRS-C[5-9][0-9]{2}' THEN 'CRS-C51..C99'
        WHEN category SIMILAR TO 'CRS-C1[0-9]{2}' THEN 'CRS-C100..C199'
        WHEN category SIMILAR TO 'CRS-C2[0-2][0-9]' THEN 'CRS-C200..C229'
        ELSE 'OTHER'
    END AS category_range,
    COUNT(*) AS cnt
FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
GROUP BY category_range
ORDER BY category_range;
-- Expected:
--   CRS-C01..C50: 50
--   CRS-C51..C229: 179
*/

COMMIT;

-- =============================================================================
-- Post-migration steps:
-- =============================================================================
-- 1. Create and run script: scripts/fix_crs_template_categories.py
--    This generates unique CRS-Cxx codes for each record in JSON
--
-- 2. Update prompts/crs_comment_template.json:
--    Script will update the file in place
--
-- 3. Update etl/tasks/crs_tier3_llm_classifier.py:
--    Change _VALID_CATEGORIES: range(1, 51) → range(1, 231)
--    Change format to: f"CRS-C{i:03d}" (supports CRS-C001..CRS-C999)
--    Add CRS-C51..CRS-C229 to _FALLBACK_CATEGORIES (optional)
--
-- 4. Run migration:
--    psql -U postgres_admin -d engineering_core -f sql/schema/migration_025_template_harmonization.sql
--
-- 5. Load data from JSON:
--    python scripts/load_crs_templates_from_json.py
--
-- 6. Run verification queries from Part D
--
-- 7. Test Tier 3 LLM classifier to ensure categories are valid
-- =============================================================================
