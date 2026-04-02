-- =============================================================================
-- Migration 019: CRS Comment Templates — Master Extended Seed
-- =============================================================================
-- Sources merged:
--   1. migration_018_crs_categories_seed.sql  (original seed)
--   2. crs_comment_templates_extended.sql     (Claude Sonnet, 149 rows)
--   3. crs_comment_by_domain.xlsx             (1071 real CRS comments)
-- Merge: union deduplicated on category_code, numerics stripped.
-- Idempotent: ON CONFLICT (category_code) DO UPDATE — safe to re-run.
-- Total: 179 templates | 12 domains
-- Severity: Critical=68 | Warning=104 | Info=7
-- =============================================================================

INSERT INTO audit_core.crs_comment_template
    (category_code, domain, template_text, short_template_text, severity)
VALUES


-- =========================================================================
-- DOMAIN: AREA
-- =========================================================================
-- Area code duplicated in cell
('AREA-001', 'area', 'AREA_CODE is duplicated within the same cell — check and correct.', 'Area code duplicated in cell', 'Warning')
-- Area name spelling error
('AREA-002', 'area', 'AREA_NAME contains spelling errors — check and correct.', 'Area name spelling error', 'Warning')
-- Area code is literal NA
('AREA-003', 'area', 'Area code is set to "NA" — this is not a valid area code, check and correct.', 'Area code is literal NA', 'Warning')
-- Missing mandatory area data
('AREA-004', 'area', 'Mandatory data is missing or incomplete — cells should not be left blank.', 'Missing mandatory area data', 'Critical')
-- Tags mapped to incorrect area level
('AREA-005', 'area', 'Tags are not correctly mapped to the appropriate area code level — resolve area hierarchy.', 'Tags mapped to incorrect area level', 'Warning')
-- Area data delivery incomplete
('AREA-006', 'area', 'Area register data delivery tracking — data is still to be completed.', 'Area data delivery incomplete', 'Info')

