-- migration_031_fix_dash_regex.sql
-- Fix: TAG_DESC_NO_LEADING_TRAILING_DASH rule used a capture-group
-- regex which caused pandas str.contains() to silently return 0
-- violations (UserWarning: "has match groups, use str.extract").
-- Removing the outer capture group `(...)` restores correct behaviour.
-- Verified live: 3/5 test samples now detected and auto-fixed.

UPDATE audit_core.export_validation_rule
SET
    rule_expression = 'TAG_DESCRIPTION matches_regex "^\\s*-|-\\s*$"',
    updated_at      = NOW()
WHERE rule_code = 'TAG_DESC_NO_LEADING_TRAILING_DASH';

-- Verify
SELECT rule_code, rule_expression, fix_expression, is_builtin
FROM audit_core.export_validation_rule
WHERE rule_code = 'TAG_DESC_NO_LEADING_TRAILING_DASH';
