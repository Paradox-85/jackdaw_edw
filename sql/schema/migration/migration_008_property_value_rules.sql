/*
Migration: 006 — Validation rules for property value exports (seq 303 & seq 301).
Date:      2026-03-13
Scope:     Adds scope='tag_property' and scope='equipment_property' rules.
           These rules are evaluated via the shared DSL engine in export_validation.py.
Depends:   migration_005_validation_rule_schema_v2.sql (tier, category, check_type columns).
*/

-- ---------------------------------------------------------------------------
-- Seq 303 — Tag Property Values (scope: 'tag_property')
-- ---------------------------------------------------------------------------

INSERT INTO audit_core.export_validation_rule
    (rule_code, scope, object_field, description,
     rule_expression, fix_expression,
     is_builtin, is_blocking, severity,
     tier, category, check_type, sort_order)
VALUES

-- L0: Identity — mandatory fields that make a row meaningful
('PROP_TAG_NAME_NOT_NULL',
 'tag_property', 'TAG_NAME',
 'TAG_NAME must be present in every property value row',
 'TAG_NAME is_null', NULL,
 true, true, 'Critical',
 'L0', 'Foundation', 'dsl', 10),

('PROP_CODE_NOT_NULL',
 'tag_property', 'PROPERTY_CODE',
 'PROPERTY_CODE must be present in every property value row',
 'PROPERTY_CODE is_null', NULL,
 true, true, 'Critical',
 'L0', 'Foundation', 'dsl', 20),

-- L1: Syntax — encoding and value format correctness
('PROP_NAN_STRINGS',
 'tag_property', 'PROPERTY_VALUE',
 'PROPERTY_VALUE must not contain bare nan/NaN strings (Pandas artefact)',
 'PROPERTY_VALUE matches_regex "(?i)^nan$"', 'replace_nan',
 true, false, 'Warning',
 'L1', 'Encoding', 'dsl', 30),

('PROP_ENCODING_ARTEFACTS',
 'tag_property', NULL,
 'Property value columns must not contain UTF-8 mojibake or Win-1252 artefacts',
 '* has_encoding_artefacts', 'encoding_repair',
 true, false, 'Warning',
 'L1', 'Encoding', 'dsl', 40),

-- L2: Completeness — expected data quality for export
('PROP_VALUE_NOT_NULL',
 'tag_property', 'PROPERTY_VALUE',
 'PROPERTY_VALUE should be populated (empty value reduces export quality)',
 'PROPERTY_VALUE is_null', NULL,
 false, true, 'Warning',
 'L2', 'Completeness', 'dsl', 50)

ON CONFLICT (rule_code) DO NOTHING;


-- ---------------------------------------------------------------------------
-- Seq 301 — Equipment Property Values (scope: 'equipment_property')
-- ---------------------------------------------------------------------------

INSERT INTO audit_core.export_validation_rule
    (rule_code, scope, object_field, description,
     rule_expression, fix_expression,
     is_builtin, is_blocking, severity,
     tier, category, check_type, sort_order)
VALUES

-- L0: Identity — mandatory fields
('PROP_EQUIP_TAG_NAME_NOT_NULL',
 'equipment_property', 'TAG_NAME',
 'TAG_NAME must be present in every equipment property value row',
 'TAG_NAME is_null', NULL,
 true, true, 'Critical',
 'L0', 'Foundation', 'dsl', 10),

('PROP_EQUIP_CODE_NOT_NULL',
 'equipment_property', 'PROPERTY_CODE',
 'PROPERTY_CODE must be present in every equipment property value row',
 'PROPERTY_CODE is_null', NULL,
 true, true, 'Critical',
 'L0', 'Foundation', 'dsl', 20),

-- L1: Syntax — encoding and value format correctness
('PROP_EQUIP_NAN_STRINGS',
 'equipment_property', 'PROPERTY_VALUE',
 'PROPERTY_VALUE must not contain bare nan/NaN strings (Pandas artefact)',
 'PROPERTY_VALUE matches_regex "(?i)^nan$"', 'replace_nan',
 true, false, 'Warning',
 'L1', 'Encoding', 'dsl', 30),

('PROP_EQUIP_ENCODING_ARTEFACTS',
 'equipment_property', NULL,
 'Equipment property value columns must not contain UTF-8 mojibake or Win-1252 artefacts',
 '* has_encoding_artefacts', 'encoding_repair',
 true, false, 'Warning',
 'L1', 'Encoding', 'dsl', 40),

-- L2: Completeness
('PROP_EQUIP_VALUE_NOT_NULL',
 'equipment_property', 'PROPERTY_VALUE',
 'PROPERTY_VALUE should be populated (empty value reduces export quality)',
 'PROPERTY_VALUE is_null', NULL,
 false, true, 'Warning',
 'L2', 'Completeness', 'dsl', 50)

ON CONFLICT (rule_code) DO NOTHING;
