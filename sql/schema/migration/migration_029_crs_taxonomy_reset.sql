-- migration_029_crs_taxonomy_reset.sql
-- Resets CRS taxonomy to unified GEN-XXX system (35 categories).
-- Drops columns: source, confidence, usage_count.
-- Renames: category → category_code.
-- Rebuilds: v_template_queries view.
-- Generated: 2026-04-08

BEGIN;

-- §1: Schema alterations on audit_core.crs_comment_template

ALTER TABLE audit_core.crs_comment_template
    DROP CONSTRAINT IF EXISTS chk_crs_template_source,
    DROP CONSTRAINT IF EXISTS chk_crs_template_confidence;

ALTER TABLE audit_core.crs_comment_template
    DROP COLUMN IF EXISTS source,
    DROP COLUMN IF EXISTS confidence,
    DROP COLUMN IF EXISTS usage_count;

-- Idempotent rename: category → category_code
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'audit_core'
          AND table_name   = 'crs_comment_template'
          AND column_name  = 'category'
    ) THEN
        ALTER TABLE audit_core.crs_comment_template
            RENAME COLUMN category TO category_code;
    END IF;
END$$;

-- §2: Rebuild view after column rename
DROP VIEW IF EXISTS audit_core.v_template_queries;

CREATE OR REPLACE VIEW audit_core.v_template_queries AS
SELECT
    ct.id                   AS template_id,
    ct.category_code        AS template_category,
    ct.check_type,
    ct.template_text,
    vq.id                   AS query_id,
    vq.query_code,
    vq.query_name,
    vq.query_type,
    vq.evaluation_strategy,
    vq.has_parameters,
    vq.parameter_names,
    vq.sql_query,
    vq.response_template,
    tqm.priority
FROM audit_core.crs_template_query_map tqm
JOIN audit_core.crs_comment_template   ct ON ct.id = tqm.template_id
JOIN audit_core.crs_validation_query   vq ON vq.id = tqm.query_id
WHERE tqm.object_status = 'Active'
  AND ct.object_status  = 'Active'
  AND vq.is_active      = true
  AND vq.query_type     = 'GROUP';

COMMENT ON VIEW "audit_core"."v_template_queries" IS
    'GROUP queries per template. Used by batch validation flow: '
    'GROUP BY category → fetch all tag_names → ONE SQL call via ANY(:tag_names). '
    'INDIVIDUAL queries are looked up directly from crs_comment_validation.';

-- §3: Clear taxonomy tables
TRUNCATE audit_core.crs_template_query_map CASCADE;
TRUNCATE audit_core.crs_validation_query   CASCADE;
TRUNCATE audit_core.crs_comment_template   CASCADE;

-- §4: Seed 35 GEN-XXX categories
INSERT INTO audit_core.crs_comment_template
    (category_code, template_text, short_template_text, template_hash, check_type, severity, object_status)
VALUES

('GEN-001',
 'NULL or empty field. Mandatory/recommended fields: tag description, class, area code, PO date, serial number, process unit, safety_critical_item, designed_by_company.',
 'ATTR_VALUE_BLANK',
 md5('NULL or empty field. Mandatory/recommended fields: tag description, class, area code, PO date, serial number, process unit, safety_critical_item, designed_by_company.'),
 'Completeness', 'Critical', 'Active'),

('GEN-002',
 'Pseudo-null placeholder: NA, N/A, TBC, TBA, NONE, zero (0). Covers serial number=NA, area code=NA, process unit=NA, UOM=TBC on property fields.',
 'ATTR_VALUE_PLACEHOLDER',
 md5('Pseudo-null placeholder: NA, N/A, TBC, TBA, NONE, zero (0). Covers serial number=NA, area code=NA, process unit=NA, UOM=TBC on property fields.'),
 'Completeness', 'Warning', 'Active'),

