/*
Purpose: Add export-facing columns to project_core.tag for EIS Tag Register report (seq 003).
Params:  None.
Output:  4 new columns + plant_id FK + partial index on plant_id.
Errors:  IF NOT EXISTS guards make this idempotent — safe to re-run.
Changes: 2026-03-10 — Initial migration for Reports-as-ETL module.
*/

ALTER TABLE project_core.tag
    -- Plant resolved via area.plant_id during sync_tag_data import
    ADD COLUMN IF NOT EXISTS plant_id                            UUID NULL
        REFERENCES reference_core.plant(id) ON DELETE NO ACTION,
    -- Loaded directly from MTR Excel: SAFETY_CRITICAL_ITEM column
    ADD COLUMN IF NOT EXISTS safety_critical_item                TEXT NULL,
    -- Loaded directly from MTR Excel: SAFETY_CRITICAL_ITEM _REASON_AWARDED column
    ADD COLUMN IF NOT EXISTS safety_critical_item_reason_awarded TEXT NULL,
    -- Loaded directly from MTR Excel: PRODUCTION_CRITICAL_ITEM column
    ADD COLUMN IF NOT EXISTS production_critical_item            TEXT NULL;

-- Why partial index: majority of tags have plant_id after first sync; NULL only pre-migration
CREATE INDEX IF NOT EXISTS idx_tag_plant_id
    ON project_core.tag(plant_id)
    WHERE plant_id IS NOT NULL;