-- =========================================================================
-- DOMAIN: TAG
-- =========================================================================
-- Tag description blank
('TAG-001', 'tag', 'Tag description is blank for one or more tags — functional description must be provided.', 'Tag description blank', 'Critical')
-- Tag description not functional or too vague
('TAG-002', 'tag', 'Functional description should indicate function/service and be elaborative enough to understand the tag clearly.', 'Tag description not functional or too vague', 'Warning')
-- Tag description too short
('TAG-003', 'tag', 'Tag description is too short — please revise and provide a more detailed description.', 'Tag description too short', 'Warning')
-- Tag description exceeds 255 chars
('TAG-004', 'tag', 'Tag description exceeds 255 characters — please limit within 255 characters.', 'Tag description exceeds 255 chars', 'Warning')
-- Tag description has extra spaces
('TAG-005', 'tag', 'Tag description contains multiple extra spaces — remove extra spaces.', 'Tag description has extra spaces', 'Warning')
-- Tag description ends with dash
('TAG-006', 'tag', 'Tag description ends with "-" — correct to reflect proper tag reference.', 'Tag description ends with dash', 'Warning')
-- Tag description starts with dash
('TAG-007', 'tag', 'Tag description starts with "-" — correct the description.', 'Tag description starts with dash', 'Warning')
-- Tag description trailing NA
('TAG-008', 'tag', 'Tag description ends with ", NA" — this trailing value can be eliminated.', 'Tag description trailing NA', 'Warning')
-- Tag description spelling error
('TAG-009', 'tag', 'Tag description contains spelling errors — include a spell check.', 'Tag description spelling error', 'Warning')
-- Tag description vs class mismatch
('TAG-010', 'tag', 'Tag description and tag class name are mismatched — check and correct.', 'Tag description vs class mismatch', 'Warning')
-- Pipe tag description missing from-to
('TAG-011', 'tag', 'Tag description does not include From-To connection details for pipe tags — update where applicable.', 'Pipe tag description missing from-to', 'Warning')
-- Tag number incomplete in description
('TAG-012', 'tag', 'Tag number is incomplete in tag description — correct the description.', 'Tag number incomplete in description', 'Warning')
-- Tag description is just class name
('TAG-013', 'tag', 'Tag description uses only the class name without additional functional detail — expand description.', 'Tag description is just class name', 'Warning')
-- Tag class not in ISM
('TAG-020', 'tag', 'Tag class is not available in the ISM / Jackdaw Reference Data — provide a valid alternative class.', 'Tag class not in ISM', 'Critical')
-- Tag class blank
('TAG-021', 'tag', 'Tag class is blank — mandatory field must be populated.', 'Tag class blank', 'Critical')
-- Better alternative tag class available
('TAG-022', 'tag', 'A better alternative tag class is available in ISM — consider using the more specific class.', 'Better alternative tag class available', 'Warning')
-- Tag class vs description mismatch
('TAG-023', 'tag', 'Tag class and description are mismatched — review and align classification with description.', 'Tag class vs description mismatch', 'Warning')
-- Abstract tag class used
('TAG-024', 'tag', 'Abstract or parent tag class used — use the most specific available class from ISM.', 'Abstract tag class used', 'Warning')
-- Tag class for soft tag assigned to physical item
('TAG-025', 'tag', 'Tag class is used only for virtual or soft tags but a physical item exists — change to appropriate physical class.', 'Tag class for soft tag assigned to physical item', 'Warning')
-- TNC non-compliance
('TAG-030', 'tag', 'Tag naming does not conform with Jackdaw Tagging Specification — check and correct.', 'TNC non-compliance', 'Critical')
-- Comma instead of point in tag name
('TAG-031', 'tag', 'Tag name contains a comma instead of a point — correct the delimiter.', 'Comma instead of point in tag name', 'Warning')
-- Tag name ends with dash
('TAG-032', 'tag', 'Tag name ends with "-" — if insulated should end with insulation code, otherwise with "N".', 'Tag name ends with dash', 'Warning')
-- Non-standard dash in tag name
('TAG-033', 'tag', 'Non-standard dash character used in tag name — use uniform "-" to ensure correct system import.', 'Non-standard dash in tag name', 'Warning')
-- Control panel CP in TNC
('TAG-034', 'tag', 'Control panel tag uses "CP" in TNC — check whether this is the correct TNC pattern.', 'Control panel CP in TNC', 'Warning')
-- TNC inconsistent with similar tags
('TAG-035', 'tag', 'TNC differs significantly from similar tags of the same class — review for consistency.', 'TNC inconsistent with similar tags', 'Warning')
-- Tag prefix vs plant code mismatch
('TAG-036', 'tag', 'Tag prefix does not match plant code — check cross-plant tagging and correct.', 'Tag prefix vs plant code mismatch', 'Warning')
-- Tag area code blank
('TAG-040', 'tag', 'Area code is blank for one or more tags — although not mandatory it is strongly recommended.', 'Tag area code blank', 'Warning')
-- Tag area code is NA
('TAG-041', 'tag', 'Area code is set to "NA" — check and correct, especially for physical items.', 'Tag area code is NA', 'Warning')
-- Tag process unit code missing
('TAG-042', 'tag', 'Process unit code is missing for one or more tags — mandatory field, populate from system.', 'Tag process unit code missing', 'Critical')
-- Tag process unit not in register
('TAG-043', 'tag', 'Process unit code does not match or is not available in the Process Unit register.', 'Tag process unit not in register', 'Critical')
-- Tag process unit code is NA
('TAG-044', 'tag', 'Process unit code is set to "NA" — check and correct.', 'Tag process unit code is NA', 'Warning')
-- Parent tag missing for physical tag
('TAG-050', 'tag', 'Parent tag is missing for tags of classes such as Valve, Transmitter, Pipe — provide parent tag where possible.', 'Parent tag missing for physical tag', 'Warning')
-- Parent tag not in MTR
('TAG-051', 'tag', 'Parent tag referenced does not exist in the tag register — parent tag must be a valid active tag.', 'Parent tag not in MTR', 'Critical')
-- Tag is own parent tag
('TAG-052', 'tag', 'Tag itself is listed as its own parent tag — self-reference not permitted.', 'Tag is own parent tag', 'Critical')
-- Pipe parent tag is also pipe
('TAG-053', 'tag', 'Parent tag for a pipe tag is also a pipe tag — acceptable only for small bore/nipple connections.', 'Pipe parent tag is also pipe', 'Warning')
-- Parent tag derivable from description
('TAG-054', 'tag', 'Parent tag can be derived from the tag description — review description and assign parent tag.', 'Parent tag derivable from description', 'Warning')
-- Parent tag not matched with doc reference
('TAG-055', 'tag', 'Parent tag does not match the Doc-Tag reference — check and correct.', 'Parent tag not matched with doc reference', 'Warning')
-- Parent tag hierarchy depth exceeded
('TAG-056', 'tag', 'Parent tag hierarchy exceeds expected depth — review parent-child chain for correctness.', 'Parent tag hierarchy depth exceeded', 'Warning')
-- Safety critical item blank
('TAG-060', 'tag', 'Safety Critical Item field is blank — must be populated with Yes or No.', 'Safety critical item blank', 'Critical')
-- Safety critical reason missing
('TAG-061', 'tag', 'Safety Critical Item Reason Awarded is not provided for safety critical items — mandatory per EIS.', 'Safety critical reason missing', 'Critical')
-- Multiple SECE groups on tag
('TAG-062', 'tag', 'Tags have multiple SECE item groups assigned — each tag should have only one performance standard.', 'Multiple SECE groups on tag', 'Critical')
-- Safety critical not linked to performance standard
('TAG-063', 'tag', 'Safety critical items are not linked to any performance standard — link required.', 'Safety critical not linked to performance standard', 'Critical')
-- Missing SECE classification
('TAG-064', 'tag', 'Some items not tagged as SECE that should be — review classification per applicable standard.', 'Missing SECE classification', 'Critical')
-- Incorrect SECE performance standard allocation
('TAG-065', 'tag', 'Incorrect equipment allocated under this performance standard — review and reassign.', 'Incorrect SECE performance standard allocation', 'Warning')
-- Safety critical item out of SECE scope
('TAG-066', 'tag', 'Safety critical item value is populated but item is no longer in the performance standard scope — review.', 'Safety critical item out of SECE scope', 'Warning')
-- Production critical item blank
('TAG-070', 'tag', 'Production Critical Item field is blank — must be populated with a valid value from the approved list.', 'Production critical item blank', 'Critical')
-- Company name missing on tag
('TAG-080', 'tag', 'Company name is missing for physical equipment tags — recommended to populate.', 'Company name missing on tag', 'Warning')
-- PO code missing on tag
('TAG-081', 'tag', 'PO code is missing for physical tags — recommended to populate for all physical items.', 'PO code missing on tag', 'Warning')
-- Designed by company blank
('TAG-082', 'tag', 'Designed by company name field is blank — check and correct.', 'Designed by company blank', 'Warning')
-- Supplier company name not matching register
('TAG-083', 'tag', 'Supplier company name differs from the Company register — align with approved company list.', 'Supplier company name not matching register', 'Warning')
-- Mandatory tag fields blank
('TAG-090', 'tag', 'Mandatory fields are blank — Tag Class, Area Code, Safety Critical, Production Critical must be populated.', 'Mandatory tag fields blank', 'Critical')
-- General tag data missing
('TAG-091', 'tag', 'Data missing or incomplete — cells should not be left blank; positive response should demonstrate entry has been considered.', 'General tag data missing', 'Critical')
-- Tags not matched with doc reference
('TAG-092', 'tag', 'Tags are not matched with the document-to-tag reference — check and correct.', 'Tags not matched with doc reference', 'Warning')
-- Previous comments outstanding
('TAG-093', 'tag', 'Previous revision comments are still outstanding — review and address.', 'Previous comments outstanding', 'Info')
-- Data to be completed in next revision
('TAG-094', 'tag', 'Delivery tracking comment — data is to be completed in next revision.', 'Data to be completed in next revision', 'Info')

