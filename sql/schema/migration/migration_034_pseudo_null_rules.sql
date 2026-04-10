-- =============================================================================
-- Migration: 20260409_pseudo_null_rules.sql
-- Autocommit mode — NO BEGIN/COMMIT wrapper
-- Safe to re-run: all statements are idempotent
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. UPDATE DOMAIN_PREFIX_NA — расширить regex: dash + underscore
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule
SET
    rule_expression = 'matches_regex "^(Area|PU|PO|SECE)[-_]NA$"',
    description     = 'Domain-prefixed NA placeholders (Area-NA, PU-NA, PO-NA, '
                      'SECE-NA, Area_NA, PU_NA, PO_NA, SECE_NA) — source-system '
                      'null sentinels, must be normalized to canonical "NA"'
WHERE rule_code = 'DOMAIN_PREFIX_NA';


-- ---------------------------------------------------------------------------
-- 2. INSERT TAG_PREFIX_NA — один ряд, scope=common
--    ON CONFLICT DO UPDATE позволяет переприменять скрипт без ошибок
-- ---------------------------------------------------------------------------
INSERT INTO audit_core.export_validation_rule (
    id, rule_code, scope, object_field, description,
    rule_expression, fix_expression, is_builtin, is_blocking,
    severity, object_status, tier, category, source_ref,
    check_type, sort_order
) VALUES (
    gen_random_uuid(),
    'TAG_PREFIX_NA',
    'common',
    NULL,
    'Extended domain-prefixed NA placeholders (Tag-NA, Tag_NA, Signal_NA, '
    'Loop_NA, Equip_NA, Instr_NA, Doc_NA, Vendor_NA, Mfr_NA, etc.) — '
    'covers all domain prefix families. Applies to tag_property and '
    'equipment_property scopes.',
    'matches_regex "^(Tag|Signal|Loop|Equip|Instr|Doc|Vendor|Mfr|Model|Class|Disc|System|Sub|Parent|Child|Group|Unit|Zone)[-_]NA$"',
    'normalize_pseudo_null',
    true,
    false,
    'Warning',
    'Active',
    'L2',
    'Completeness & Validity',
    'JDAW-PT-D-JA-7739-00003',
    'dsl',
    210
)
ON CONFLICT (rule_code) DO UPDATE SET
    rule_expression = EXCLUDED.rule_expression,
    description     = EXCLUDED.description,
    fix_expression  = EXCLUDED.fix_expression,
    sort_order      = EXCLUDED.sort_order;


-- ---------------------------------------------------------------------------
-- 3. INSERT NOT_APPLICABLE_VARIANT — один ряд, scope=common
-- ---------------------------------------------------------------------------
INSERT INTO audit_core.export_validation_rule (
    id, rule_code, scope, object_field, description,
    rule_expression, fix_expression, is_builtin, is_blocking,
    severity, object_status, tier, category, source_ref,
    check_type, sort_order
) VALUES (
    gen_random_uuid(),
    'NOT_APPLICABLE_VARIANT',
    'common',
    NULL,
    'Verbose "not applicable" variants (N.A., n/a, N/A, n.a., '
    'not applicable, not appl.) — must be normalized to canonical "NA"',
    'matches_regex "(?i)^(N\\.A\\.|n/a|n\\.a\\.|not\\s+applicable|not\\s+appl\\.?)$"',
    'normalize_pseudo_null',
    true,
    false,
    'Warning',
    'Active',
    'L2',
    'Completeness & Validity',
    'JDAW-PT-D-JA-7739-00003',
    'dsl',
    215
)
ON CONFLICT (rule_code) DO UPDATE SET
    rule_expression = EXCLUDED.rule_expression,
    description     = EXCLUDED.description,
    fix_expression  = EXCLUDED.fix_expression,
    sort_order      = EXCLUDED.sort_order;


-- ---------------------------------------------------------------------------
-- 4. UPDATE VALUE_UOM_COMBINED_IN_CELL — добавить fix_expression
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule
SET
    fix_expression  = 'split_value_uom',
    description     = 'PROPERTY_VALUE contains embedded UoM — e.g. "490mm", '
                      '"4 - 50 mm", "49063mm2", "17013mm", "100kW", "3.5bar(g)". '
                      'Auto-split: numeric → PROPERTY_VALUE, UoM → PROPERTY_VALUE_UOM.',
    is_blocking     = false
WHERE rule_code = 'VALUE_UOM_COMBINED_IN_CELL';


-- ---------------------------------------------------------------------------
-- 5. VERIFY — результат должен быть 4 строки
-- ---------------------------------------------------------------------------
SELECT
    rule_code,
    scope,
    left(rule_expression, 55)  AS rule_expression_preview,
    fix_expression,
    tier,
    sort_order
FROM audit_core.export_validation_rule
WHERE rule_code IN (
    'DOMAIN_PREFIX_NA',
    'TAG_PREFIX_NA',
    'NOT_APPLICABLE_VARIANT',
    'VALUE_UOM_COMBINED_IN_CELL'
)
ORDER BY sort_order NULLS LAST, rule_code;