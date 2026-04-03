-- =============================================================================
-- Migration 020: CRS Template Harmonization & Check Type Fix
-- =============================================================================
-- Purpose:
--   1. Update check_type to match domain values (deterministic routing)
--   2. Harmonize CRS-C01..C09 categories to match template standard
--   3. Ensure category_code follows pattern: CRS-C## | TAG-### | EQUIP-### | etc.
--   4. Verify all templates have consistent check_type values
--
-- Dependencies: migration_019_crs_comment_templates.sql (must run first)
-- Idempotent: Yes (uses CASE with explicit fallbacks)
-- =============================================================================

BEGIN;

-- =============================================================================
-- Part A: Update check_type from domain (deterministic routing)
-- =============================================================================
-- Maps domain column to appropriate check_type value for Tier 3 filtering.
-- Domain values match _SEQ_TO_DOMAIN mapping in crs_tier3_llm_classifier.py.
-- =============================================================================

UPDATE audit_core.crs_comment_template
SET check_type = CASE
    WHEN domain = 'area' THEN 'area'
    WHEN domain = 'process_unit' THEN 'process_unit'
    WHEN domain = 'tag' THEN 'tag'
    WHEN domain = 'equipment' THEN 'equipment'
    WHEN domain = 'model_part' THEN 'model_part'
    WHEN domain = 'tag_connection' THEN 'tag_connection'
    WHEN domain = 'purchase_order' THEN 'purchase_order'
    WHEN domain = 'tag_class_property' THEN 'tag_class_property'
    WHEN domain = 'tag_property' THEN 'tag_property'
    WHEN domain = 'equipment_property' THEN 'equipment_property'
    WHEN domain = 'document' THEN 'document'
    WHEN domain = 'other' THEN 'other'
    ELSE check_type  -- Fallback: preserve existing value if domain unknown
END
WHERE category_code IS NOT NULL
  AND (
      check_type IS NULL
   OR check_type != domain
  );

-- =============================================================================
-- Part B: Harmonize category values to readable descriptions
-- =============================================================================
-- For CRS-C01 through CRS-C09: update category field to readable text
-- mapping matches migration_019 template definitions.
-- =============================================================================

UPDATE audit_core.crs_comment_template
SET category = CASE category_code
    -- CRS-C01: Missing tag description
    WHEN 'CRS-C01' THEN 'Tag description is blank for one or more tags — functional description must be provided.'
    WHEN 'CRS-C02' THEN 'Tag description should indicate function/service and be elaborative enough to understand the tag clearly.'
    WHEN 'CRS-C03' THEN 'Tag description is too short — please revise and provide a more detailed description.'
    WHEN 'CRS-C04' THEN 'Tag description exceeds 255 characters — please limit within 255 characters.'
    WHEN 'CRS-C05' THEN 'Tag description contains multiple extra spaces — remove extra spaces.'
    WHEN 'CRS-C06' THEN 'Tag description ends with a dash — correct to reflect proper tag reference.'
    WHEN 'CRS-C07' THEN 'Tag description starts with a dash — correct to description.'
    WHEN 'CRS-C08' THEN 'Process Unit Code is missing or set to NA'
    WHEN 'CRS-C09' THEN 'Process Unit Code is not in register or set to NA/Not Applicable'

    -- Fallback: preserve existing category text
    ELSE category
END
WHERE category_code LIKE 'CRS-C0%'
  AND category_code IS NOT NULL;

-- =============================================================================
-- Part C: Verify category_code format consistency
-- =============================================================================
-- Ensure category_code follows expected patterns:
--   CRS-C## | TAG-### | EQUIP-### | EQPROP-### | TPROP-### | TCONN-###
--   TCPROP-### | DOC-### | PO-### | PU-### | MPART-### | AREA-### | OTHER-###
--
-- If category_code deviates from pattern, preserve it for manual review.
-- =============================================================================

-- Note: This SELECT is for verification only — no DML executed here.
-- Actual category_code values are already correct per migration_019.

/*
-- Verification query (run manually after migration):
SELECT
    CASE
        WHEN category_code ~ '^(CRS-C|TAG-|EQUIP-|EQPROP-|TPROP-|TCONN-|TCPROP-|DOC-|PO-|PU-|MPART-|AREA-|OTHER-)-\d{2,3}$'
        THEN 'VALID_FORMAT'
        ELSE 'INVALID_FORMAT: ' || category_code
    END AS format_check,
    category_code,
    category,
    check_type,
    domain
FROM audit_core.crs_comment_template
WHERE category_code IS NOT NULL
ORDER BY
    CASE
        WHEN category_code LIKE 'CRS-C%' THEN 1
        WHEN category_code LIKE 'TAG-%' THEN 2
        WHEN category_code LIKE 'EQUIP-%' THEN 3
        WHEN category_code LIKE 'EQPROP-%' THEN 4
        WHEN category_code LIKE 'TPROP-%' THEN 5
        WHEN category_code LIKE 'TCONN-%' THEN 6
        WHEN category_code LIKE 'TCPROP-%' THEN 7
        WHEN category_code LIKE 'DOC-%' THEN 8
        WHEN category_code LIKE 'PO-%' THEN 9
        WHEN category_code LIKE 'PU-%' THEN 10
        WHEN category_code LIKE 'MPART-%' THEN 11
        WHEN category_code LIKE 'AREA-%' THEN 12
        ELSE 13
    END,
    category_code;
-- Expected: All rows show VALID_FORMAT
*/

-- =============================================================================
-- Part D: Summary report (for verification)
-- =============================================================================

SELECT
    domain,
    check_type,
    COUNT(*) AS template_count,
    COUNT(DISTINCT category_code) AS unique_categories
FROM audit_core.crs_comment_template
WHERE category_code IS NOT NULL
GROUP BY domain, check_type
ORDER BY domain, check_type;

-- =============================================================================
COMMIT;
-- =============================================================================
-- Post-migration verification (run manually):
-- =============================================================================

/*
-- 1. Verify check_type = domain for all templates
SELECT category_code, domain, check_type
FROM audit_core.crs_comment_template
WHERE category_code IS NOT NULL AND check_type != domain;

-- Expected: 0 rows

-- 2. Verify category_code format
SELECT category_code, category
FROM audit_core.crs_comment_template
WHERE category_code IS NOT NULL
  AND category_code !~ '^(CRS-C|TAG-|EQUIP-|EQPROP-|TPROP-|TCONN-|TCPROP-|DOC-|PO-|PU-|MPART-|AREA-|OTHER-)-\d{2,3}$';

-- Expected: 0 rows

-- 3. Verify CRS-C01..C09 have readable descriptions
SELECT category_code, category, check_type
FROM audit_core.crs_comment_template
WHERE category_code LIKE 'CRS-C0%'
ORDER BY category_code;

-- Expected: CRS-C01..C09 show descriptive category text
*/