-- =========================================================================
-- DOMAIN: EQUIPMENT
-- =========================================================================
-- Equipment class not in ISM
('EQUIP-001', 'equipment', 'Equipment class is missing or not matching Jackdaw ISM (RDL) — provide correct class.', 'Equipment class not in ISM', 'Critical')
-- Equipment class blank
('EQUIP-002', 'equipment', 'Equipment class blank — mandatory field must be populated.', 'Equipment class blank', 'Critical')
-- Equipment class vs description mismatch
('EQUIP-003', 'equipment', 'Equipment class does not match tag description — review and align classification.', 'Equipment class vs description mismatch', 'Warning')
-- Equipment description missing
('EQUIP-010', 'equipment', 'Equipment description is missing — mandatory field must be populated.', 'Equipment description missing', 'Critical')
-- Equipment description ends with dash
('EQUIP-011', 'equipment', 'Equipment description ends with "-" — correct the description.', 'Equipment description ends with dash', 'Warning')
-- Equipment description starts with dash
('EQUIP-012', 'equipment', 'Equipment description starts with "-" — correct the description.', 'Equipment description starts with dash', 'Warning')
-- Equipment description too short
('EQUIP-013', 'equipment', 'Equipment description is too short — revise and provide a more detailed description.', 'Equipment description too short', 'Warning')
-- Equipment description spelling error
('EQUIP-014', 'equipment', 'Equipment description contains spelling errors — check and correct.', 'Equipment description spelling error', 'Warning')
-- Equipment description duplicated
('EQUIP-015', 'equipment', 'Equipment description duplicated across multiple equipment numbers — verify uniqueness.', 'Equipment description duplicated', 'Warning')
-- Manufacturer serial number blank
('EQUIP-020', 'equipment', 'Manufacturer serial number is blank — mandatory property per EIS; use TBC if unknown, BULK MATERIAL for bulk items.', 'Manufacturer serial number blank', 'Critical')
-- Manufacturer serial number is NA
('EQUIP-021', 'equipment', 'Manufacturer serial number is set to NA — NA is not permitted; use TBC or BULK MATERIAL.', 'Manufacturer serial number is NA', 'Critical')
-- Model part name missing
('EQUIP-022', 'equipment', 'Model part name is missing — mandatory property per EIS (except soft tags).', 'Model part name missing', 'Critical')
-- Manufacturing company not populated
('EQUIP-023', 'equipment', 'Manufacturing company is not populated — non-mandatory but recommended for all physical equipment.', 'Manufacturing company not populated', 'Warning')
-- Equipment TNC non-compliance
('EQUIP-030', 'equipment', 'Equipment number does not conform with Jackdaw Tagging Specifications — check and correct.', 'Equipment TNC non-compliance', 'Critical')
-- Equipment plant code not in register
('EQUIP-031', 'equipment', 'Equipment plant code contains values not part of the Area or Process Unit register — verify validity.', 'Equipment plant code not in register', 'Warning')
-- Equipment parent tag derivable from description
('EQUIP-040', 'equipment', 'Parent tag can be derived from the equipment description — review and assign.', 'Equipment parent tag derivable from description', 'Warning')
-- Equipment is own parent tag
('EQUIP-041', 'equipment', 'Equipment is self-referencing as parent tag — check and correct.', 'Equipment is own parent tag', 'Critical')
-- Equipment not matched with doc reference
('EQUIP-042', 'equipment', 'Equipment number is not matched with the Doc-Equipment reference — check and correct.', 'Equipment not matched with doc reference', 'Warning')
-- Equipment tag not in MTR
('EQUIP-043', 'equipment', 'Equipment number corresponding tag is not part of the Tag Register (MTR).', 'Equipment tag not in MTR', 'Critical')
-- Equipment number missing plant code prefix
('EQUIP-044', 'equipment', 'Equipment number format does not include required plant code prefix.', 'Equipment number missing plant code prefix', 'Warning')
-- Mandatory equipment fields blank
('EQUIP-050', 'equipment', 'Mandatory fields are blank — equipment description, installation date and other required fields must be populated.', 'Mandatory equipment fields blank', 'Critical')
-- General equipment data missing
('EQUIP-051', 'equipment', 'Data missing or incomplete — use "not applicable" to indicate the review has been considered.', 'General equipment data missing', 'Warning')
-- Tag register changes not reflected in equipment register
('EQUIP-052', 'equipment', 'Changes made in the Tag Register should also be reflected in the Equipment Register.', 'Tag register changes not reflected in equipment register', 'Warning')
-- Equipment has no document references
('EQUIP-053', 'equipment', 'Equipment in Equipment Register is not referenced in any Document-Equipment reference.', 'Equipment has no document references', 'Warning')

