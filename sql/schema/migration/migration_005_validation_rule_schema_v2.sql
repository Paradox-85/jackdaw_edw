/*
Purpose: Add tier, category, check_type, source_ref, sort_order columns to
         export_validation_rule and validation_result tables.
         Enables rule classification by QA tier (L0–L4), category, and executor type.
         Backwards-compatible — all ADD COLUMN IF NOT EXISTS, DEFAULT values preserved.
Changes: 2026-03-13 — Initial implementation per validation_rules_gap_analysis.md
*/

-- ---------------------------------------------------------------------------
-- export_validation_rule — 5 new columns
-- ---------------------------------------------------------------------------

ALTER TABLE audit_core.export_validation_rule
    ADD COLUMN IF NOT EXISTS tier        TEXT    NULL,
    ADD COLUMN IF NOT EXISTS category    TEXT    NULL,
    ADD COLUMN IF NOT EXISTS source_ref  TEXT    NULL,
    ADD COLUMN IF NOT EXISTS check_type  TEXT    NOT NULL DEFAULT 'dsl',
    ADD COLUMN IF NOT EXISTS sort_order  INTEGER NULL;

-- Constrain check_type to known executor types
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'chk_check_type'
          AND table_schema = 'audit_core'
          AND table_name   = 'export_validation_rule'
    ) THEN
        ALTER TABLE audit_core.export_validation_rule
            ADD CONSTRAINT chk_check_type CHECK (
                check_type IN ('dsl', 'cross_field', 'cross_table', 'aggregate', 'graph', 'metadata')
            );
    END IF;
END;
$$;

-- Constrain tier to QA classification levels
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'chk_tier'
          AND table_schema = 'audit_core'
          AND table_name   = 'export_validation_rule'
    ) THEN
        ALTER TABLE audit_core.export_validation_rule
            ADD CONSTRAINT chk_tier CHECK (
                tier IS NULL OR tier IN ('L0', 'L1', 'L2', 'L3', 'L4')
            );
    END IF;
END;
$$;

-- ---------------------------------------------------------------------------
-- validation_result — 3 new columns for analytics (tier/category breakdown)
-- ---------------------------------------------------------------------------

ALTER TABLE audit_core.validation_result
    ADD COLUMN IF NOT EXISTS tier        TEXT NULL,
    ADD COLUMN IF NOT EXISTS category    TEXT NULL,
    ADD COLUMN IF NOT EXISTS check_type  TEXT NULL;
