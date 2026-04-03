-- migration_013_crs_audit_reset_type.sql
-- Extends change_type CHECK to allow 'RESET' for UI-initiated classification resets.

ALTER TABLE audit_core.crs_comment_audit
    DROP CONSTRAINT IF EXISTS crs_comment_audit_change_type_check;

ALTER TABLE audit_core.crs_comment_audit
    ADD CONSTRAINT crs_comment_audit_change_type_check
        CHECK (change_type IN ('INSERT', 'UPDATE', 'DELETE', 'RESET'));