-- =========================================================================
-- DOMAIN: EQUIPMENT_PROPERTY
-- =========================================================================
-- Equipment has no properties in property register
('EQPROP-001', 'equipment_property', 'Equipment property values are not available for equipment that is part of the Equipment Register.', 'Equipment has no properties in property register', 'Warning')
-- Equipment class-property mapping mismatch
('EQPROP-002', 'equipment_property', 'Equipment class mapping against equipment is incorrect — the expected properties per ISM are not provided.', 'Equipment class-property mapping mismatch', 'Critical')
-- Required ISM equipment properties not submitted
('EQPROP-003', 'equipment_property', 'Required properties per ISM standards are not included in the CIS submission.', 'Required ISM equipment properties not submitted', 'Critical')
-- Equipment in property register not in equipment register
('EQPROP-004', 'equipment_property', 'Equipment entries in the Property register are not part of the Equipment Register — may be void or deleted.', 'Equipment in property register not in equipment register', 'Warning')
-- Equipment property orphan record
('EQPROP-005', 'equipment_property', 'Equipment number is listed in Property Register but is not part of the Equipment Register.', 'Equipment property orphan record', 'Warning')
-- Duplicate equipment property entries
('EQPROP-006', 'equipment_property', 'Duplicate property entries exist for the same equipment number — each property should appear only once.', 'Duplicate equipment property entries', 'Critical')
-- UOM populated when property value is NA
('EQPROP-007', 'equipment_property', 'Property value is NA but UOM is populated — remove UOM when property value is NA.', 'UOM populated when property value is NA', 'Warning')
-- Equipment property value blank
('EQPROP-008', 'equipment_property', 'Property value cells are blank — update or indicate not applicable.', 'Equipment property value blank', 'Warning')
-- Wrong header in equipment property register
('EQPROP-009', 'equipment_property', 'Equipment Number header is required in the Equipment Property Register instead of Tag Number.', 'Wrong header in equipment property register', 'Warning')
-- Equipment property value is zero
('EQPROP-010', 'equipment_property', 'Property value is set to "0" — if data is pending use TBC rather than zero.', 'Equipment property value is zero', 'Warning')
-- Equipment property register has tag numbers
('EQPROP-011', 'equipment_property', 'Equipment Property register contains tags instead of equipment numbers — use equipment numbers only.', 'Equipment property register has tag numbers', 'Critical')

