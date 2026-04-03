/*
Purpose: Insert 27 new validation rules derived from master_qa_register.md and
         master_qa_techRules.md gap analysis (validation_rules_gap_analysis.md §4).
         Rules use existing DSL operators — no engine changes required for dsl check_type.
         L3/L4 rules inserted as metadata for traceability; executor not yet implemented.
Changes: 2026-03-13 — Initial implementation per gap analysis recommendations.
Depends: migration_005_validation_rule_schema_v2.sql (tier, category, check_type columns)
*/

INSERT INTO audit_core.export_validation_rule
    (rule_code, scope, tier, category, check_type, description, source_ref,
     rule_expression, fix_expression, is_builtin, is_blocking, severity)
VALUES

-- ===========================================================================
-- L0 — Foundation (hard drops: mandatory identity fields)
-- ===========================================================================
(
    'TAG_NAME_NOT_NULL', 'tag', 'L0', 'Foundation', 'dsl',
    'TAG_NAME must be populated — missing tag name cannot be exported',
    'JDAW-PT-D-JA-7739-00003',
    'TAG_NAME is_null', NULL,
    true, true, 'Critical'
),
(
    'TAG_STATUS_NOT_NULL', 'tag', 'L0', 'Foundation', 'dsl',
    'TAG_STATUS must be populated — required for export filter and ACTION_STATUS derivation (L0.2)',
    'JDAW Final Information Handover Spec / techRules L0.2',
    'TAG_STATUS is_null', NULL,
    true, true, 'Critical'
),
(
    'TAG_CLASS_NOT_NULL', 'tag', 'L0', 'Foundation', 'dsl',
    'TAG_CLASS_NAME must be populated — class drives property validation and EIS schema mapping (L0.3)',
    'JDAW-PT-D-JA-7880-00001 / techRules L0.3',
    'TAG_CLASS_NAME is_null', NULL,
    true, true, 'Critical'
),

-- ===========================================================================
-- L1 — Syntax & Encoding
-- ===========================================================================
(
    'TAG_DESC_MAX_120', 'tag', 'L1', 'Limits', 'dsl',
    'TAG_DESCRIPTION must not exceed 120 characters — Aveva internal constraint (L1.3). 255 is DB limit; 120 is Aveva sync limit.',
    'JDAW-KVE-E-JA-6944-00001-003_A27 / techRules L1.3',
    'TAG_DESCRIPTION max_length 120', 'truncate 120',
    false, false, 'Warning'
),
(
    'TAG_STATUS_VALID_VALUES', 'tag', 'L1', 'Validity', 'dsl',
    'TAG_STATUS must be one of: Active, Void, Future, Hold — other values are rejected',
    'JDAW-PT-D-JA-7739-00003',
    'TAG_STATUS matches_regex "^(?!(Active|Void|Future|Hold)$).*"', NULL,
    false, true, 'Critical'
),
(
    'SAFETY_CRITICAL_VALID_VALUES', 'tag', 'L1', 'Validity', 'dsl',
    'SAFETY_CRITICAL_ITEM must be YES, NO, or NA only',
    'JDAW-PT-D-HX-7876-00002',
    'SAFETY_CRITICAL_ITEM matches_regex "^(?!(YES|NO|NA)$).*"', NULL,
    false, true, 'Warning'
),
(
    'SECE_SEMICOLON_DELIMITER', 'tag', 'L1', 'Syntax', 'dsl',
    'SAFETY_CRITICAL_ITEM_GROUP multi-values must use semicolon ";" separator — comma is incorrect (L1.9)',
    'techRules L1.9',
    'SAFETY_CRITICAL_ITEM_GROUP contains ","', 'replace "," ";"',
    true, false, 'Warning'
),
(
    'PIPE_TAG_NO_TRAILING_DASH', 'tag', 'L1', 'Syntax', 'dsl',
    'TAG_NAME must not end with "-" — pipeline tags must end with insulation code or -N for no insulation',
    'JDAW-KVE-E-JA-6944-00001-003',
    'TAG_NAME matches_regex "-$"', NULL,
    false, false, 'Warning'
),
(
    'DESC_NO_DOUBLE_SPACE', 'tag', 'L1', 'Syntax', 'dsl',
    'TAG_DESCRIPTION must not contain consecutive spaces — use single space',
    'JDAW-KVE-E-JA-6944-00001-003',
    'TAG_DESCRIPTION matches_regex "  "', 'replace "  " " "',
    true, false, 'Info'
),
(
    'DESC_NO_FROM_TO_SUFFIX', 'tag', 'L1', 'Syntax', 'dsl',
    'TAG_DESCRIPTION must not end with "From To" or "From/To" — remove this suffix for pipe tags where From/To will not be available',
    'JDAW-KVE-E-JA-6944-00001-003',
    'TAG_DESCRIPTION matches_regex "(?i)From[ /]?To\s*$"', NULL,
    false, false, 'Warning'
),
(
    'PO_CODE_NOT_VOID_SUFFIX', 'common', 'L1', 'Validity', 'dsl',
    'PO_CODE must not contain -VOID suffix — voided purchase orders cannot be referenced in export',
    'JDAW-KVE-E-JA-6944-00001-022',
    'PO_CODE icontains "-VOID"', NULL,
    false, true, 'Critical'
),

