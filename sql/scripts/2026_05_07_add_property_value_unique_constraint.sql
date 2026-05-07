-- Migration: add unique constraint to project_core.property_value
-- Date: 2026-05-07
-- Pre-condition: duplicate_count = 0 confirmed via scripts/deduplicate_property_values.py --dry-run
-- Rollback: ALTER TABLE project_core.property_value DROP CONSTRAINT uq_property_value_tag_property_status;

ALTER TABLE project_core.property_value
    ADD CONSTRAINT uq_property_value_tag_property_status
    UNIQUE (tag_id, property_id, property_value, property_uom_raw, object_status);