-- =========================================================================
-- DOMAIN: TAG_PROPERTY
-- =========================================================================
-- Tag has no properties in property register
('TPROP-001', 'tag_property', 'Tags in the Tag Register have no associated properties in the Tag Property register.', 'Tag has no properties in property register', 'Warning')
-- Tag class-property mapping mismatch
('TPROP-002', 'tag_property', 'Tag class mapping against tag in the Property register is different from the class in the Tag Register — mismatch must be resolved.', 'Tag class-property mapping mismatch', 'Critical')
-- Property register tag not in MTR
('TPROP-003', 'tag_property', 'Tags referenced in the Property register are not available in the Tag Register (MTR) — may be void or deleted.', 'Property register tag not in MTR', 'Critical')
-- Required ISM tag properties not submitted
('TPROP-004', 'tag_property', 'Required properties per ISM standards are not included in the CIS submission.', 'Required ISM tag properties not submitted', 'Critical')
-- Tag property value is zero
('TPROP-005', 'tag_property', 'Property value is set to "0" — if data is pending use TBC rather than zero.', 'Tag property value is zero', 'Warning')
-- UOM populated when property value is NA
('TPROP-006', 'tag_property', 'Property value is NA but UOM is populated — remove UOM when property value is NA.', 'UOM populated when property value is NA', 'Warning')
-- Duplicate tag property entries
('TPROP-007', 'tag_property', 'Duplicate property values exist in the register — check and remove duplicates.', 'Duplicate tag property entries', 'Critical')
-- Non-standard property code prefix
('TPROP-008', 'tag_property', 'Property code contains non-standard prefix — confirm whether it is approved and provide TQ reference if so.', 'Non-standard property code prefix', 'Warning')
-- Property register incomplete submission
('TPROP-009', 'tag_property', 'Property register is incomplete — the submission contains too few records to be reviewed; resubmit complete register.', 'Property register incomplete submission', 'Critical')
-- Plant code column missing in property register
('TPROP-010', 'tag_property', 'Plant Code column is missing from the deliverable — add required column.', 'Plant code column missing in property register', 'Critical')
-- Column header names changed
('TPROP-011', 'tag_property', 'Column header names must not be changed from the approved template.', 'Column header names changed', 'Warning')
-- Tag property value blank or incomplete
('TPROP-012', 'tag_property', 'Property value cells are blank or only partially populated — update in next revision.', 'Tag property value blank or incomplete', 'Warning')
-- Cable CSA value contains unexpected characters
('TPROP-013', 'tag_property', 'Cable cross sectional area contains unexpected characters — verify correctness.', 'Cable CSA value contains unexpected characters', 'Warning')
-- UOM missing for numeric property value
('TPROP-014', 'tag_property', 'UOM (unit of measure) is missing for numeric property values — add UOM per ISM specification.', 'UOM missing for numeric property value', 'Warning')
-- Non-numeric value in numeric property field
('TPROP-015', 'tag_property', 'Property value contains text in a numeric field — provide numeric value or use TBC.', 'Non-numeric value in numeric property field', 'Warning')

