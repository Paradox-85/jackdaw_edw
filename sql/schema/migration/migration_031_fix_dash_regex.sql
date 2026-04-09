-- migration_031_fix_dash_regex.sql
-- Fix: TAG_DESC_NO_LEADING_TRAILING_DASH regex had 4 backslashes (\\\\s)
-- instead of 1 (\s). Python read literal '\\s' text, not the whitespace
-- class — so str.contains() matched 0 violations and strip_edge_char
-- never fired.
--
-- Root cause: INSERT in migration_030 double-escaped the backslash
-- when writing through Python string → SQL string → DB storage.
--
-- Fix: write exactly one backslash before s so DB stores '\s'.
-- In PostgreSQL dollar-quoted string: \s is already one backslash.
--
-- Verified in container 2026-04-09:
--   BEFORE: rule_expression = 'TAG_DESCRIPTION matches_regex "^\\\\s*-|-\\\\s*$"'
--   AFTER:  rule_expression = 'TAG_DESCRIPTION matches_regex "^\\s*-|-\\s*$"'
--   Violations: 3/4 detected, auto-fixed, sanitize_dataframe OK.

UPDATE audit_core.export_validation_rule
SET rule_expression = $$TAG_DESCRIPTION matches_regex "^\s*-|-\s*$"$$
WHERE rule_code = 'TAG_DESC_NO_LEADING_TRAILING_DASH';

-- Verify result
SELECT rule_code,
       rule_expression,
       fix_expression,
       is_builtin,
       object_status
FROM audit_core.export_validation_rule
WHERE rule_code = 'TAG_DESC_NO_LEADING_TRAILING_DASH';
