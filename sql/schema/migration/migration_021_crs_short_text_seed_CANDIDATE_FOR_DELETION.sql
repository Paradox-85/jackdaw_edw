-- =============================================================================
-- migration_021_crs_short_text_seed.sql
--
-- Purpose: Seed short_template_text column for CRS-C01..C50 categories.
--          Provides compact one-line labels for LLM prompt injection.
--
-- Applies after: migration_020_crs_template_short_text.sql (column DDL)
-- Safe to re-run: UPDATE only (no INSERT, no DDL)
-- =============================================================================

BEGIN;

UPDATE audit_core.crs_comment_template AS t
SET short_template_text = v.short_text
FROM (
    VALUES
        ('CRS-C01', 'missing required fields'),
        ('CRS-C02', 'tag description missing'),
        ('CRS-C03', 'description too long'),
        ('CRS-C04', 'tag class not in RDL'),
        ('CRS-C05', 'tag naming convention violated'),
        ('CRS-C06', 'area code blank'),
        ('CRS-C07', 'area code invalid'),
        ('CRS-C08', 'process unit code missing'),
        ('CRS-C09', 'process unit not in register'),
        ('CRS-C10', 'parent tag missing for physical tag'),
        ('CRS-C11', 'parent tag not in MTR'),
        ('CRS-C12', 'pipe-to-pipe parent reference'),
        ('CRS-C13', 'safety critical item blank or invalid'),
        ('CRS-C14', 'safety critical reason missing'),
        ('CRS-C15', 'production critical item blank'),
        ('CRS-C16', 'duplicate tags'),
        ('CRS-C17', 'property tag not in MTR'),
        ('CRS-C18', 'UOM present when value is NA'),
        ('CRS-C19', 'property value is zero'),
        ('CRS-C20', 'property not in class scope'),
        ('CRS-C21', 'tag has no properties'),
        ('CRS-C22', 'mandatory property missing'),
        ('CRS-C23', 'equipment class not in RDL'),
        ('CRS-C24', 'equipment description blank'),
        ('CRS-C25', 'manufacturer serial number blank'),
        ('CRS-C26', 'model part name blank'),
        ('CRS-C27', 'manufacturer company blank'),
        ('CRS-C28', 'equipment tag not in MTR'),
        ('CRS-C29', 'plant code invalid'),
        ('CRS-C30', 'document missing or NYI/CAN status'),
        ('CRS-C31', 'tag has no document reference'),
        ('CRS-C32', 'document in mapping not in DocMaster'),
        ('CRS-C33', 'tag in mapping not in MTR'),
        ('CRS-C34', 'document area code missing'),
        ('CRS-C35', 'document process unit missing'),
        ('CRS-C36', 'PO code not in register'),
        ('CRS-C37', 'PO date missing'),
        ('CRS-C38', 'company name missing or invalid'),
        ('CRS-C39', 'duplicate physical connections'),
        ('CRS-C40', 'equipment has no document mapping'),
        ('CRS-C41', 'EX class or IP grade missing'),
        ('CRS-C42', 'MC package code missing'),
        ('CRS-C43', 'heat tracing type missing'),
        ('CRS-C44', 'insulation type missing'),
        ('CRS-C45', 'from-tag or to-tag not in MTR'),
        ('CRS-C46', 'tag linked to inactive document'),
        ('CRS-C47', 'revision status inconsistent'),
        ('CRS-C48', 'property UOM not in RDL'),
        ('CRS-C49', 'tag status inconsistent with class'),
        ('CRS-C50', 'circular parent hierarchy')
) AS v(category, short_text)
WHERE t.category = v.category
  AND t.object_status = 'Active';

COMMIT;


-- =============================================================================
-- VERIFICATION (run manually after applying)
-- =============================================================================

/*
SELECT category, short_template_text
FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
ORDER BY category;
-- Expected: rows with non-NULL short_template_text where category IN (CRS-C01..C50)
*/
