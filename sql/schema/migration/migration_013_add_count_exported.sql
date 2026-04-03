/*
Purpose: Add count_exported column to audit_core.sync_run_stats.
         Fixes bug in export_pipeline.py where row_count was incorrectly written
         to count_unchanged instead of a dedicated export counter column.
Date:    2026-03-18
*/

ALTER TABLE audit_core.sync_run_stats
    ADD COLUMN IF NOT EXISTS count_exported INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN audit_core.sync_run_stats.count_exported
    IS 'Number of rows written to the EIS export CSV file. Set by export_pipeline._log_audit_end().';
