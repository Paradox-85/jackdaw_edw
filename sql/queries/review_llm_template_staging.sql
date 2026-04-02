-- =============================================================================
-- review_llm_template_staging.sql
--
-- Purpose:
--   Helper queries for reviewing LLM-suggested CRS templates.
--   Run these manually to approve or reject entries in the staging table
--   before promoting them to the read-only reference table.
--
-- Workflow:
--   1. Run SELECT below to see PendingReview entries ranked by confidence.
--   2. For each entry:
--      - Approve:  UPDATE ... SET object_status='Approved', reviewed_at=now()
--      - Reject:   UPDATE ... SET object_status='Rejected', reviewed_at=now(), review_notes='reason'
--   3. Promote approved entries to the reference table using the INSERT template below.
-- =============================================================================


-- =============================================================================
-- 1. Review pending entries (most reliable first)
-- =============================================================================
SELECT
    id,
    suggested_category,
    occurrence_count,
    ROUND(confidence, 3)   AS confidence,
    template_text,
    llm_response,
    revision,
    created_at::date       AS first_seen
FROM audit_core.crs_llm_template_staging
WHERE object_status = 'PendingReview'
ORDER BY occurrence_count DESC, confidence DESC;


-- =============================================================================
-- 2. Approve an entry (replace <uuid> with actual id from query above)
-- =============================================================================
/*
UPDATE audit_core.crs_llm_template_staging
SET
    object_status = 'Approved',
    reviewed_at   = now()
WHERE id = '<uuid>';
*/


-- =============================================================================
-- 3. Reject an entry
-- =============================================================================
/*
UPDATE audit_core.crs_llm_template_staging
SET
    object_status = 'Rejected',
    reviewed_at   = now(),
    review_notes  = 'Wrong category — LLM confused CRS-C08 with CRS-C12'
WHERE id = '<uuid>';
*/


-- =============================================================================
-- 4. Promote approved entry to reference table (manual INSERT)
--    Run once per approved entry. ON CONFLICT DO NOTHING = safe to re-run.
-- =============================================================================
/*
INSERT INTO audit_core.crs_comment_template
    (template_text, template_hash, category, check_type, confidence,
     source, usage_count, last_used_at, created_at, object_status)
SELECT
    template_text,
    template_hash,
    suggested_category,
    check_type,
    confidence,
    'manual',
    0,
    now(),
    now(),
    'Active'
FROM audit_core.crs_llm_template_staging
WHERE id = '<uuid>'
  AND object_status = 'Approved'
ON CONFLICT (template_hash) DO NOTHING;
*/


-- =============================================================================
-- 5. Summary dashboard
-- =============================================================================
/*
SELECT
    object_status,
    COUNT(*)                              AS cnt,
    ROUND(AVG(confidence), 3)             AS avg_confidence,
    ROUND(AVG(occurrence_count), 1)       AS avg_occurrences,
    MAX(last_seen_at)::date               AS latest_seen
FROM audit_core.crs_llm_template_staging
GROUP BY object_status
ORDER BY object_status;
*/
