-- Migration: Add and update validation rules for pseudo-null normalization
-- Purpose: Extend pseudo-null rules to support Tag prefixes, verbose variants, and UoM splitting
-- Date: 2026-04-09
-- Dependencies: None (can run independently)

-- UPDATE DOMAIN_PREFIX_NA - extend regex to support hyphen AND underscore
UPDATE audit_core.export_validation_rule
SET rule_expression = 'str.contains ".*-NA$" or str.contains ".*_NA$"',
    description = 'Domain-prefixed NA variants with hyphen or underscore (Area-NA, PU_NA, PO-NA, SECE_NA, etc.)'
WHERE rule_code = 'DOMAIN_PREFIX_NA'
  AND scope = 'common';

-- INSERT TAG_PREFIX_NA - new rule for all Tag-prefixed variants
INSERT INTO audit_core.export_validation_rule (
    id,
    rule_code,
    scope,
    object_field,
    description,
    rule_expression,
    fix_expression,
    is_builtin,
    is_blocking,
    severity,
    object_status,
    tier,
    category,
    source_ref,
    check_type,
    sort_order
)
SELECT
    gen_random_uuid(),
    'TAG_PREFIX_NA',
    'tag_property',
    NULL,
    'Tag-prefixed NA variants (Tag-NA, Signal_NA, Loop_NA, etc.)',
    'str.contains ".*-NA$" or str.contains ".*_NA$"',
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
WHERE NOT EXISTS (
    SELECT 1 FROM audit_core.export_validation_rule
    WHERE rule_code = 'TAG_PREFIX_NA'
);

-- Also add TAG_PREFIX_NA to equipment_property scope
INSERT INTO audit_core.export_validation_rule (
    id,
    rule_code,
    scope,
    object_field,
    description,
    rule_expression,
    fix_expression,
    is_builtin,
    is_blocking,
    severity,
    object_status,
    tier,
    category,
    source_ref,
    check_type,
    sort_order
)
SELECT
    gen_random_uuid(),
    'TAG_PREFIX_NA',
    'equipment_property',
    NULL,
    'Tag-prefixed NA variants (Tag-NA, Signal_NA, Loop_NA, etc.)',
    'str.contains ".*-NA$" or str.contains ".*_NA$"',
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
WHERE NOT EXISTS (
    SELECT 1 FROM audit_core.export_validation_rule
    WHERE rule_code = 'TAG_PREFIX_NA'
      AND scope = 'equipment_property'
);

-- INSERT NOT_APPLICABLE_VARIANT - rule for verbose pseudo-null variants
INSERT INTO audit_core.export_validation_rule (
    id,
    rule_code,
    scope,
    object_field,
    description,
    rule_expression,
    fix_expression,
    is_builtin,
    is_blocking,
    severity,
    object_status,
    tier,
    category,
    source_ref,
    check_type,
    sort_order
)
SELECT
    gen_random_uuid(),
    'NOT_APPLICABLE_VARIANT',
    'common',
    NULL,
    'Verbose "not applicable" variants (N.A., n/a, not applicable)',
    'str.matches_regex "(?i)^(N\.A\.|n/a|n\.a\.|not\s+applicable|not\s+appl\.?)$"',
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
WHERE NOT EXISTS (
    SELECT 1 FROM audit_core.export_validation_rule
    WHERE rule_code = 'NOT_APPLICABLE_VARIANT'
      AND scope = 'common'
);

-- UPDATE VALUE_UOM_COMBINED_IN_CELL - add fix_expression and improve regex
UPDATE audit_core.export_validation_rule
SET rule_expression = 'str.matches_regex "^[\d.,]+(?:\s*[-–]\s*[\d.,]+)?\s*[A-Za-z°²³µμ%][A-Za-z0-9°²³/.*()\\-]*$"',
    fix_expression = 'split_value_uom',
    description = 'Combined value and UoM in single cell (e.g., "490mm", "3.5bar(g)")',
    is_blocking = false
WHERE rule_code = 'VALUE_UOM_COMBINED_IN_CELL'
  AND scope IN ('tag_property', 'equipment_property');

-- Verify the changes
SELECT
    rule_code,
    scope,
    rule_expression,
    fix_expression,
    is_builtin,
    is_blocking,
    tier,
    category
FROM audit_core.export_validation_rule
WHERE rule_code IN ('DOMAIN_PREFIX_NA', 'TAG_PREFIX_NA', 'NOT_APPLICABLE_VARIANT', 'VALUE_UOM_COMBINED_IN_CELL')
ORDER BY rule_code, scope;