-- =========================================================================
-- DOMAIN: TAG_CONNECTION
-- =========================================================================
-- Duplicate physical connection entries
('TCONN-001', 'tag_connection', 'Duplicate physical connection records exist — remove duplicate entries.', 'Duplicate physical connection entries', 'Critical')
-- From-tag equals to-tag
('TCONN-002', 'tag_connection', 'From-Tag and To-Tag are the same — self-connection not permitted, check and correct.', 'From-tag equals to-tag', 'Critical')
-- From-tag not in MTR
('TCONN-003', 'tag_connection', 'Tags referenced in the From-Tag column are not part of the Tag Register.', 'From-tag not in MTR', 'Critical')
-- Physical connections scope too narrow
('TCONN-004', 'tag_connection', 'Physical connection scope is limited to pipes — expand to include cable and instrument connections per specification.', 'Physical connections scope too narrow', 'Warning')
-- Wrong CSV template for tag connections
('TCONN-005', 'tag_connection', 'CSV template used is incorrect — required columns are PLANT_CODE, FROM_TAG_NAME, TO_TAG_NAME only.', 'Wrong CSV template for tag connections', 'Warning')
-- Tag class list for connections not provided
('TCONN-006', 'tag_connection', 'Tag class list for which physical connections are expected has not been provided — submit list to track progress.', 'Tag class list for connections not provided', 'Info')
-- Low physical connection record count
('TCONN-007', 'tag_connection', 'Physical connection record count is low — expand coverage beyond current tag classes as discussed.', 'Low physical connection record count', 'Warning')
-- To-tag not in MTR
('TCONN-008', 'tag_connection', 'To-Tag column contains tags not in the Tag Register — verify and correct.', 'To-tag not in MTR', 'Critical')
-- Physical connection register empty
('TCONN-009', 'tag_connection', 'Physical connection register is empty — data has not been submitted.', 'Physical connection register empty', 'Critical')

-- =========================================================================
-- DOMAIN: TAG_CLASS_PROPERTY
-- =========================================================================
-- Tag class required properties not in CIS submission
('TCPROP-001', 'tag_class_property', 'Tag class property scope table — listed properties required per ISM are not provided in the CIS submission.', 'Tag class required properties not in CIS submission', 'Critical')
-- Tag class properties not matching ISM schema
('TCPROP-002', 'tag_class_property', 'Tag class properties submitted do not match the expected properties from the approved ISM schema.', 'Tag class properties not matching ISM schema', 'Critical')
-- Tag class name blank in property scope
('TCPROP-003', 'tag_class_property', 'Tag class name in property scope table is blank — mandatory field.', 'Tag class name blank in property scope', 'Critical')

