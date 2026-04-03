/*
Migration: 007 — Validation rules cleanup, Power Query gap closure, DSL engine extensions.
Date:      2026-03-13
Source:    docs/validation_rules_review_summary.md
Depends:   migration_005_validation_rule_schema_v2.sql (tier, category, check_type columns).

Changes summary:
  P1 (no code change): Remove 4 duplicate rules; fix DISCIPLINE_FK_RESOLVED typo;
                       tune SECE_SEMICOLON_DELIMITER; add fix to DECIMAL_DOT_SEPARATOR.
  P2 (with engine):    Expand NO_INVALID_CHARS; update PSEUDO_NULL_NA_FORMAT;
                       delete DESC_NO_DOUBLE_SPACE; insert 5 new DSL rules.
  P3 (metadata only):  Insert SIGNAL_TAG_NO_DUPLICATES (aggregate, is_builtin=false).
*/

-- ===========================================================================
-- BLOCK 1: DELETE duplicate rules (P1)
-- ---------------------------------------------------------------------------
-- These rules are exact semantic duplicates of newer, properly classified rules.
-- Keeping both would cause double-logging and confusion in violation reports.
-- ===========================================================================

DELETE FROM audit_core.export_validation_rule
WHERE rule_code IN (
    'PROCESS_UNIT_MANDATORY',   -- exact dup of PROCESS_UNIT_NOT_NULL (L2, better tier/source_ref)
    'AREA_CODE_EXPECTED',       -- exact dup of AREA_CODE_NOT_NULL (L2, better tier/source_ref)
    'PO_CODE_NOT_VOID',         -- exact dup of PO_CODE_NOT_VOID_SUFFIX (scope=common, better)
    'TAG_MIN_ONE_DOCUMENT'      -- exact dup of TAG_MIN_DOC_LINK (L3, better tier/check_type)
);


-- ===========================================================================
-- BLOCK 2: FIX TYPO in DISCIPLINE_FK_RESOLVED (P1)
-- ---------------------------------------------------------------------------
-- Bug: second condition reads 'discipline_code_raw not_null' — should be 'discipline_id is_null'.
-- The rule never fires correctly in its current form: it checks the same field twice.
-- ===========================================================================

UPDATE audit_core.export_validation_rule
SET rule_expression = 'discipline_code_raw not_null AND discipline_id is_null',
    description     = 'Raw discipline code present but discipline FK not resolved — code missing from reference_core.discipline'
WHERE rule_code = 'DISCIPLINE_FK_RESOLVED';


-- ===========================================================================
-- BLOCK 3: TUNE existing rules (P1)
-- ===========================================================================

-- SECE_SEMICOLON_DELIMITER: source always uses space-separated values, not comma.
-- Demote to full-scan only — fires only if data source changes in future.
UPDATE audit_core.export_validation_rule
SET is_builtin   = false,
    severity     = 'Info',
    description  = 'SECE multi-values separator check — comma found (source always uses space; fires only if data source changes)'
WHERE rule_code = 'SECE_SEMICOLON_DELIMITER';

-- DECIMAL_DOT_SEPARATOR: Power Query auto-fixes this — validation engine should match.
UPDATE audit_core.export_validation_rule
SET fix_expression = 'replace "," "."',
    is_builtin     = true,
    description    = 'Decimal separator must be dot, not comma — auto-replaced (Power Query: Text.Replace comma with dot when UoM present)'
WHERE rule_code = 'DECIMAL_DOT_SEPARATOR';


-- ===========================================================================
-- BLOCK 4: UPDATE rules requiring new fix-operations in engine (P2)
-- Requires: export_transforms.clean_engineering_text() extended in same release.
-- ===========================================================================

-- NO_INVALID_CHARS: expanded to cover all structural/non-ASCII chars that break CSV
-- or EIS field matching. Previously only caught '<'. Now delegates full repair to
-- encoding_repair which is extended to handle em/en-dashes, unicode hyphens, MM².
UPDATE audit_core.export_validation_rule
SET rule_expression = '* matches_regex "[<>{}|\\^`\u2010\u2013\u2014]"',
    fix_expression  = 'encoding_repair',
    object_field    = NULL,
    description     = 'Structural/non-ASCII chars that break CSV or EIS field matching: <, >, {, }, |, ^, ` (control hazards), en/em-dashes (U+2013/U+2014), unicode hyphen (U+2010), MM² unit artefacts — all repaired by encoding_repair pipeline'
WHERE rule_code = 'NO_INVALID_CHARS';

-- PSEUDO_NULL_NA_FORMAT: expand to catch all NA variants (N/A, N.A, na, n/a).
-- New fix: normalize_na replaces all variants with strict "NA" (added to engine).
UPDATE audit_core.export_validation_rule
SET rule_expression = '* matches_regex "(?i)^(N\.A\.?|N/A|na|n/a)$"',
    fix_expression  = 'normalize_na',
    description     = 'All NA-variant pseudo-null formats (N/A, N.A., N.A, na, n/a) must be normalized to strict "NA" — EIS system expects uppercase two-letter code'
WHERE rule_code = 'PSEUDO_NULL_NA_FORMAT';

-- VOID_DELETED_EXCLUDED_FROM_XREF: extend to also cover document status CAN.
UPDATE audit_core.export_validation_rule
SET description     = 'Tags with status VOID or DELETED and documents with status CAN must be excluded from all cross-reference matrices',
    rule_expression = 'cross_file: tag_name IN xref_matrix WHERE object_status IN (''VOID'',''DELETED'') OR doc_status = ''CAN'''