('GEN-003',
 'Reference not submitted — raw value AND resolved FK both NULL. Parent tag missing for Valve/Pipe, area code absent, PO code not provided on physical tag.',
 'REF_NOT_SUBMITTED',
 md5('Reference not submitted — raw value AND resolved FK both NULL. Parent tag missing for Valve/Pipe, area code absent, PO code not provided on physical tag.'),
 'Completeness', 'Warning', 'Active'),

('GEN-004',
 'Reference code has wrong syntax/format — fails regex, not looked up in master. Covers site code format, doc number prefix mismatch, plant code pattern violation.',
 'REF_FORMAT_INVALID',
 md5('Reference code has wrong syntax/format — fails regex, not looked up in master. Covers site code format, doc number prefix mismatch, plant code pattern violation.'),
 'Referential', 'Warning', 'Active'),

('GEN-005',
 'Raw reference submitted but FK unresolved — object not in master. Parent tag not in MTR, PO not in PO register, doc not in DocMaster/Assai, company not in register.',
 'REF_NOT_RESOLVED',
 md5('Raw reference submitted but FK unresolved — object not in master. Parent tag not in MTR, PO not in PO register, doc not in DocMaster/Assai, company not in register.'),
 'Referential', 'Critical', 'Active'),

('GEN-006',
 'Duplicate record by key fields: tag name, doc number, PO code, property key. Applies to MTR, DocMaster, PO register, tag_property, equipment_property, physical connections.',
 'DUPLICATE_RECORD',
 md5('Duplicate record by key fields: tag name, doc number, PO code, property key. Applies to MTR, DocMaster, PO register, tag_property, equipment_property, physical connections.'),
 'Completeness', 'Critical', 'Active'),

('GEN-007',
 'Multiple comma/semicolon-separated values in single field. Typical: AREA_CODE=''A100,A200''. Split or select correct single value.',
 'ATTR_MULTI_VALUE',
 md5('Multiple comma/semicolon-separated values in single field. Typical: AREA_CODE=''A100,A200''. Split or select correct single value.'),
 'Completeness', 'Warning', 'Active'),

('GEN-008',
 'Spelling errors, double spaces, prohibited characters in text: tag/equipment description, area name, company name. Includes leading/trailing dash artefacts.',
 'ATTR_TEXT_FORMAT_ERROR',
 md5('Spelling errors, double spaces, prohibited characters in text: tag/equipment description, area name, company name. Includes leading/trailing dash artefacts.'),
 'Completeness', 'Warning', 'Active'),

('GEN-010',
 'Text value below minimum length. Tag/equipment description under 20 chars. Signal: ''too short'', ''not functional'', ''please revise''.',
 'ATTR_TEXT_TOO_SHORT',
 md5('Text value below minimum length. Tag/equipment description under 20 chars. Signal: ''too short'', ''not functional'', ''please revise''.'),
 'Completeness', 'Warning', 'Active'),

('GEN-011',
 'Text value exceeds max length. Tag/equipment description must be ≤255 chars. Typical: ''Tag Description is exceeding 255 characters''.',
 'ATTR_TEXT_TOO_LONG',
 md5('Text value exceeds max length. Tag/equipment description must be ≤255 chars. Typical: ''Tag Description is exceeding 255 characters''.'),
 'Completeness', 'Warning', 'Active'),

('GEN-012',
 'Value present but fails regex. Description starts/ends with dash, trailing '','',NA'', non-numeric in numeric field, cable CSA unexpected chars, PO description special chars.',
 'ATTR_VALUE_PATTERN_FAIL',
 md5('Value present but fails regex. Description starts/ends with dash, trailing '','',NA'', non-numeric in numeric field, cable CSA unexpected chars, PO description special chars.'),
 'Completeness', 'Warning', 'Active'),