-- =========================================================================
-- DOMAIN: DOCUMENT
-- =========================================================================
-- Tags without document references
('DOC-001', 'document', 'Tags in the Tag Register do not have document references in the Doc-Tag register.', 'Tags without document references', 'Warning')
-- Doc-tag references tag not in MTR
('DOC-002', 'document', 'Tags referenced in the Doc-Tag register are not available in the Tag Register (MTR).', 'Doc-tag references tag not in MTR', 'Critical')
-- Doc-tag document not in DocMaster
('DOC-003', 'document', 'Documents in the Doc-Tag reference are not available in the Document Master register.', 'Doc-tag document not in DocMaster', 'Critical')
-- Duplicate document records
('DOC-004', 'document', 'Duplicate document records found in the register — remove duplicates.', 'Duplicate document records', 'Critical')
-- Doc numbers not matching DMS
('DOC-005', 'document', 'Document numbers do not match records in the Document Management system (Assai) — check and correct.', 'Doc numbers not matching DMS', 'Critical')
-- Void tags have doc references
('DOC-006', 'document', 'Void or deleted tags should not have document references — remove references for deleted tags.', 'Void tags have doc references', 'Warning')
-- Outdated document template used
('DOC-007', 'document', 'Document template version used is outdated — resubmit using the current approved template.', 'Outdated document template used', 'Warning')
-- Doc title mismatch with DMS
('DOC-008', 'document', 'Document title in the register does not match the title in the Document Management system.', 'Doc title mismatch with DMS', 'Warning')
-- Doc revision mismatch with DMS
('DOC-009', 'document', 'Document revision in the register does not match the latest revision in the DMS.', 'Doc revision mismatch with DMS', 'Warning')
-- Doc-area document not in DocMaster
('DOC-010', 'document', 'Documents in the Doc-Area reference are not available in the Document Master register.', 'Doc-area document not in DocMaster', 'Critical')
-- Doc-area reference missing area code
('DOC-011', 'document', 'Document records in the Doc-Area reference do not have Area Code — populate or explain if not applicable.', 'Doc-area reference missing area code', 'Warning')
-- Doc-PU document not in DocMaster
('DOC-020', 'document', 'Documents in the Doc-Process Unit reference are not available in the Document Master register.', 'Doc-PU document not in DocMaster', 'Critical')
-- Doc-PU reference missing process unit code
('DOC-021', 'document', 'Process unit code is missing in the Doc-Process Unit register records.', 'Doc-PU reference missing process unit code', 'Warning')
-- Doc-PU process unit not in register
('DOC-022', 'document', 'Process unit code in the Doc-Process Unit register does not match the Process Unit register.', 'Doc-PU process unit not in register', 'Critical')
-- Doc-PU plant code not in register
('DOC-023', 'document', 'Plant code in the Doc-Process Unit register is not available in the Process Unit register — verify validity.', 'Doc-PU plant code not in register', 'Warning')
-- Wrong CSV template for doc-PU register
('DOC-024', 'document', 'Incorrect CSV template used — required columns are DOCUMENT_NUMBER, PLANT_CODE, PROCESS_UNIT_CODE.', 'Wrong CSV template for doc-PU register', 'Warning')
-- Equipment without document reference
('DOC-030', 'document', 'Equipment items do not have any document reference — recommended to have Doc-Equipment reference.', 'Equipment without document reference', 'Warning')
-- Doc-equipment document not in DocMaster
('DOC-031', 'document', 'Documents in the Doc-Equipment reference are not available in the Document Master register.', 'Doc-equipment document not in DocMaster', 'Critical')
-- Doc-equipment equipment not in register
('DOC-032', 'document', 'Equipment records in the Doc-Equipment reference are not part of the Equipment Register.', 'Doc-equipment equipment not in register', 'Critical')
-- Doc-equipment references model parts
('DOC-033', 'document', 'Doc-Equipment register references model parts instead of equipment numbers — correct entity type.', 'Doc-equipment references model parts', 'Warning')
-- Doc-PO document not in DocMaster
('DOC-040', 'document', 'Documents in the Doc-PO reference are not available in the Document Master register.', 'Doc-PO document not in DocMaster', 'Critical')
-- Doc-PO code not in PO register
('DOC-041', 'document', 'PO code in the Doc-PO reference does not exist in the Purchase Order register.', 'Doc-PO code not in PO register', 'Critical')
-- Void PO code in doc-PO reference
('DOC-042', 'document', 'PO code is void — void PO codes should not be referenced in this register.', 'Void PO code in doc-PO reference', 'Warning')
-- Company name not in company register for PO
('DOC-043', 'document', 'Company name is missing or not matching the Company register for PO references.', 'Company name not in company register for PO', 'Warning')
-- Doc-plant document not in DocMaster
('DOC-050', 'document', 'Documents in the Doc-Plant reference are not available in the Document Master register.', 'Doc-plant document not in DocMaster', 'Critical')
-- Doc-site document not in DocMaster
('DOC-051', 'document', 'Documents in the Doc-Site reference are not available in the Document Master register.', 'Doc-site document not in DocMaster', 'Critical')
-- Site code format incorrect
('DOC-052', 'document', 'Site code must be standardised — use the approved site code format.', 'Site code format incorrect', 'Warning')
-- Document not in DMS or NYI
('DOC-060', 'document', 'Documents are not available in the Document Management system or are in NYI (Not Yet Issued) status.', 'Document not in DMS or NYI', 'Critical')
-- Loop diagram reference missing
('DOC-061', 'document', 'Contractor is asked to reference associated loop diagrams against each tag.', 'Loop diagram reference missing', 'Warning')
-- Layout drawing reference missing
('DOC-062', 'document', 'Contractor is asked to reference associated layout drawings against each tag.', 'Layout drawing reference missing', 'Warning')
-- PID schematic reference missing
('DOC-063', 'document', 'Contractor is asked to reference associated P&ID or schematics against each tag.', 'PID schematic reference missing', 'Warning')
-- Combined document file submitted
('DOC-064', 'document', 'Document is submitted as a combined file — individual documents should be referenced separately.', 'Combined document file submitted', 'Info')

