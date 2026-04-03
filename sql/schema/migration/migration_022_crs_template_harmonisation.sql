-- =============================================================================
-- migration_022_crs_template_harmonisation.sql
-- Purpose: Harmonise audit_core.crs_comment_template:
--   1. Fix invalid check_type values: tag_data→tag, reference→tag, other→domain
--   2. Reformat CRS-C01..C50 to 3-digit CRS-C001..C050
--   3. Assign unique CRS-C051..CRS-C229 (one per row) to 179 old-format rows
--   4. DROP redundant columns: domain, category_code, response_template
--   5. COMMENT ON COLUMN — replace stale content
-- Pre-condition: migration_021_add_crs_llm_staging.sql applied
-- Idempotent: Yes (WHERE guards on each UPDATE section; DROP IF EXISTS)
-- Date: 2026-04-03
-- =============================================================================

BEGIN;

-- ── Section 1: Fix check_type='tag_data' → 'tag' ────────────────────────────
-- 16 rows with check_type='tag_data' (source: old TAG_DATA category group)
UPDATE audit_core.crs_comment_template
SET check_type = 'tag',
    updated_at = now()
WHERE check_type = 'tag_data'
  AND object_status = 'Active';

-- ── Section 2: Fix check_type='reference' → 'tag' ────────────────────────────
-- 1 row (CRS-C029, plant code check) — plant codes are tag-level attributes
UPDATE audit_core.crs_comment_template
SET check_type = 'tag',
    updated_at = now()
WHERE check_type = 'reference'
  AND object_status = 'Active';

-- ── Section 3: Fix check_type='other' → domain-specific value ────────────────
-- 2 rows with document-related short_template_text
UPDATE audit_core.crs_comment_template
SET check_type = 'document',
    updated_at = now()
WHERE check_type = 'other'
  AND object_status = 'Active'
  AND short_template_text IN (
      'Documents not in DMS or in NYI status',
      'Wrong CIS submission template used'
  );

-- Remaining OTHER rows relate to tag-level data issues (6 rows)
UPDATE audit_core.crs_comment_template
SET check_type = 'tag',
    updated_at = now()
WHERE check_type = 'other'
  AND object_status = 'Active';

-- ── Section 4: Reformat CRS-C01..C50 → CRS-C001..C050 (pad to 3 digits) ─────
-- Matches exactly 2-digit suffix (CRS-C01 through CRS-C99)
UPDATE audit_core.crs_comment_template
SET category   = regexp_replace(category, '^CRS-C(\d{2})$', 'CRS-C0\1'),
    updated_at = now()
WHERE object_status = 'Active'
  AND category SIMILAR TO 'CRS-C[0-9]{2}';

-- ── Section 5: Assign unique CRS-C051..CRS-C229 to each old-format row ───────
-- Deterministic order: check_type, short_template_text, template_hash
-- One unique code PER ROW — 179 rows → CRS-C051..CRS-C229
-- Idempotent: WHERE excludes rows already in 3-digit CRS-Cxxx format
WITH numbered AS (
    SELECT id,
           row_number() OVER (
               ORDER BY check_type, short_template_text, template_hash
           ) AS rn
    FROM audit_core.crs_comment_template
    WHERE object_status = 'Active'
      AND category NOT SIMILAR TO 'CRS-C[0-9]{3}'
)
UPDATE audit_core.crs_comment_template t
SET category   = format('CRS-C%s', lpad((50 + r.rn)::text, 3, '0')),
    updated_at = now()
FROM numbered r
WHERE t.id = r.id;

-- ── Section 6: DROP redundant columns ─────────────────────────────────────────
-- domain         — always supposed to = check_type, partially filled, never read by classifiers
-- category_code  — always supposed to = category, all NULL currently, redundant UNIQUE constraint
-- response_template — selected in Tier 1 but never used in output
ALTER TABLE audit_core.crs_comment_template
    DROP COLUMN IF EXISTS domain,
    DROP COLUMN IF EXISTS category_code,
    DROP COLUMN IF EXISTS response_template;

-- ── Section 7: COMMENT ON COLUMN — replace stale content ──────────────────────
COMMENT ON COLUMN audit_core.crs_comment_template.category IS
    'CRS classification code — always 3-digit: CRS-C001..CRS-C050 (canonical categories) '
    'or CRS-C051..CRS-C229 (granular sub-categories derived from real CRS comments). '
    'Must be present in _VALID_CATEGORIES — etl/tasks/crs_tier3_llm_classifier.py.';

COMMENT ON COLUMN audit_core.crs_comment_template.check_type IS
    'EIS domain for Tier-3 LLM template filtering. '
    'Valid values: tag, area, process_unit, equipment, model_part, '
    'tag_connection, purchase_order, tag_class_property, tag_property, '
    'equipment_property, document. '
    'Matched via substring: domain.lower() in check_type.lower() — '
    '_build_categories_line() in etl/tasks/crs_tier3_llm_classifier.py. '
    'Also used for Tier-1 domain pre-filtering to reduce cross-domain false positives.';

COMMENT ON COLUMN audit_core.crs_comment_template.short_template_text IS
    'One-line description for Tier-3 LLM prompt injection. '
    'Format: brief issue description, e.g. "tag description missing". '
    'Used by _build_categories_line() to build the categories hint for the LLM.';

COMMENT ON COLUMN audit_core.crs_comment_template.source IS
    'Origin of the template: manual (curated by engineer), llm (auto-generated '
    'by Tier-3), rule (derived from validation rule). '
    'Useful for filtering: only manual templates are trusted for Tier-1 matching.';

COMMIT;

-- =============================================================================
-- Verification queries (run after COMMIT):
-- =============================================================================

-- a) Zero rows with old-format category (not 3-digit CRS-Cxxx):
/*
SELECT count(*) FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
  AND category NOT SIMILAR TO 'CRS-C[0-9]{3}';
-- Expected: 0
*/

-- b) Zero rows with invalid check_type:
/*
SELECT count(*) FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
  AND check_type IN ('reference', 'other', 'tag_data');
-- Expected: 0
*/

-- c) Distribution C001..C050 vs C051..C229:
/*
SELECT
    CASE WHEN category <= 'CRS-C050' THEN 'C001..C050' ELSE 'C051..C229' END AS range,
    count(*)
FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
GROUP BY 1
ORDER BY 1;
-- Expected: C001..C050=50, C051..C229=179
*/

-- d) Total active templates unchanged:
/*
SELECT count(*) FROM audit_core.crs_comment_template
WHERE object_status = 'Active';
-- Expected: 229
*/

-- e) Dropped columns no longer exist:
/*
SELECT attname FROM pg_attribute
WHERE attrelid = 'audit_core.crs_comment_template'::regclass
  AND attname IN ('domain', 'category_code', 'response_template')
  AND NOT attisdropped;
-- Expected: 0 rows
*/

-- f) New C051..C229 category list for _FALLBACK_CATEGORIES:
/*
SELECT category, short_template_text
FROM audit_core.crs_comment_template
WHERE object_status = 'Active'
  AND category > 'CRS-C050'
ORDER BY category;
*/
