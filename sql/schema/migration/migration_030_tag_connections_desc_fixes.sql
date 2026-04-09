/*
Migration: 030 — DB-driven fixes for Tag Connections and Tag Description validation rules.
Date:      2026-04-09
Source:    docs/plans/mutable-riding-hanrahan.md
Depends:   migration_005_validation_rule_schema_v2.sql (validation rules table exists).

Changes summary:
  1. FROM_TO_TAG_NOT_EQUAL scope → 'common' (fixes scope mismatch for tag_connection exports)
  2. TAG_DESC_NO_LEADING_TRAILING_DASH → DB-driven strip_edge_char fix

Code changes (separate commits):
  - etl/flows/export_tag_connections_deploy.py: DISTINCT + self-loop SQL guard
  - etl/tasks/export_transforms.py: remove Step 12b (strip edge dashes)
  - etl/tasks/export_validation.py: add strip_edge_char DSL operator
*/

-- ===========================================================================
-- BLOCK 1: FROM_TO_TAG_NOT_EQUAL scope → 'common'
-- ---------------------------------------------------------------------------
-- Problem: Rule has scope='tag' but export_tag_connections uses scope='tag_connection'.
-- The load_validation_rules() function filters by scope IN ('common', :scope),
-- so the rule never loads for tag_connection exports.
--
-- Solution: Change scope to 'common' so the rule loads for ALL exports.
-- This is correct because FROM_TO_TAG_NOT_EQUAL is a structural cross-column
-- check that applies to any object with FROM_TAG and TO_TAG fields, not just tags.
-- ===========================================================================

UPDATE audit_core.export_validation_rule
SET scope = 'common',
    description = 'FROM_TAG_NAME must not equal TO_TAG_NAME — self-loop connections are invalid for physical signal paths (applies to all exports with FROM/TO fields)'
WHERE rule_code = 'FROM_TO_TAG_NOT_EQUAL';


-- ===========================================================================
-- BLOCK 2: TAG_DESC_NO_LEADING_TRAILING_DASH → DB-driven strip_edge_char fix
-- ---------------------------------------------------------------------------
-- Problem: Step 12b in clean_engineering_text() strips leading/trailing dashes
-- from TAG_DESCRIPTION, but this is hardcoded and cannot be configured via DB.
--
-- Solution: Move this logic to DB-driven validation rule with fix_expression.
-- The new 'strip_edge_char' DSL operator removes leading/trailing occurrences
-- of a specified character (equivalent to Python s.strip("X").strip()).
-- ===========================================================================

UPDATE audit_core.export_validation_rule
SET is_builtin      = true,
    fix_expression  = 'strip_edge_char "-"',
    description     = 'TAG_DESCRIPTION must not start or end with a dash — leading/trailing dashes are source artefacts that should be stripped (auto-fixed via strip_edge_char "-" DSL operator)'
WHERE rule_code = 'TAG_DESC_NO_LEADING_TRAILING_DASH';


-- ===========================================================================
-- Verification queries (for manual testing after migration)
-- ===========================================================================

-- Verify FROM_TO_TAG_NOT_EQUAL is now common scope:
-- SELECT rule_code, scope, is_builtin, fix_expression
-- FROM audit_core.export_validation_rule
-- WHERE rule_code = 'FROM_TO_TAG_NOT_EQUAL';
-- Expected: scope='common', is_builtin=false, fix_expression=NULL

-- Verify TAG_DESC_NO_LEADING_TRAILING_DASH is now builtin with fix:
-- SELECT rule_code, scope, is_builtin, fix_expression
-- FROM audit_core.export_validation_rule
-- WHERE rule_code = 'TAG_DESC_NO_LEADING_TRAILING_DASH';
-- Expected: scope='common', is_builtin=true, fix_expression='strip_edge_char "-"'