WHERE rule_code = 'VOID_DELETED_EXCLUDED_FROM_XREF';


-- ===========================================================================
-- BLOCK 5: DELETE superseded rule (P2)
-- ---------------------------------------------------------------------------
-- DESC_NO_DOUBLE_SPACE covered entirely by encoding_repair (step 11: collapse spaces).
-- Keeping it causes redundant violation records for the same issue.
-- ===========================================================================

DELETE FROM audit_core.export_validation_rule
WHERE rule_code = 'DESC_NO_DOUBLE_SPACE';


-- ===========================================================================
-- BLOCK 6: INSERT new DSL rules (P2)
-- All scope='common' → applied to ALL export flows automatically.
-- ===========================================================================

INSERT INTO audit_core.export_validation_rule
    (rule_code, scope, object_field, description,
     rule_expression, fix_expression,
     is_builtin, is_blocking, severity,
     tier, category, check_type, sort_order)
VALUES

-- UNSET_VALUE_IN_ANY_FIELD: universal "unset" cleanup for all columns in all exports.
-- Power Query: Replace_ParentTag replaces "unset" → "". Now extended to all fields.
-- "unset" is a source-system placeholder that can appear in any EAV or tag field.
('UNSET_VALUE_IN_ANY_FIELD',
 'common', NULL,
 'Source-system placeholder "unset" must be replaced with empty string in all fields — applies to PARENT_TAG_NAME, property values, descriptions, and any other column',
 '* icontains "unset"', 'replace "unset" ""',
 true, false, 'Info',
 'L1', 'Syntax', 'dsl', 25),

-- BOOLEAN_VALUE_CASING: EIS picklist validator rejects ALL CAPS YES/NO.
-- Power Query: YES → Yes, NO → No (TagProperties query).
('BOOLEAN_VALUE_CASING',
 'common', NULL,
 'Boolean property values YES/NO must use Title Case: Yes/No — ALL CAPS variant is rejected by EIS picklist validator (Power Query: YES→Yes, NO→No)',
 'PROPERTY_VALUE matches_regex "^YES$|^NO$"', 'normalize_boolean_case',
 true, false, 'Info',
 'L1', 'Validity', 'dsl', 35),

-- NUMERIC_PSEUDO_NULL_VARIANT: 999999 (6 nines) is non-standard pseudo-null.
-- Standard is 999999999 (9 nines). Both must map to "NA".
('NUMERIC_PSEUDO_NULL_VARIANT',
 'common', NULL,
 'Numeric pseudo-NULL "999999" (6 nines) is a non-standard variant — must be normalized to "NA". Approved standard is 999999999 (9 nines) but 6-nine variant found in TagProperties source.',
 'PROPERTY_VALUE matches_regex "^999999$"', 'replace "999999" "NA"',
 true, false, 'Warning',
 'L2', 'Validity', 'dsl', 55),

-- UOM_LONGFORM_NORMALIZE: SI unit long-forms must use standard abbreviations.
-- Power Query: "hertz" → Hz, "volt" → V, "ampere" → A, "pascal" → Pa.
('UOM_LONGFORM_NORMALIZE',
 'common', NULL,
 'UoM long-form names must be replaced with standard abbreviations: ampere→A, volt→V, pascal→Pa, hertz→Hz, kilowatt→kW (Power Query UoM normalization)',
 'PROPERTY_VALUE_UOM matches_regex "(?i)^(ampere|volt|pascal|hertz|kilowatt)$"', 'normalize_uom_longform',
 true, false, 'Info',
 'L1', 'UoM', 'dsl', 45),

-- PROP_VALUE_UNSET: "UNSET" as an exact property value means the field was never set.
-- Power Query: Table.SelectRows(..., each Text.Upper([Property Value]) <> "UNSET").
-- NOT auto-fixed — rows with this value must be excluded from export, not silently blanked.
('PROP_VALUE_UNSET',
 'common', NULL,
 'PROPERTY_VALUE "UNSET" is a source-system placeholder — these rows must be excluded from EIS export (Power Query filter: Text.Upper([Property Value]) <> "UNSET"). No auto-fix: manual review required.',
 'PROPERTY_VALUE icontains "UNSET"', NULL,
 false, true, 'Warning',
 'L1', 'Validity', 'dsl', 28)

ON CONFLICT (rule_code) DO NOTHING;


-- ===========================================================================
-- BLOCK 7: INSERT aggregate metadata rule (P3 — no fix, is_builtin=false)
-- ---------------------------------------------------------------------------
-- check_type='aggregate' is not yet supported by the DSL executor.
-- Stored as metadata for future implementation / documentation.
-- ===========================================================================

INSERT INTO audit_core.export_validation_rule
    (rule_code, scope, object_field, description,
     rule_expression, fix_expression,
     is_builtin, is_blocking, severity,
     tier, category, check_type, sort_order)
VALUES
('SIGNAL_TAG_NO_DUPLICATES',
 'tag', 'TAG_NAME',
 'SIGNAL tags must be unique — duplicate SIGNAL tag_name values indicate a source extraction error (split/merge artifact). MTR PQ filter: not([COUNT] >= 2 and [TAG_CLASS_NAME] = "SIGNAL").',
 'aggregate: COUNT(tag_name) >= 2 WHERE tag_class_name = ''SIGNAL''', NULL,
 false, true, 'Critical',
 'L0', 'Uniqueness', 'aggregate', 5)

ON CONFLICT (rule_code) DO NOTHING;
