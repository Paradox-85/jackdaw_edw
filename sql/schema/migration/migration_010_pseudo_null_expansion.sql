/*
Migration: 008 — Pseudo-null placeholder expansion.
Date:      2026-03-13
Source:    EIS source-system replacement table (!replaceData array).
Depends:   migration_007_validation_rules_cleanup.sql

Changes summary:
  BLOCK 1: Extend NUMERIC_PSEUDO_NULL_VARIANT regex to cover all 9{5,} variants
            (with optional unit suffix: 999999999kg, 999999999Pa.s, 9999999mm, etc.)
            and switch fix to new normalize_pseudo_null engine operation.
  BLOCK 2: Insert 3 new common-scope rules:
            DOMAIN_PREFIX_NA    — Area-NA, PU-NA, PO-NA, SECE-NA
            EPOCH_DATE_PSEUDO_NULL — 01/01/1990 00:00:00
            SINGLE_DASH_NULL    — bare "-"
*/


-- ===========================================================================
-- BLOCK 1: EXTEND NUMERIC_PSEUDO_NULL_VARIANT
-- ---------------------------------------------------------------------------
-- Previous regex: ^999999$ (6-nine variant only, fix: replace "999999" "NA").
-- New regex: ^9{5,}[\d./a-zA-Z ]*$ — covers all length variants (5–10 nines)
-- with or without unit suffix:
--   pure nines:  99999, 999999, 9999999, 999999999
--   extra digits: 9999999000, 9999999993
--   with unit:  999999999kg, 999999999Pa.s, 999999999mm2, 9999999mm,
--               9999999000ampere, 999999ampere, 999999999deg/s, 999999999N/m
-- ===========================================================================

UPDATE audit_core.export_validation_rule
SET rule_expression = 'PROPERTY_VALUE matches_regex "^9{5,}[\\d./a-zA-Z ]*$"',
    fix_expression  = 'normalize_pseudo_null',
    description     = 'Numeric pseudo-NULL placeholders (9{5,} with optional unit suffix: '
                      '999999999, 999999999kg, 999999999Pa.s, 9999999mm etc.) — '
                      'all normalized to "NA" (EIS source-system sentinel values)'
WHERE rule_code = 'NUMERIC_PSEUDO_NULL_VARIANT';


-- ===========================================================================
-- BLOCK 2: INSERT new pseudo-null rules (scope='common')
-- All use normalize_pseudo_null fix op (added to export_validation.py engine).
-- ===========================================================================

INSERT INTO audit_core.export_validation_rule
    (rule_code, scope, object_field, description,
     rule_expression, fix_expression,
     is_builtin, is_blocking, severity,
     tier, category, check_type, sort_order)
VALUES

-- DOMAIN_PREFIX_NA: EIS source uses Area-NA, PU-NA, PO-NA, SECE-NA as
-- domain-scoped null placeholders in property value and register fields.
('DOMAIN_PREFIX_NA',
 'common', 'PROPERTY_VALUE',
 'Domain-prefixed NA placeholders (Area-NA, PU-NA, PO-NA, SECE-NA) are '
 'source-system null sentinels — must be normalized to strict "NA"',
 'PROPERTY_VALUE matches_regex "^(Area|PU|PO|SECE)-NA$"', 'normalize_pseudo_null',
 true, false, 'Warning',
 'L2', 'Validity', 'dsl', 57),

-- EPOCH_DATE_PSEUDO_NULL: source system default "no date" value is 01/01/1990.
-- May appear with time component: "01/01/1990 00:00:00".
('EPOCH_DATE_PSEUDO_NULL',
 'common', 'PROPERTY_VALUE',
 'Epoch date "01/01/1990" is the source-system default "no date" placeholder — '
 'must be replaced with "NA" (EIS does not accept date-format null surrogates)',
 'PROPERTY_VALUE matches_regex "^01/01/1990"', 'normalize_pseudo_null',
 true, false, 'Warning',
 'L2', 'Validity', 'dsl', 58),

-- SINGLE_DASH_NULL: bare hyphen "-" used as null indicator in some source fields.
('SINGLE_DASH_NULL',
 'common', 'PROPERTY_VALUE',
 'Single dash "-" is a source-system pseudo-null placeholder — '
 'must be replaced with "NA"',
 'PROPERTY_VALUE matches_regex "^-$"', 'normalize_pseudo_null',
 true, false, 'Warning',
 'L2', 'Validity', 'dsl', 59)

ON CONFLICT (rule_code) DO NOTHING;
