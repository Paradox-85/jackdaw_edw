/*
Purpose: Backfill tier, category, check_type, source_ref on all 42 existing validation rules
         seeded by migration_003. Enables tier-based filtering and executor routing.
Changes: 2026-03-13 — Initial backfill per validation_rules_gap_analysis.md
Depends: migration_005_validation_rule_schema_v2.sql (new columns must exist)
*/

-- ---------------------------------------------------------------------------
-- L0 — Foundation
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L0', category = 'Foundation', check_type = 'metadata',
    source_ref = 'JDAW-PT-D-JA-7739-00003'
WHERE rule_code = 'TAG_NAME_CHANGED';

-- ---------------------------------------------------------------------------
-- L1 — Encoding
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L1', category = 'Encoding', check_type = 'dsl',
    source_ref = 'JDAW-KVE-E-JA-6944-00001-003'
WHERE rule_code IN ('NO_COMMA_IN_VALUES', 'NO_NAN_STRINGS', 'NO_INVALID_CHARS', 'ENCODING_ARTEFACTS');

-- ---------------------------------------------------------------------------
-- L1 — Syntax
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L1', category = 'Syntax', check_type = 'dsl',
    source_ref = 'JDAW-PT-D-JA-7739-00003'
WHERE rule_code = 'DECIMAL_DOT_SEPARATOR';

-- ---------------------------------------------------------------------------
-- L1 — Limits
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L1', category = 'Limits', check_type = 'dsl',
    source_ref = 'JDAW-KVE-E-JA-6944-00001-003'
WHERE rule_code IN ('COMPANY_NAME_MAX_30', 'TAG_DESC_MAX_255');

-- ---------------------------------------------------------------------------
-- L1 — Validity (DSL-evaluable cross-file checks that happen to be simple patterns)
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L1', category = 'Validity', check_type = 'dsl',
    source_ref = 'JDAW-KVE-E-JA-6944-00001-022'
WHERE rule_code = 'PO_CODE_NOT_VOID';

-- ---------------------------------------------------------------------------
-- L2 — Referential (FK resolution — all DSL, single-DataFrame evaluable)
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L2', category = 'Referential', check_type = 'dsl',
    source_ref = 'JDAW-PT-D-JA-7739-00003'
WHERE rule_code IN (
    'AREA_FK_RESOLVED',
    'CLASS_FK_RESOLVED',
    'PROCESS_UNIT_FK_RESOLVED',
    'PLANT_FK_RESOLVED',
    'DESIGN_CO_FK_RESOLVED',
    'PO_FK_RESOLVED',
    'ARTICLE_FK_RESOLVED',
    'PARENT_TAG_FK_RESOLVED',
    'DISCIPLINE_FK_RESOLVED'
);

UPDATE audit_core.export_validation_rule SET
    tier = 'L2', category = 'Referential', check_type = 'dsl',
    source_ref = 'JDAW-KVE-E-JA-6944-00001-004'
WHERE rule_code IN (
    'MODEL_PART_FK_RESOLVED',
    'MANUFACTURER_FK_RESOLVED',
    'VENDOR_FK_RESOLVED'
);

-- ---------------------------------------------------------------------------
-- L2 — Completeness
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L2', category = 'Completeness', check_type = 'dsl',
    source_ref = 'JDAW Final Information Handover Spec'
WHERE rule_code IN ('EQUIP_NO_NOT_NULL', 'SERIAL_NO_NOT_EMPTY', 'PROCESS_UNIT_MANDATORY', 'AREA_CODE_EXPECTED');

-- Descriptive-only rule — not DSL-evaluable as-is
UPDATE audit_core.export_validation_rule SET
    tier = 'L2', category = 'Completeness', check_type = 'metadata',
    source_ref = 'JDAW-PT-D-JA-7739-00003'
WHERE rule_code = 'MANDATORY_NOT_EMPTY';

-- ---------------------------------------------------------------------------
-- L2 — Validity
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L2', category = 'Validity', check_type = 'dsl',
    source_ref = 'techRules L2.7'
WHERE rule_code IN ('NO_INFORMATIONAL_ZERO', 'HEATER_WATTAGE_POSITIVE', 'SERIAL_NO_NO_NA_FOR_BULK');

-- ---------------------------------------------------------------------------
-- L2 — UoM
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L2', category = 'UoM', check_type = 'dsl',
    source_ref = 'techRules L1.10'
WHERE rule_code IN (
    'UOM_BLANK_WHEN_VALUE_NA',
    'UOM_BLANK_WHEN_VALUE_TBC',
    'AREA_UNIT_AVEVA_FORMAT',
    'VALUE_UOM_COMBINED_IN_CELL',
    'COUNT_PROPERTY_UOM_EMPTY'
);

-- ---------------------------------------------------------------------------
-- L3 — Referential (cross-file, require custom executor)
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L3', category = 'Referential', check_type = 'cross_table',
    source_ref = 'JDAW-KVE-E-JA-6944-00001-016'
WHERE rule_code IN (
    'TAG_ACTIVE_IN_MASTER',
    'DOC_EXISTS_IN_MDR',
    'PO_CODE_EXISTS_IN_MASTER',
    'CLASS_MATCHES_RDL',
    'NO_ABSTRACT_CLASS'
);

-- ---------------------------------------------------------------------------
-- L3 — Topology
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L3', category = 'Topology', check_type = 'aggregate',
    source_ref = 'techRules L3.8'
WHERE rule_code IN ('TAG_MIN_ONE_DOCUMENT', 'PHYSICAL_CONNECTION_NO_DUPLICATE');

UPDATE audit_core.export_validation_rule SET
    tier = 'L3', category = 'Topology', check_type = 'cross_table',
    source_ref = 'JDAW-KVE-E-JA-6944-00001-003'
WHERE rule_code IN ('VOID_DELETED_EXCLUDED_FROM_XREF', 'PHYSICAL_CONNECTION_TAGS_VALID');

-- ---------------------------------------------------------------------------
-- L3 — CrossField
-- ---------------------------------------------------------------------------
UPDATE audit_core.export_validation_rule SET
    tier = 'L3', category = 'CrossField', check_type = 'cross_table',
    source_ref = 'JDAW-KVE-E-JA-6944-00001-004'
WHERE rule_code = 'EQUIP_TAG_PREFIX_MATCH';

-- ---------------------------------------------------------------------------
-- Verify: no rule_code left with NULL tier (except intentional exceptions)
-- Run after applying this migration:
--   SELECT rule_code FROM audit_core.export_validation_rule WHERE tier IS NULL;
-- Expected: 0 rows
-- ---------------------------------------------------------------------------
