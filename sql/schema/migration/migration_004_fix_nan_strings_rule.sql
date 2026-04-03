/*
Purpose: Fix NO_NAN_STRINGS rule — align detection expression with fix expression.
Problem: rule_expression '* icontains "nan"' (substring match) flagged words like
         "Nansen" or "advance" as violations. fix_expression 'replace_nan' only
         replaces exact nan/NaN values, so false positives were never cleared,
         inflating count_errors in audit_core.sync_run_stats indefinitely.
Fix:     Switch to full-string regex match so detection and fix cover the same set.
Changes: 2026-03-13 — Initial fix.
*/

UPDATE audit_core.export_validation_rule
SET    rule_expression = '* matches_regex "(?i)^nan$"'
WHERE  rule_code = 'NO_NAN_STRINGS';
