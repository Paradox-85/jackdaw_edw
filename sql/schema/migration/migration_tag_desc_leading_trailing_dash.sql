/*
Fix: TAG_DESCRIPTION leading/trailing dash artefacts cleanup
Date: 2026-04-08
Purpose: Catch and report TAG_DESCRIPTION values with leading or trailing dashes
         (data entry artefacts from copy-paste operations).
Note:    fix_expression is NULL because clean_engineering_text() handles
         this fix at sanitize_dataframe() time (Step 12b above).
         The rule exists for full scan observability only.
*/

INSERT INTO audit_core.export_validation_rule (
    id, rule_code, scope, object_field, description,
    rule_expression, fix_expression,
    is_builtin, is_blocking, severity, object_status,
    tier, category, source_ref, check_type, sort_order
) VALUES (
    gen_random_uuid(),
    'TAG_DESC_NO_LEADING_TRAILING_DASH',
    'common',
    'TAG_DESCRIPTION',
    'TAG_DESCRIPTION must not start or end with a dash. '
    'These are data entry artefacts from copy-paste (e.g. "- Description" or "Description -").',
    'TAG_DESCRIPTION matches_regex "(^\\s*-|\\-\\s*$)"',
    NULL,
    FALSE,
    FALSE,
    'Warning',
    'Active',
    'L1',
    'Validity',
    NULL,
    'dsl',
    55
) ON CONFLICT (rule_code) DO NOTHING;
