/*
Purpose: Add expected_result (and group_by_field) to CRS Phase 3 views.
         v_template_queries was missing group_by_field and expected_result — causing
         batch validator to silently return 0 results (try/except swallowed the column error).
         v_crs_resolution_report was missing expected_result — breaking {expected_result}
         placeholder substitution in cascade evaluator formal responses.
Changes: 2026-04-28 — Fix missing columns in both Phase 3 views.
*/

CREATE OR REPLACE VIEW "audit_core"."v_template_queries" AS
SELECT
    ct.id                   AS template_id,
    ct.category_code        AS template_category,
    ct.check_type,
    ct.template_text,
    vq.id                   AS query_id,
    vq.query_code,
    vq.query_name,
    vq.query_type,
    vq.evaluation_strategy,
    vq.has_parameters,
    vq.parameter_names,
    vq.sql_query,
    vq.response_template,
    vq.group_by_field,
    vq.expected_result,
    tqm.priority
FROM "audit_core"."crs_template_query_map" tqm
JOIN "audit_core"."crs_comment_template"   ct  ON ct.id  = tqm.template_id
JOIN "audit_core"."crs_validation_query"   vq  ON vq.id  = tqm.query_id
WHERE tqm.object_status = 'Active'
  AND ct.object_status  = 'Active'
  AND vq.is_active      = true
  AND vq.query_type     = 'GROUP';

CREATE OR REPLACE VIEW "audit_core"."v_crs_resolution_report" AS
SELECT
    cc.id                    AS comment_id,
    cc.comment_id            AS comment_ref,
    cc.revision,
    cc.tag_name,
    cc.status                AS comment_status,
    cc.category_code,
    cc.classification_tier,
    cc.deferred_reason,
    cc.formal_response,
    cc.response_author,
    cc.response_approval_date,
    cv.validation_status,
    cv.validation_result_json,
    cv.validation_error,
    cv.validation_timestamp,
    cv.run_id                AS validation_run_id,
    vq.query_code,
    vq.query_name,
    vq.category              AS query_category,
    vq.evaluation_strategy,
    vq.response_template,
    vq.group_by_field,
    vq.expected_result
FROM "audit_core"."crs_comment" cc
LEFT JOIN "audit_core"."crs_comment_validation"  cv ON cv.comment_id = cc.id
LEFT JOIN "audit_core"."crs_validation_query"     vq ON vq.id         = cv.validation_query_id
WHERE cc.object_status = 'Active';
