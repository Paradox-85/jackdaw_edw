-- migration_025: Add deferred_reason column to audit_core.crs_comment
-- Records the specific reason Tier 0 deferred a comment (not classified by LLM).
-- Populated by save_classification_results() when classification_tier = 0.

ALTER TABLE audit_core.crs_comment
    ADD COLUMN IF NOT EXISTS deferred_reason TEXT NULL;

COMMENT ON COLUMN audit_core.crs_comment.deferred_reason IS
    'Tier 0 skip reason. Values: INFORMATIONAL (status note, not actionable), '
    'TAG_NOT_IN_EDW (tag_name present but tag_id NULL), '
    'TAG_INACTIVE (tag exists but status is Inactive/Voided/Cancelled), '
    'TAG_NO_STATUS (tag exists but tag_status IS NULL or empty). '
    'NULL for rows processed by Tier 1+.';

CREATE INDEX idx_crs_comment_deferred_reason
    ON audit_core.crs_comment (deferred_reason)
    WHERE deferred_reason IS NOT NULL;
