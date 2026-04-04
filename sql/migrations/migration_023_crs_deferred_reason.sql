-- migration_023: Add deferred_reason column to audit_core.crs_comment
-- Records the specific reason Tier 0 deferred a comment.
-- Populated by save_classification_results() when classification_tier = 0.

ALTER TABLE audit_core.crs_comment
    ADD COLUMN IF NOT EXISTS deferred_reason TEXT NULL;

COMMENT ON COLUMN audit_core.crs_comment.deferred_reason IS
    'Tier 0 skip reason. Values:
     INFORMATIONAL        — comment is a status/info note, not an actionable CRS item;
     TAG_NOT_IN_EDW       — tag_name present but tag_id is NULL (tag not found in project_core.tag);
     TAG_INACTIVE         — tag exists but tag_status is Inactive/Void/Voided/Cancelled;
     TAG_NO_STATUS        — tag exists but tag_status is NULL/empty (incomplete tag, likely erroneous);
     TAG_OBJECT_INACTIVE  — tag exists but tag.object_status = Inactive (deactivated in EDW).
     NULL for rows processed by Tier 1–3 (classified, not deferred).';

CREATE INDEX IF NOT EXISTS idx_crs_comment_deferred_reason
    ON audit_core.crs_comment (deferred_reason)
    WHERE deferred_reason IS NOT NULL;
