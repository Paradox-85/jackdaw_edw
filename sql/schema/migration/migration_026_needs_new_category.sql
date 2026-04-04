/*
Purpose: Add NEEDS_NEW_CATEGORY status to CRS comment workflow.
         Extend crs_llm_template_staging to accept rows with NULL category
         and a new 'NeedsNewCategory' object_status value.

Verified against live DB 2026-04-04:
  - crs_comment.status constraint: RECEIVED, IN_REVIEW, RESPONDED, APPROVED, CLOSED, DEFERRED
  - crs_llm_template_staging.suggested_category: NOT NULL (varchar 20)
  - crs_llm_template_staging.object_status constraint: PendingReview, Approved, Rejected

Apply BEFORE deploying code changes that write NEEDS_NEW_CATEGORY rows.
*/

-- 1. Extend crs_comment status constraint (preserves all existing values)
ALTER TABLE audit_core.crs_comment
    DROP CONSTRAINT IF EXISTS crs_comment_status_check;

ALTER TABLE audit_core.crs_comment
    ADD CONSTRAINT crs_comment_status_check
    CHECK (status IN (
        'RECEIVED',
        'IN_REVIEW',
        'RESPONDED',
        'APPROVED',
        'CLOSED',
        'DEFERRED',
        'NEEDS_NEW_CATEGORY'
    ));

-- 2. Allow NULL suggested_category (NEEDS_NEW_CATEGORY rows have no category to suggest)
ALTER TABLE audit_core.crs_llm_template_staging
    ALTER COLUMN suggested_category DROP NOT NULL;

-- 3. Extend object_status constraint to include NeedsNewCategory
ALTER TABLE audit_core.crs_llm_template_staging
    DROP CONSTRAINT IF EXISTS chk_llm_staging_status;

ALTER TABLE audit_core.crs_llm_template_staging
    ADD CONSTRAINT chk_llm_staging_status
    CHECK (object_status IN (
        'PendingReview',
        'Approved',
        'Rejected',
        'NeedsNewCategory'
    ));
