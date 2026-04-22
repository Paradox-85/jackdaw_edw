-- Migration: 036_add_missing_raw_columns
-- Date: 2026-04-22
-- Purpose: Add raw XLSX columns for PURCHASE_DATE, COMPANY_NAME, REQUISITION_CODE, PART_OF
--          to project_core.tag for snapshot storage and comparison report.
-- Note:    These columns exist in real XLSX but were missing from schema.sql.

ALTER TABLE project_core.tag ADD COLUMN IF NOT EXISTS purchase_date_raw TEXT;
ALTER TABLE project_core.tag ADD COLUMN IF NOT EXISTS company_raw TEXT;
ALTER TABLE project_core.tag ADD COLUMN IF NOT EXISTS requisition_code_raw TEXT;
ALTER TABLE project_core.tag ADD COLUMN IF NOT EXISTS part_of_raw TEXT;