-- ===========================================================================
-- L2 — Completeness & Attribute Validation
-- ===========================================================================
(
    'TAG_DESC_NOT_NULL', 'tag', 'L2', 'Completeness', 'dsl',
    'TAG_DESCRIPTION must be populated — functional description required per handover spec',
    'JDAW Final Information Handover Spec',
    'TAG_DESCRIPTION is_null', NULL,
    false, true, 'Warning'
),
(
    'AREA_CODE_NOT_NULL', 'tag', 'L2', 'Completeness', 'dsl',
    'AREA_CODE must be defined — use NA for soft tags (SIGNAL, LOOP) if not applicable (L2.18)',
    'JDAW-PT-D-JA-7739-00003 / techRules L2.18',
    'AREA_CODE is_null', NULL,
    false, true, 'Warning'
),
(
    'PROCESS_UNIT_NOT_NULL', 'tag', 'L2', 'Completeness', 'dsl',
    'PROCESS_UNIT_CODE must be defined for ALL tags without exception (L2.3, L2.19)',
    'JDAW Final Information Handover Spec / techRules L2.3',
    'PROCESS_UNIT_CODE is_null', NULL,
    false, true, 'Warning'
),
(
    'SECE_GROUP_NOT_NULL', 'tag', 'L2', 'Completeness', 'dsl',
    'SAFETY_CRITICAL_ITEM_GROUP must be defined or set to NA — cannot be empty (L2.17)',
    'JDAW-PT-D-HX-7876-00002 / techRules L2.17',
    'SAFETY_CRITICAL_ITEM_GROUP is_null', NULL,
    false, false, 'Warning'
),
(
    'PSEUDO_NULL_NA_FORMAT', 'common', 'L2', 'Validity', 'dsl',
    'Pseudo-NULL for STRING must be exactly "NA" — variants like "N.A", "N.A.", "n/a", "na" are non-compliant',
    'JDAW-PT-D-JA-7739-00003 / master_qa_register Mandatory Null Values Handling',
    '* matches_regex "^[Nn][.][Aa][.]{0,1}$|^n/a$|^na$"', 'replace "N.A." "NA"',
    true, false, 'Warning'
),
(
    'PSEUDO_NULL_DATE_FORMAT', 'common', 'L2', 'Validity', 'dsl',
    'Date pseudo-NULL must be exactly "01.01.1990" — ISO format 1990-01-01 or slash variant are non-compliant',
    'JDAW-PT-D-JA-7739-00003',
    '* matches_regex "^1990-01-01|^01/01/1990"', NULL,
    false, false, 'Warning'
),
(
    'PROP_VALUE_ZERO_NOT_ALLOWED', 'common', 'L2', 'Validity', 'dsl',
    'PROPERTY_VALUE of exactly "0" is not allowed — use "TBC" for unknown values (L2.7)',
    'techRules L2.7 / JDAW-KVE-E-JA-6944-00001-010',
    'PROPERTY_VALUE matches_regex "^0$"', NULL,
    false, false, 'Warning'
),
(
    'EQUIP_MANUFACTURER_NOT_NULL', 'equipment', 'L2', 'Completeness', 'dsl',
    'MANUFACTURER_COMPANY_NAME mandatory for physical equipment — NA only for soft tags (L2.4)',
    'techRules L2.4 / JDAW Final Information Handover Spec',
    'MANUFACTURER_COMPANY_NAME is_null', NULL,
    false, true, 'Warning'
),
(
    'EQUIP_MODEL_NOT_NULL', 'equipment', 'L2', 'Completeness', 'dsl',
    'MODEL_PART_NAME mandatory for all physical equipment — exception only for soft tags',
    'JDAW-KVE-E-JA-6944-00001-004',
    'MODEL_PART_NAME is_null', NULL,
    false, true, 'Warning'
),