('GEN-014',
 'Referenced object found but has invalid status: VOID, NYI (Not Yet Issued), CAN, INACTIVE. Doc in NYI in Assai/DMS, void PO, TAG_STATUS outside EIS vocabulary.',
 'REF_STATUS_INVALID',
 md5('Referenced object found but has invalid status: VOID, NYI (Not Yet Issued), CAN, INACTIVE. Doc in NYI in Assai/DMS, void PO, TAG_STATUS outside EIS vocabulary.'),
 'Referential', 'Warning', 'Active'),

('GEN-015',
 'UOM error on property. MISSING: numeric property has no UOM. INVALID: UOM not in ontology. UNEXPECTED: value is NA/TBC but UOM populated. Applies to tag_property, equipment_property.',
 'UOM_ERROR',
 md5('UOM error on property. MISSING: numeric property has no UOM. INVALID: UOM not in ontology. UNEXPECTED: value is NA/TBC but UOM populated. Applies to tag_property, equipment_property.'),
 'Completeness', 'Warning', 'Active'),

('GEN-017',
 'Object class not found in ISM/RDL (Reference Data Library). class_id NULL when class_raw provided. Applies to tag class and equipment class. Signal: ''not available in Jackdaw ISM''.',
 'CLASS_NOT_IN_ISM',
 md5('Object class not found in ISM/RDL (Reference Data Library). class_id NULL when class_raw provided. Applies to tag class and equipment class. Signal: ''not available in Jackdaw ISM''.'),
 'Referential', 'Critical', 'Active'),

('GEN-018',
 'Abstract/parent class assigned to physical object. is_abstract=TRUE in ontology. Use most specific ISM leaf class. Consequence: no class_property → property_value unvalidatable.',
 'CLASS_IS_ABSTRACT',
 md5('Abstract/parent class assigned to physical object. is_abstract=TRUE in ontology. Use most specific ISM leaf class. Consequence: no class_property → property_value unvalidatable.'),
 'Referential', 'Warning', 'Active'),

('GEN-019',
 'Class name and description semantically inconsistent — LLM check. Tag class vs tag description mismatch, equipment class vs description mismatch. Both values exist but contradict.',
 'CLASS_DESC_MISMATCH',
 md5('Class name and description semantically inconsistent — LLM check. Tag class vs tag description mismatch, equipment class vs description mismatch. Both values exist but contradict.'),
 'Semantic', 'Warning', 'Active'),

('GEN-020',
 'Name violates TNC (Tagging/Naming Convention) per Jackdaw Spec JDAW-PT-D-OA-7880. Comma instead of point, non-standard dash, ends with dash, tag prefix vs plant code mismatch.',
 'TNC_VIOLATION',
 md5('Name violates TNC (Tagging/Naming Convention) per Jackdaw Spec JDAW-PT-D-OA-7880. Comma instead of point, non-standard dash, ends with dash, tag prefix vs plant code mismatch.'),
 'Naming', 'Critical', 'Active'),

('GEN-021',
 'TNC prefix does not match expected prefix for assigned class. Control panel ''CP'' TNC check. TNC inconsistent with similar tags of same class. Requires tnc_class_map lookup.',
 'TNC_PREFIX_MISMATCH',
 md5('TNC prefix does not match expected prefix for assigned class. Control panel ''CP'' TNC check. TNC inconsistent with similar tags of same class. Requires tnc_class_map lookup.'),
 'Naming', 'Warning', 'Active'),

('GEN-022',
 'Circular parent-child hierarchy — recursive CTE detects cycle. Tag A→parent B→parent A. Depth limit 10. Signal: ''tag hierarchy must be acyclic''.',
 'HIERARCHY_CIRCULAR',
 md5('Circular parent-child hierarchy — recursive CTE detects cycle. Tag A→parent B→parent A. Depth limit 10. Signal: ''tag hierarchy must be acyclic''.'),
 'Referential', 'Critical', 'Active'),

('GEN-023',
 'Object references itself as own parent tag. parent_tag_id = id. Applies to tag and equipment. Signal: ''self-reference not permitted'', ''equipment is own parent tag''.',
 'HIERARCHY_SELF_REF',
 md5('Object references itself as own parent tag. parent_tag_id = id. Applies to tag and equipment. Signal: ''self-reference not permitted'', ''equipment is own parent tag''.'),
 'Referential', 'Critical', 'Active'),

