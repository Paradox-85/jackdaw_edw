-- Migration: 0025_add_safety_critical_item_group
-- Date: 2026-04-21
-- Author: Claude Code (per user request)
--
-- Purpose:
--   1. Add safety_critical_item_group TEXT column to project_core.tag
--      (raw denormalized string for EIS export and comparison)
--   2. Clean up existing bad snapshot values with "None"/"nan"/"null" strings
--
-- Notes:
--   - Column stores space-separated SECE group codes from source XLSX
--   - Examples: "DS01", "DS01 IP01 ER01 ER03 ER06 PS04 SS01"
--   - Coexists with normalized mapping.tag_sece (FK relationship)
--   - Raw string used for: direct EIS export, point-in-time comparison
--   - Mapping table used for: queries, joins, analytics
--   - Snapshot key documented as "sece_group" in audit_core.tag_status_history.snapshot

-- 1. Add column
ALTER TABLE project_core.tag
    ADD COLUMN IF NOT EXISTS safety_critical_item_group TEXT;

COMMENT ON COLUMN project_core.tag.safety_critical_item_group IS
    'SECE group codes from source XLSX column SAFETY_CRITICAL_ITEM _GROUP (note trailing space).
     Space-separated list. Examples: "DS01", "DS01 IP01 ER01 ER03 ER06 PS04 SS01".
     Raw denormalized string for EIS export and comparison. Normalized N:M mapping stored
     in mapping.tag_sece table. Also stored in audit_core.tag_status_history.snapshot
     as key "sece_group" for point-in-time comparison.';

-- 2. Clean up bad snapshot values from older import runs
-- Remove "None", "nan", "NaT", "null" sentinel strings that cause false positives
UPDATE audit_core.tag_status_history
SET snapshot = (
    SELECT jsonb_object_agg(key, value)
    FROM jsonb_each_text(snapshot)
    WHERE lower(value) NOT IN ('none', 'nan', 'nat', 'null')
      AND value != ''
)
WHERE snapshot IS NOT NULL
  AND snapshot::text ~ '(:"None"|:"nan"|:"null"|:"NaT")';

-- 3. Verify cleanup (optional, can be removed)
-- SELECT count(*) AS bad_snapshots_remaining
-- FROM audit_core.tag_status_history
-- WHERE snapshot::text ~ '(:"None"|:"nan"|:"null"|:"NaT")';