-- ===========================================================================
-- L3 — Topology & Cross-Reference
-- check_type != 'dsl' — rules stored for traceability; require custom executor.
-- rule_expression is descriptive text — NOT parsed by DSL engine.
-- is_builtin=false ensures these are skipped during export apply_builtin_fixes().
-- ===========================================================================
(
    'PARENT_TAG_STATUS_VALID', 'tag', 'L3', 'Topology', 'cross_table',
    'Parent tag referenced in PARENT_TAG_NAME must exist with Active status — orphan/inactive parent links not accepted (L3.2)',
    'JDAW-KVE-E-JA-6944-00001-003_A31 / techRules L3.2',
    'cross_table: parent_tag_id.object_status NOT IN (''Active'')', NULL,
    false, true, 'Critical'
),
(
    'CYCLIC_PARENT_REFERENCE', 'tag', 'L3', 'Topology', 'graph',
    'No circular parent references allowed — Tag A cannot be ancestor of itself (L3.3)',
    'techRules L3.3',
    'graph: MATCH path=(t:Tag)-[:HAS_PARENT*]->(t) RETURN t', NULL,
    false, true, 'Critical'
),
(
    'SINGLE_PARENT_RULE', 'tag', 'L3', 'Topology', 'aggregate',
    'A tag can only have ONE parent — multiple parent mappings are forbidden (L3.4)',
    'techRules L3.4',
    'aggregate: COUNT(parent_tag_id) > 1 GROUP BY tag_id', NULL,
    false, true, 'Error'
),
(
    'TAG_MIN_DOC_LINK', 'tag', 'L3', 'Referential', 'aggregate',
    'Every active non-loop tag must have at least one valid Doc-Tag link (L3.8)',
    'JDAW-KVE-E-JA-6944-00001-016 / techRules L3.8',
    'aggregate: COUNT(doc_links) = 0 WHERE tag_class NOT IN (''INSTRUMENT LOOP'')', NULL,
    false, false, 'Warning'
),
(
    'IN_SERVICE_STARTUP_DATE', 'tag', 'L3', 'CrossField', 'cross_field',
    'If TAG_STATUS is In Service, STARTUP_DATE must not be pseudo-NULL (01.01.1990) or empty (L2.11)',
    'techRules L2.11',
    'cross_field: TAG_STATUS = ''In Service'' AND (STARTUP_DATE is_null OR STARTUP_DATE = ''01.01.1990'')', NULL,
    false, false, 'Warning'
),
(
    'DATE_SEQUENCE_VALID', 'equipment', 'L3', 'CrossField', 'cross_field',
    'PURCHASE_DATE must be <= INSTALLATION_DATE when both are populated (L2.12)',
    'techRules L2.12',
    'cross_field: PURCHASE_DATE > INSTALLATION_DATE WHERE both not null and not pseudo-null', NULL,
    false, false, 'Warning'
),

-- ===========================================================================
-- L4 — Semantics (ML-assisted; metadata-only — Ollama executor not yet integrated)
-- ===========================================================================
(
    'DESC_FUNCTIONAL_NOT_CLASS_COPY', 'tag', 'L4', 'Semantics', 'metadata',
    'TAG_DESCRIPTION must describe function/service — not simply duplicate class name (e.g. "Centrifugal Pump" is poor; "Hot Oil Circulation Pump" is good) (L4.1)',
    'techRules L4.1 / JDAW-KVE-E-JA-6944-00001-003',
    'ml: description_is_class_name_duplicate', NULL,
    false, false, 'Warning'
),
(
    'DESC_FUTURE_TAG_EXCEPTION', 'tag', 'L4', 'Semantics', 'metadata',
    'If TAG_STATUS is Future, description "TO BE DEFINED" or "FUTURE" is acceptable — bypass functional description check (L4.2)',
    'techRules L4.2 / JDAW-KVE-E-JA-6944-00001-003_A29',
    'ml: bypass_if_tag_status_future', NULL,
    false, false, 'Info'
)

ON CONFLICT (rule_code) DO NOTHING;