('GEN-024',
 'Parent has invalid class for child type. Pipe parent is also pipe (allowed only for small bore/nozzle). Check parent class against allowed rules per child class.',
 'HIERARCHY_PARENT_CLASS_INVALID',
 md5('Parent has invalid class for child type. Pipe parent is also pipe (allowed only for small bore/nozzle). Check parent class against allowed rules per child class.'),
 'Referential', 'Warning', 'Active'),

('GEN-025',
 'SAFETY_CRITICAL_ITEM invalid or blank — must be YES/NO/Y/N per EIS. Signal: ''missing yes or no for safety critical item'', ''Safety Critical Item field is blank''.',
 'SCI_VALUE_INVALID',
 md5('SAFETY_CRITICAL_ITEM invalid or blank — must be YES/NO/Y/N per EIS. Signal: ''missing yes or no for safety critical item'', ''Safety Critical Item field is blank''.'),
 'Completeness', 'Critical', 'Active'),

('GEN-026',
 'SAFETY_CRITICAL_ITEM=YES but SAFETY_CRITICAL_ITEM_REASON_AWARDED is NULL. Mandatory per EIS. Signal: ''SAFETY_CRITICAL_ITEM_REASON_AWARDED is not provided for safety critical items''.',
 'SCI_REASON_MISSING',
 md5('SAFETY_CRITICAL_ITEM=YES but SAFETY_CRITICAL_ITEM_REASON_AWARDED is NULL. Mandatory per EIS. Signal: ''SAFETY_CRITICAL_ITEM_REASON_AWARDED is not provided for safety critical items''.'),
 'Completeness', 'Critical', 'Active'),

('GEN-027',
 'Safety critical tag has no SECE (Safety Environmentally Critical Element) link in mapping.tag_sece. Signal: ''safety critical items not linked to performance standard (SECE mapping missing)''.',
 'SECE_MAPPING_MISSING',
 md5('Safety critical tag has no SECE (Safety Environmentally Critical Element) link in mapping.tag_sece. Signal: ''safety critical items not linked to performance standard (SECE mapping missing)''.'),
 'Completeness', 'Critical', 'Active'),

('GEN-028',
 'Tag assigned to >1 SECE group. Each tag must have exactly one performance standard. Signal: ''multiple SECE item groups assigned — each tag should have only one performance standard''.',
 'SECE_MULTIPLE_GROUPS',
 md5('Tag assigned to >1 SECE group. Each tag must have exactly one performance standard. Signal: ''multiple SECE item groups assigned — each tag should have only one performance standard''.'),
 'Referential', 'Warning', 'Active'),

('GEN-029',
 'Properties mismatch class spec from ISM/ontology. MISSING: mandatory props absent. EXTRA: props outside class scope. BOTH. Applies to tag_property and equipment_property.',
 'PROPERTY_CLASS_MISMATCH',
 md5('Properties mismatch class spec from ISM/ontology. MISSING: mandatory props absent. EXTRA: props outside class scope. BOTH. Applies to tag_property and equipment_property.'),
 'Completeness', 'Warning', 'Active'),

('GEN-030',
 'From-tag equals to-tag in physical connection — self-loop. from_tag_raw = to_tag_raw. Signal: ''From-Tag and To-Tag are the same — self-connection not permitted''.',
 'CONNECTION_SELF_LOOP',
 md5('From-tag equals to-tag in physical connection — self-loop. from_tag_raw = to_tag_raw. Signal: ''From-Tag and To-Tag are the same — self-connection not permitted''.'),
 'Referential', 'Critical', 'Active'),