-- =========================================================================
-- DOMAIN: PURCHASE_ORDER
-- =========================================================================
-- PO code not in PO register
('PO-001', 'purchase_order', 'PO code referenced in the Tag Register is not available or not matching the Purchase Order register.', 'PO code not in PO register', 'Critical')
-- PO date missing
('PO-002', 'purchase_order', 'PO date is missing — mandatory field in the Purchase Order register.', 'PO date missing', 'Critical')
-- PO code missing for physical tags
('PO-003', 'purchase_order', 'Physical tags do not have PO code — non-mandatory but recommended for all physical items.', 'PO code missing for physical tags', 'Warning')
-- PO receiver company missing
('PO-004', 'purchase_order', 'PO receiver company name is missing — check and correct.', 'PO receiver company missing', 'Warning')
-- PO description contains invalid characters
('PO-005', 'purchase_order', 'PO description values contain special characters or commas not permitted in this field.', 'PO description contains invalid characters', 'Warning')
-- PO code is void
('PO-006', 'purchase_order', 'PO code is listed as void in the Purchase Order register — remove or replace reference.', 'PO code is void', 'Critical')
-- Multiple PO codes for same equipment
('PO-007', 'purchase_order', 'Multiple PO codes reference the same equipment — verify and retain only the correct association.', 'Multiple PO codes for same equipment', 'Warning')

-- =========================================================================
-- DOMAIN: PROCESS_UNIT
-- =========================================================================
-- Multiple process unit codes for same system
('PU-001', 'process_unit', 'Multiple process unit codes are used for the same system — consolidate or clarify scope.', 'Multiple process unit codes for same system', 'Warning')
-- Process unit plant code not in standard list
('PU-002', 'process_unit', 'Plant code used in the Process Unit register is not part of the standard plant code list — verify.', 'Process unit plant code not in standard list', 'Warning')
-- Process unit formatting inconsistent
('PU-003', 'process_unit', 'Formatting is inconsistent — use either all caps or first-letter capitals consistently.', 'Process unit formatting inconsistent', 'Info')
-- Process unit data missing
('PU-004', 'process_unit', 'Mandatory data is missing or incomplete — populate all required process unit fields.', 'Process unit data missing', 'Critical')
-- Process unit description blank
('PU-005', 'process_unit', 'Process unit description is blank — populate the description field.', 'Process unit description blank', 'Warning')
-- Process unit hierarchy inconsistent
('PU-006', 'process_unit', 'Process unit hierarchy (parent/child) is not consistent with the Area register structure.', 'Process unit hierarchy inconsistent', 'Warning')

-- =========================================================================
-- DOMAIN: MODEL_PART
-- =========================================================================
-- Model part description not defined
('MPART-001', 'model_part', 'Model part description is not yet defined — required for data loading in downstream system.', 'Model part description not defined', 'Critical')
-- Model part not in model part register
('MPART-002', 'model_part', 'Model part referenced in Equipment Register does not exist in the Model Part register.', 'Model part not in model part register', 'Critical')
-- Model part number invalid characters
('MPART-003', 'model_part', 'Model part number contains special characters not permitted — correct the format.', 'Model part number invalid characters', 'Warning')

-- =========================================================================
-- DOMAIN: OTHER
-- =========================================================================
-- Company name missing for tags
('OTHER-001', 'other', 'Company name is not available for physical equipment tags — recommended to populate.', 'Company name missing for tags', 'Warning')
-- Company name has double spaces
('OTHER-002', 'other', 'Company name contains double spaces — remove extra spaces from the company register.', 'Company name has double spaces', 'Warning')
-- Company name not in company register
('OTHER-003', 'other', 'Company name referenced in MTR is not available in the Company register.', 'Company name not in company register', 'Critical')
-- Company name contains invalid characters
('OTHER-004', 'other', 'Company register values contain commas or special characters not permitted — remove invalid characters.', 'Company name contains invalid characters', 'Warning')
-- Many TBA entries in register
('OTHER-005', 'other', 'Significant number of entries remain TBA or TBC — include all available information.', 'Many TBA entries in register', 'Warning')
-- Documents not in DMS or NYI
('OTHER-006', 'other', 'Document numbers are not available in the DMS or are still in NYI status.', 'Documents not in DMS or NYI', 'Critical')
-- Wrong CIS submission template
('OTHER-007', 'other', 'Submission uses wrong file template — resubmit using the approved CIS template.', 'Wrong CIS submission template', 'Critical')
-- Outstanding items from previous revision
('OTHER-008', 'other', 'General comment — data quality is improving but outstanding items from previous revision still require attention.', 'Outstanding items from previous revision', 'Info')

ON CONFLICT (category_code) DO UPDATE SET
    domain              = EXCLUDED.domain,
    template_text       = EXCLUDED.template_text,
    short_template_text = EXCLUDED.short_template_text,
    severity            = EXCLUDED.severity,
    updated_at          = now();

-- =============================================================================
-- Verification
-- =============================================================================
SELECT domain, severity, COUNT(*) AS n
FROM audit_core.crs_comment_template
GROUP BY domain, severity
ORDER BY domain, severity;