('GEN-031',
 'PRODUCTION_CRITICAL_ITEM invalid or NULL. Must be YES/NO/Y/N. Signal: ''Production Critical Item field is blank'', ''must be populated with valid value from approved list''.',
 'PCI_VALUE_INVALID',
 md5('PRODUCTION_CRITICAL_ITEM invalid or NULL. Must be YES/NO/Y/N. Signal: ''Production Critical Item field is blank'', ''must be populated with valid value from approved list''.'),
 'Completeness', 'Warning', 'Active'),

('GEN-032',
 'Register has fewer records than minimum expected. Physical connections (too few pipe/cable), tag_property (too few rows). Signal: ''incomplete — resubmit complete register''.',
 'REGISTER_INCOMPLETE',
 md5('Register has fewer records than minimum expected. Physical connections (too few pipe/cable), tag_property (too few rows). Signal: ''incomplete — resubmit complete register''.'),
 'Completeness', 'Warning', 'Active'),

('GEN-033',
 'File header structure does not match approved CIS template. Wrong column names, missing PLANT_CODE column, wrong CSV template for Doc-PU or tag connections. Import-time check.',
 'TEMPLATE_STRUCTURE_INVALID',
 md5('File header structure does not match approved CIS template. Wrong column names, missing PLANT_CODE column, wrong CSV template for Doc-PU or tag connections. Import-time check.'),
 'Completeness', 'Critical', 'Active'),

('GEN-034',
 'Description exists but quality insufficient — LLM check. Only class name used, no from-to for pipe, tag number incomplete, vague/generic functional description.',
 'DESC_QUALITY_LOW',
 md5('Description exists but quality insufficient — LLM check. Only class name used, no from-to for pipe, tag number incomplete, vague/generic functional description.'),
 'Semantic', 'Warning', 'Active'),

('GEN-035',
 'Administrative/advisory/process comment — no data error, always DEFERRED. Data delivery tracking, ''better class available'', previous revision outstanding, P&ID/loop diagram requests.',
 'ADVISORY_DEFERRED',
 md5('Administrative/advisory/process comment — no data error, always DEFERRED. Data delivery tracking, ''better class available'', previous revision outstanding, P&ID/loop diagram requests.'),
 'Advisory', 'Info', 'Active'),

('GEN-036',
 'Object has zero document links in mapping.tag_document / Doc-Equipment. Every physical tag/equipment needs ≥1 active doc reference. Signal: ''do not have document references in Doc-Tag register''.',
 'DOC_LINK_MISSING',
 md5('Object has zero document links in mapping.tag_document / Doc-Equipment. Every physical tag/equipment needs ≥1 active doc reference. Signal: ''do not have document references in Doc-Tag register''.'),
 'Completeness', 'Warning', 'Active'),

('GEN-037',
 'Class assigned but zero property rows in property register. Non-abstract class with no tag_property or equipment_property records. Signal: ''do not have any property in Tag Property CSV''.',
 'PROPERTY_ROWS_MISSING',
 md5('Class assigned but zero property rows in property register. Non-abstract class with no tag_property or equipment_property records. Signal: ''do not have any property in Tag Property CSV''.'),
 'Completeness', 'Warning', 'Active'),

('GEN-038',
 'Property code/name does not match ontology. Code found but name differs, or non-standard prefix. Signal: ''non-standard prefix — confirm whether approved and provide TQ reference''.',
 'PROPERTY_CODE_MISMATCH',
 md5('Property code/name does not match ontology. Code found but name differs, or non-standard prefix. Signal: ''non-standard prefix — confirm whether approved and provide TQ reference''.'),
 'Referential', 'Warning', 'Active');

-- §5: Post-migration verification
SELECT 'crs_template_query_map' AS table_name, COUNT(*) AS row_count
  FROM audit_core.crs_template_query_map
UNION ALL
SELECT 'crs_validation_query',  COUNT(*)
  FROM audit_core.crs_validation_query
UNION ALL
SELECT 'crs_comment_template',  COUNT(*)
  FROM audit_core.crs_comment_template;
-- Expected: 0 / 0 / 35

COMMIT;
