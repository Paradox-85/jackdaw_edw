-- =============================================================================
-- Migration 019: CRS Comment Templates — Master Extended Seed
-- =============================================================================
-- Sources merged:
--   1. migration_018_crs_categories_seed.sql  (original seed, CRS-C01..C50)
--   2. crs_comment_templates_extended.sql     (Claude Sonnet, 149 rows)
--   3. crs_comment_by_domain.xlsx             (1071 real CRS comments)
-- Idempotent: DELETE rows owned by this migration, then plain INSERT.
-- Total: 179 templates | 12 domains
-- Severity: Critical=68 | Warning=104 | Info=7
-- =============================================================================

BEGIN;

-- =============================================================================
-- Part A: DDL — add new columns if not already present
-- =============================================================================

ALTER TABLE audit_core.crs_comment_template
    ADD COLUMN IF NOT EXISTS category_code TEXT        NULL,
    ADD COLUMN IF NOT EXISTS domain        TEXT        NULL,
    ADD COLUMN IF NOT EXISTS severity      TEXT        NULL DEFAULT 'Warning',
    ADD COLUMN IF NOT EXISTS updated_at    TIMESTAMPTZ NULL DEFAULT now();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname  = 'crs_comment_template_category_code_key'
          AND conrelid = 'audit_core.crs_comment_template'::regclass
    ) THEN
        ALTER TABLE audit_core.crs_comment_template
            ADD CONSTRAINT crs_comment_template_category_code_key
            UNIQUE (category_code);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_crs_template_category_code
    ON audit_core.crs_comment_template (category_code)
    WHERE category_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_crs_template_domain
    ON audit_core.crs_comment_template (domain)
    WHERE domain IS NOT NULL AND object_status = 'Active';

-- =============================================================================
-- Part B: DML — wipe rows owned by this migration, then re-insert clean
-- All rows seeded here are identified by category_code IS NOT NULL.
-- Legacy rows (category_code IS NULL) from earlier migrations are untouched.
-- =============================================================================

DELETE FROM audit_core.crs_comment_template
WHERE category_code IS NOT NULL;

INSERT INTO audit_core.crs_comment_template
    (category_code, domain, template_text, template_hash,
     short_template_text, severity, source, category)
SELECT
    category_code,
    domain,
    template_text,
    md5(lower(trim(template_text))),
    short_template_text,
    severity,
    'manual',
    CASE
        WHEN category_code LIKE 'TAG-06%' OR category_code LIKE 'TAG-07%' THEN 'SAFETY'
        WHEN category_code LIKE 'TAG-%'   OR category_code LIKE 'AREA-%'  THEN 'TAG_DATA'
        WHEN category_code LIKE 'EQUIP-%'                                  THEN 'EQUIPMENT_DATA'
        WHEN category_code LIKE 'EQPROP-%' OR category_code LIKE 'TPROP-%'
          OR category_code LIKE 'TCPROP-%'                                 THEN 'PROPERTY'
        WHEN category_code LIKE 'TCONN-%'  THEN 'TAG_CONNECTION'
        WHEN category_code LIKE 'DOC-%'    THEN 'DOCUMENT'
        WHEN category_code LIKE 'PO-%'     THEN 'PURCHASE_ORDER'
        WHEN category_code LIKE 'PU-%'     THEN 'PROCESS_UNIT'
        WHEN category_code LIKE 'MPART-%'  THEN 'MODEL_PART'
        ELSE 'OTHER'
    END
FROM (VALUES

-- =========================================================================
-- DOMAIN: AREA (6)
-- =========================================================================
  ('AREA-001', 'area', 'AREA_CODE is duplicated within the same cell — check and correct.',             'Area code duplicated in cell',              'Warning'),
  ('AREA-002', 'area', 'AREA_NAME contains spelling errors — check and correct.',                        'Area name spelling error',                  'Warning'),
  ('AREA-003', 'area', 'Area code is set to "NA" — this is not a valid area code, check and correct.',  'Area code is literal NA',                   'Warning'),
  ('AREA-004', 'area', 'Mandatory data is missing or incomplete — cells should not be left blank.',      'Missing mandatory area data',               'Critical'),
  ('AREA-005', 'area', 'Tags are not correctly mapped to the appropriate area code level — resolve area hierarchy.', 'Tags mapped to incorrect area level', 'Warning'),
  ('AREA-006', 'area', 'Area register data delivery tracking — data is still to be completed.',          'Area data delivery incomplete',             'Info'),

-- =========================================================================
-- DOMAIN: TAG (56)
-- =========================================================================
  ('TAG-001', 'tag', 'Tag description is blank for one or more tags — functional description must be provided.',                           'Tag description blank',                     'Critical'),
  ('TAG-002', 'tag', 'Functional description should indicate function/service and be elaborative enough to understand the tag clearly.',    'Tag description not functional or too vague','Warning'),
  ('TAG-003', 'tag', 'Tag description is too short — please revise and provide a more detailed description.',                              'Tag description too short',                 'Warning'),
  ('TAG-004', 'tag', 'Tag description exceeds 255 characters — please limit within 255 characters.',                                       'Tag description exceeds 255 chars',         'Warning'),
  ('TAG-005', 'tag', 'Tag description contains multiple extra spaces — remove extra spaces.',                                              'Tag description has extra spaces',          'Warning'),
  ('TAG-006', 'tag', 'Tag description ends with a dash — correct to reflect proper tag reference.',                                        'Tag description ends with dash',            'Warning'),
  ('TAG-007', 'tag', 'Tag description starts with a dash — correct the description.',                                                      'Tag description starts with dash',          'Warning'),
  ('TAG-008', 'tag', 'Tag description ends with ", NA" — this trailing value can be eliminated.',                                          'Tag description trailing NA',               'Warning'),
  ('TAG-009', 'tag', 'Tag description contains spelling errors — include a spell check.',                                                   'Tag description spelling error',            'Warning'),
  ('TAG-010', 'tag', 'Tag description and tag class name are mismatched — check and correct.',                                             'Tag description vs class mismatch',         'Warning'),
  ('TAG-011', 'tag', 'Tag description does not include From-To connection details for pipe tags — update where applicable.',               'Pipe tag description missing from-to',      'Warning'),
  ('TAG-012', 'tag', 'Tag number is incomplete in tag description — correct the description.',                                             'Tag number incomplete in description',       'Warning'),
  ('TAG-013', 'tag', 'Tag description uses only the class name without additional functional detail — expand description.',                'Tag description is just class name',         'Warning'),
  ('TAG-020', 'tag', 'Tag class is not available in the ISM / Jackdaw Reference Data — provide a valid alternative class.',               'Tag class not in ISM',                      'Critical'),
  ('TAG-021', 'tag', 'Tag class is blank — mandatory field must be populated.',                                                            'Tag class blank',                           'Critical'),
  ('TAG-022', 'tag', 'A better alternative tag class is available in ISM — consider using the more specific class.',                       'Better alternative tag class available',     'Warning'),
  ('TAG-023', 'tag', 'Tag class and description are mismatched — review and align classification with description.',                       'Tag class vs description mismatch',         'Warning'),
  ('TAG-024', 'tag', 'Abstract or parent tag class used — use the most specific available class from ISM.',                                'Abstract tag class used',                   'Warning'),
  ('TAG-025', 'tag', 'Tag class is used only for virtual or soft tags but a physical item exists — change to appropriate physical class.', 'Tag class for soft tag on physical item',    'Warning'),
  ('TAG-030', 'tag', 'Tag naming does not conform with Jackdaw Tagging Specification — check and correct.',                               'TNC non-compliance',                        'Critical'),
  ('TAG-031', 'tag', 'Tag name contains a comma instead of a point — correct the delimiter.',                                              'Comma instead of point in tag name',        'Warning'),
  ('TAG-032', 'tag', 'Tag name ends with a dash — if insulated should end with insulation code, otherwise with N.',                        'Tag name ends with dash',                   'Warning'),
  ('TAG-033', 'tag', 'Non-standard dash character used in tag name — use uniform hyphen to ensure correct system import.',                 'Non-standard dash in tag name',             'Warning'),
  ('TAG-034', 'tag', 'Control panel tag uses CP in TNC — check whether this is the correct TNC pattern.',                                  'Control panel CP in TNC',                   'Warning'),
  ('TAG-035', 'tag', 'TNC differs significantly from similar tags of the same class — review for consistency.',                            'TNC inconsistent with similar tags',        'Warning'),
  ('TAG-036', 'tag', 'Tag prefix does not match plant code — check cross-plant tagging and correct.',                                      'Tag prefix vs plant code mismatch',         'Warning'),
  ('TAG-040', 'tag', 'Area code is blank for one or more tags — although not mandatory it is strongly recommended.',                       'Tag area code blank',                       'Warning'),
  ('TAG-041', 'tag', 'Area code is set to NA — check and correct, especially for physical items.',                                          'Tag area code is NA',                       'Warning'),
  ('TAG-042', 'tag', 'Process unit code is missing for one or more tags — mandatory field, populate from system.',                         'Tag process unit code missing',             'Critical'),
  ('TAG-043', 'tag', 'Process unit code does not match or is not available in the Process Unit register.',                                 'Tag process unit not in register',          'Critical'),
  ('TAG-044', 'tag', 'Process unit code is set to NA — check and correct.',                                                                'Tag process unit code is NA',               'Warning'),
  ('TAG-050', 'tag', 'Parent tag is missing for tags of classes such as Valve, Transmitter, Pipe — provide parent tag where possible.',   'Parent tag missing for physical tag',       'Warning'),
  ('TAG-051', 'tag', 'Parent tag referenced does not exist in the tag register — parent tag must be a valid active tag.',                  'Parent tag not in MTR',                     'Critical'),
  ('TAG-052', 'tag', 'Tag itself is listed as its own parent tag — self-reference not permitted.',                                         'Tag is own parent tag',                     'Critical'),
  ('TAG-053', 'tag', 'Parent tag for a pipe tag is also a pipe tag — acceptable only for small bore or nipple connections.',               'Pipe parent tag is also pipe',              'Warning'),
  ('TAG-054', 'tag', 'Parent tag can be derived from the tag description — review description and assign parent tag.',                     'Parent tag derivable from description',     'Warning'),
  ('TAG-055', 'tag', 'Parent tag does not match the Doc-Tag reference — check and correct.',                                               'Parent tag not matched with doc reference', 'Warning'),
  ('TAG-056', 'tag', 'Parent tag hierarchy exceeds expected depth — review parent-child chain for correctness.',                           'Parent tag hierarchy depth exceeded',       'Warning'),
  ('TAG-060', 'tag', 'Safety Critical Item field is blank — must be populated with Yes or No.',                                            'Safety critical item blank',                'Critical'),
  ('TAG-061', 'tag', 'Safety Critical Item Reason Awarded is not provided for safety critical items — mandatory per EIS.',                 'Safety critical reason missing',            'Critical'),
  ('TAG-062', 'tag', 'Tags have multiple SECE item groups assigned — each tag should have only one performance standard.',                 'Multiple SECE groups on tag',               'Critical'),
  ('TAG-063', 'tag', 'Safety critical items are not linked to any performance standard — link required.',                                  'Safety critical not linked to perf standard','Critical'),
  ('TAG-064', 'tag', 'Some items not tagged as SECE that should be — review classification per applicable standard.',                      'Missing SECE classification',               'Critical'),
  ('TAG-065', 'tag', 'Incorrect equipment allocated under this performance standard — review and reassign.',                               'Incorrect SECE perf standard allocation',   'Warning'),
  ('TAG-066', 'tag', 'Safety critical item value is populated but item is no longer in the performance standard scope — review.',          'Safety critical item out of SECE scope',    'Warning'),
  ('TAG-070', 'tag', 'Production Critical Item field is blank — must be populated with a valid value from the approved list.',             'Production critical item blank',            'Critical'),
  ('TAG-080', 'tag', 'Company name is missing for physical equipment tags — recommended to populate.',                                     'Company name missing on tag',               'Warning'),
  ('TAG-081', 'tag', 'PO code is missing for physical tags — recommended to populate for all physical items.',                             'PO code missing on tag',                    'Warning'),
  ('TAG-082', 'tag', 'Designed by company name field is blank — check and correct.',                                                       'Designed by company blank',                 'Warning'),
  ('TAG-083', 'tag', 'Supplier company name differs from the Company register — align with approved company list.',                        'Supplier company name not in register',     'Warning'),
  ('TAG-090', 'tag', 'Mandatory fields are blank — Tag Class, Area Code, Safety Critical, Production Critical must be populated.',         'Mandatory tag fields blank',                'Critical'),
  ('TAG-091', 'tag', 'Data missing or incomplete — cells should not be left blank; positive response should demonstrate entry has been considered.', 'General tag data missing',          'Critical'),
  ('TAG-092', 'tag', 'Tags are not matched with the document-to-tag reference — check and correct.',                                       'Tags not matched with doc reference',       'Warning'),
  ('TAG-093', 'tag', 'Previous revision comments are still outstanding — review and address.',                                             'Previous comments outstanding',             'Info'),
  ('TAG-094', 'tag', 'Delivery tracking comment — data is to be completed in next revision.',                                              'Data to be completed in next revision',     'Info'),

-- =========================================================================
-- DOMAIN: EQUIPMENT (24)
-- =========================================================================
  ('EQUIP-001', 'equipment', 'Equipment class is missing or not matching Jackdaw ISM (RDL) — provide correct class.',                        'Equipment class not in ISM',                             'Critical'),
  ('EQUIP-002', 'equipment', 'Equipment class blank — mandatory field must be populated.',                                                     'Equipment class blank',                                  'Critical'),
  ('EQUIP-003', 'equipment', 'Equipment class does not match tag description — review and align classification.',                              'Equipment class vs description mismatch',                'Warning'),
  ('EQUIP-010', 'equipment', 'Equipment description is missing — mandatory field must be populated.',                                          'Equipment description missing',                          'Critical'),
  ('EQUIP-011', 'equipment', 'Equipment description ends with a dash — correct the description.',                                              'Equipment description ends with dash',                   'Warning'),
  ('EQUIP-012', 'equipment', 'Equipment description starts with a dash — correct the description.',                                           'Equipment description starts with dash',                 'Warning'),
  ('EQUIP-013', 'equipment', 'Equipment description is too short — revise and provide a more detailed description.',                           'Equipment description too short',                        'Warning'),
  ('EQUIP-014', 'equipment', 'Equipment description contains spelling errors — check and correct.',                                            'Equipment description spelling error',                   'Warning'),
  ('EQUIP-015', 'equipment', 'Equipment description duplicated across multiple equipment numbers — verify uniqueness.',                        'Equipment description duplicated',                       'Warning'),
  ('EQUIP-020', 'equipment', 'Manufacturer serial number is blank — use TBC if unknown, BULK MATERIAL for bulk items.',                        'Manufacturer serial number blank',                       'Critical'),
  ('EQUIP-021', 'equipment', 'Manufacturer serial number is set to NA — NA is not permitted; use TBC or BULK MATERIAL.',                      'Manufacturer serial number is NA',                       'Critical'),
  ('EQUIP-022', 'equipment', 'Model part name is missing — mandatory property per EIS (except soft tags).',                                    'Model part name missing',                                'Critical'),
  ('EQUIP-023', 'equipment', 'Manufacturing company is not populated — non-mandatory but recommended for all physical equipment.',             'Manufacturing company not populated',                    'Warning'),
  ('EQUIP-030', 'equipment', 'Equipment number does not conform with Jackdaw Tagging Specifications — check and correct.',                     'Equipment TNC non-compliance',                           'Critical'),
  ('EQUIP-031', 'equipment', 'Equipment plant code contains values not part of the Area or Process Unit register — verify validity.',          'Equipment plant code not in register',                   'Warning'),
  ('EQUIP-040', 'equipment', 'Parent tag can be derived from the equipment description — review and assign.',                                  'Equipment parent tag derivable from description',         'Warning'),
  ('EQUIP-041', 'equipment', 'Equipment is self-referencing as parent tag — check and correct.',                                              'Equipment is own parent tag',                            'Critical'),
  ('EQUIP-042', 'equipment', 'Equipment number is not matched with the Doc-Equipment reference — check and correct.',                          'Equipment not matched with doc reference',                'Warning'),
  ('EQUIP-043', 'equipment', 'Equipment number corresponding tag is not part of the Tag Register (MTR).',                                      'Equipment tag not in MTR',                               'Critical'),
  ('EQUIP-044', 'equipment', 'Equipment number format does not include required plant code prefix.',                                           'Equipment number missing plant code prefix',              'Warning'),
  ('EQUIP-050', 'equipment', 'Mandatory fields are blank — equipment description, installation date and other required fields must be populated.', 'Mandatory equipment fields blank',                 'Critical'),
  ('EQUIP-051', 'equipment', 'Data missing or incomplete — use not applicable to indicate the review has been considered.',                     'General equipment data missing',                         'Warning'),
  ('EQUIP-052', 'equipment', 'Changes made in the Tag Register should also be reflected in the Equipment Register.',                           'Tag register changes not in equipment register',          'Warning'),
  ('EQUIP-053', 'equipment', 'Equipment in Equipment Register is not referenced in any Document-Equipment reference.',                         'Equipment has no document references',                   'Warning'),

-- =========================================================================
-- DOMAIN: EQUIPMENT_PROPERTY (11)
-- =========================================================================
  ('EQPROP-001', 'equipment_property', 'Equipment property values are not available for equipment that is part of the Equipment Register.',           'Equipment has no properties',                           'Warning'),
  ('EQPROP-002', 'equipment_property', 'Equipment class mapping against equipment is incorrect — expected properties per ISM are not provided.',    'Equipment class-property mapping mismatch',             'Critical'),
  ('EQPROP-003', 'equipment_property', 'Required properties per ISM standards are not included in the CIS submission.',                             'Required ISM equipment properties not submitted',        'Critical'),
  ('EQPROP-004', 'equipment_property', 'Equipment entries in the Property register are not part of the Equipment Register — may be void.',         'Equipment in property register not in equip register',  'Warning'),
  ('EQPROP-005', 'equipment_property', 'Equipment number is listed in Property Register but is not part of the Equipment Register.',                'Equipment property orphan record',                      'Warning'),
  ('EQPROP-006', 'equipment_property', 'Duplicate property entries exist for the same equipment number — each property should appear only once.',  'Duplicate equipment property entries',                  'Critical'),
  ('EQPROP-007', 'equipment_property', 'Property value is NA but UOM is populated — remove UOM when property value is NA.',                       'UOM populated when property value is NA for equipment', 'Warning'),
  ('EQPROP-008', 'equipment_property', 'Property value cells are blank — update or indicate not applicable.',                                     'Equipment property value blank',                        'Warning'),
  ('EQPROP-009', 'equipment_property', 'Equipment Number header is required in the Equipment Property Register instead of Tag Number.',            'Wrong header in equipment property register',           'Warning'),
  ('EQPROP-010', 'equipment_property', 'Property value is set to zero — if data is pending use TBC rather than zero.',                            'Equipment property value is zero',                      'Warning'),
  ('EQPROP-011', 'equipment_property', 'Equipment Property register contains tags instead of equipment numbers — use equipment numbers only.',     'Equipment property register has tag numbers',           'Critical'),

-- =========================================================================
-- DOMAIN: TAG_PROPERTY (15)
-- =========================================================================
  ('TPROP-001', 'tag_property', 'Tags in the Tag Register have no associated properties in the Tag Property register.',                          'Tag has no properties in property register',    'Warning'),
  ('TPROP-002', 'tag_property', 'Tag class mapping in the Property register differs from the class in the Tag Register — mismatch must be resolved.', 'Tag class-property mapping mismatch',       'Critical'),
  ('TPROP-003', 'tag_property', 'Tags referenced in the Property register are not available in the Tag Register (MTR) — may be void or deleted.',  'Property register tag not in MTR',             'Critical'),
  ('TPROP-004', 'tag_property', 'Required tag properties per ISM standards are not included in the CIS submission.',                             'Required ISM tag properties not submitted',     'Critical'),
  ('TPROP-005', 'tag_property', 'Tag property value is set to zero — if data is pending use TBC rather than zero.',                              'Tag property value is zero',                    'Warning'),
  ('TPROP-006', 'tag_property', 'Tag property value is NA but UOM is populated — remove UOM when property value is NA.',                         'UOM populated when tag property value is NA',   'Warning'),
  ('TPROP-007', 'tag_property', 'Duplicate property values exist in the tag property register — check and remove duplicates.',                    'Duplicate tag property entries',                'Critical'),
  ('TPROP-008', 'tag_property', 'Property code contains non-standard prefix — confirm whether it is approved and provide TQ reference if so.',   'Non-standard property code prefix',             'Warning'),
  ('TPROP-009', 'tag_property', 'Tag property register is incomplete — too few records submitted; resubmit complete register.',                   'Tag property register incomplete submission',   'Critical'),
  ('TPROP-010', 'tag_property', 'Plant Code column is missing from the tag property deliverable — add required column.',                          'Plant code column missing in tag property register', 'Critical'),
  ('TPROP-011', 'tag_property', 'Column header names must not be changed from the approved template.',                                           'Column header names changed in tag property',   'Warning'),
  ('TPROP-012', 'tag_property', 'Tag property value cells are blank or only partially populated — update in next revision.',                      'Tag property value blank or incomplete',         'Warning'),
  ('TPROP-013', 'tag_property', 'Cable cross sectional area contains unexpected characters — verify correctness.',                               'Cable CSA value contains unexpected characters', 'Warning'),
  ('TPROP-014', 'tag_property', 'UOM is missing for numeric property values — add UOM per ISM specification.',                                   'UOM missing for numeric tag property value',     'Warning'),
  ('TPROP-015', 'tag_property', 'Tag property value contains text in a numeric field — provide numeric value or use TBC.',                        'Non-numeric value in numeric tag property field','Warning'),

-- =========================================================================
-- DOMAIN: TAG_CONNECTION (9)
-- =========================================================================
  ('TCONN-001', 'tag_connection', 'Duplicate physical connection records exist — remove duplicate entries.',                                                 'Duplicate physical connection entries',          'Critical'),
  ('TCONN-002', 'tag_connection', 'From-Tag and To-Tag are the same — self-connection not permitted, check and correct.',                                    'From-tag equals to-tag',                        'Critical'),
  ('TCONN-003', 'tag_connection', 'Tags referenced in the From-Tag column are not part of the Tag Register.',                                                'From-tag not in MTR',                           'Critical'),
  ('TCONN-004', 'tag_connection', 'Physical connection scope is limited to pipes — expand to include cable and instrument connections per specification.',    'Physical connections scope too narrow',          'Warning'),
  ('TCONN-005', 'tag_connection', 'CSV template used is incorrect — required columns are PLANT_CODE, FROM_TAG_NAME, TO_TAG_NAME only.',                      'Wrong CSV template for tag connections',         'Warning'),
  ('TCONN-006', 'tag_connection', 'Tag class list for which physical connections are expected has not been provided — submit list to track progress.',        'Tag class list for connections not provided',    'Info'),
  ('TCONN-007', 'tag_connection', 'Physical connection record count is low — expand coverage beyond current tag classes as discussed.',                      'Low physical connection record count',           'Warning'),
  ('TCONN-008', 'tag_connection', 'To-Tag column contains tags not in the Tag Register — verify and correct.',                                               'To-tag not in MTR',                             'Critical'),
  ('TCONN-009', 'tag_connection', 'Physical connection register is empty — data has not been submitted.',                                                    'Physical connection register empty',             'Critical'),

-- =========================================================================
-- DOMAIN: TAG_CLASS_PROPERTY (3)
-- =========================================================================
  ('TCPROP-001', 'tag_class_property', 'Tag class property scope table — listed properties required per ISM are not provided in the CIS submission.', 'Tag class required properties not in CIS',    'Critical'),
  ('TCPROP-002', 'tag_class_property', 'Tag class properties submitted do not match the expected properties from the approved ISM schema.',            'Tag class properties not matching ISM schema', 'Critical'),
  ('TCPROP-003', 'tag_class_property', 'Tag class name in property scope table is blank — mandatory field.',                                          'Tag class name blank in property scope',       'Critical'),

-- =========================================================================
-- DOMAIN: DOCUMENT (32)
-- =========================================================================
  ('DOC-001', 'document', 'Tags in the Tag Register do not have document references in the Doc-Tag register.',                                 'Tags without document references',            'Warning'),
  ('DOC-002', 'document', 'Tags referenced in the Doc-Tag register are not available in the Tag Register (MTR).',                             'Doc-tag references tag not in MTR',           'Critical'),
  ('DOC-003', 'document', 'Documents in the Doc-Tag reference are not available in the Document Master register.',                            'Doc-tag document not in DocMaster',           'Critical'),
  ('DOC-004', 'document', 'Duplicate document records found in the register — remove duplicates.',                                            'Duplicate document records',                  'Critical'),
  ('DOC-005', 'document', 'Document numbers do not match records in the Document Management system (Assai) — check and correct.',             'Doc numbers not matching DMS',                'Critical'),
  ('DOC-006', 'document', 'Void or deleted tags should not have document references — remove references for deleted tags.',                   'Void tags have doc references',               'Warning'),
  ('DOC-007', 'document', 'Document template version used is outdated — resubmit using the current approved template.',                       'Outdated document template used',             'Warning'),
  ('DOC-008', 'document', 'Document title in the register does not match the title in the Document Management system.',                       'Doc title mismatch with DMS',                 'Warning'),
  ('DOC-009', 'document', 'Document revision in the register does not match the latest revision in the DMS.',                                'Doc revision mismatch with DMS',              'Warning'),
  ('DOC-010', 'document', 'Documents in the Doc-Area reference are not available in the Document Master register.',                          'Doc-area document not in DocMaster',          'Critical'),
  ('DOC-011', 'document', 'Document records in the Doc-Area reference do not have Area Code — populate or explain if not applicable.',       'Doc-area reference missing area code',        'Warning'),
  ('DOC-020', 'document', 'Documents in the Doc-Process Unit reference are not available in the Document Master register.',                  'Doc-PU document not in DocMaster',            'Critical'),
  ('DOC-021', 'document', 'Process unit code is missing in the Doc-Process Unit register records.',                                          'Doc-PU reference missing process unit code',  'Warning'),
  ('DOC-022', 'document', 'Process unit code in the Doc-Process Unit register does not match the Process Unit register.',                    'Doc-PU process unit not in register',         'Critical'),
  ('DOC-023', 'document', 'Plant code in the Doc-Process Unit register is not available in the Process Unit register — verify validity.',    'Doc-PU plant code not in register',           'Warning'),
  ('DOC-024', 'document', 'Incorrect CSV template used for Doc-PU register — required columns are DOCUMENT_NUMBER, PLANT_CODE, PROCESS_UNIT_CODE.', 'Wrong CSV template for doc-PU register', 'Warning'),
  ('DOC-030', 'document', 'Equipment items do not have any document reference — recommended to have Doc-Equipment reference.',               'Equipment without document reference',         'Warning'),
  ('DOC-031', 'document', 'Documents in the Doc-Equipment reference are not available in the Document Master register.',                     'Doc-equipment document not in DocMaster',     'Critical'),
  ('DOC-032', 'document', 'Equipment records in the Doc-Equipment reference are not part of the Equipment Register.',                        'Doc-equipment equipment not in register',     'Critical'),
  ('DOC-033', 'document', 'Doc-Equipment register references model parts instead of equipment numbers — correct entity type.',               'Doc-equipment references model parts',        'Warning'),
  ('DOC-040', 'document', 'Documents in the Doc-PO reference are not available in the Document Master register.',                           'Doc-PO document not in DocMaster',            'Critical'),
  ('DOC-041', 'document', 'PO code in the Doc-PO reference does not exist in the Purchase Order register.',                                 'Doc-PO code not in PO register',              'Critical'),
  ('DOC-042', 'document', 'PO code is void — void PO codes should not be referenced in this register.',                                     'Void PO code in doc-PO reference',            'Warning'),
  ('DOC-043', 'document', 'Company name is missing or not matching the Company register for PO references.',                                'Company name not in company register for PO', 'Warning'),
  ('DOC-050', 'document', 'Documents in the Doc-Plant reference are not available in the Document Master register.',                         'Doc-plant document not in DocMaster',         'Critical'),
  ('DOC-051', 'document', 'Documents in the Doc-Site reference are not available in the Document Master register.',                         'Doc-site document not in DocMaster',          'Critical'),
  ('DOC-052', 'document', 'Site code must be standardised — use the approved site code format.',                                            'Site code format incorrect',                  'Warning'),
  ('DOC-060', 'document', 'Documents are not available in the Document Management system or are in NYI (Not Yet Issued) status.',           'Document not in DMS or NYI',                  'Critical'),
  ('DOC-061', 'document', 'Contractor is asked to reference associated loop diagrams against each tag.',                                     'Loop diagram reference missing',              'Warning'),
  ('DOC-062', 'document', 'Contractor is asked to reference associated layout drawings against each tag.',                                   'Layout drawing reference missing',            'Warning'),
  ('DOC-063', 'document', 'Contractor is asked to reference associated P&ID or schematics against each tag.',                               'PID schematic reference missing',             'Warning'),
  ('DOC-064', 'document', 'Document is submitted as a combined file — individual documents should be referenced separately.',                'Combined document file submitted',            'Info'),

-- =========================================================================
-- DOMAIN: PURCHASE_ORDER (7)
-- =========================================================================
  ('PO-001', 'purchase_order', 'PO code referenced in the Tag Register is not available or not matching the Purchase Order register.',  'PO code not in PO register',               'Critical'),
  ('PO-002', 'purchase_order', 'PO date is missing — mandatory field in the Purchase Order register.',                                   'PO date missing',                          'Critical'),
  ('PO-003', 'purchase_order', 'Physical tags do not have PO code — non-mandatory but recommended for all physical items.',              'PO code missing for physical tags',        'Warning'),
  ('PO-004', 'purchase_order', 'PO receiver company name is missing — check and correct.',                                              'PO receiver company missing',              'Warning'),
  ('PO-005', 'purchase_order', 'PO description values contain special characters or commas not permitted in this field.',               'PO description contains invalid characters','Warning'),
  ('PO-006', 'purchase_order', 'PO code is listed as void in the Purchase Order register — remove or replace reference.',               'PO code is void',                          'Critical'),
  ('PO-007', 'purchase_order', 'Multiple PO codes reference the same equipment — verify and retain only the correct association.',      'Multiple PO codes for same equipment',     'Warning'),

-- =========================================================================
-- DOMAIN: PROCESS_UNIT (6)
-- =========================================================================
  ('PU-001', 'process_unit', 'Multiple process unit codes are used for the same system — consolidate or clarify scope.',                           'Multiple process unit codes for same system',   'Warning'),
  ('PU-002', 'process_unit', 'Plant code used in the Process Unit register is not part of the standard plant code list — verify.',                 'Process unit plant code not in standard list',  'Warning'),
  ('PU-003', 'process_unit', 'Formatting is inconsistent — use either all caps or first-letter capitals consistently throughout register.',        'Process unit formatting inconsistent',           'Info'),
  ('PU-004', 'process_unit', 'Mandatory data is missing or incomplete — populate all required process unit fields.',                               'Process unit mandatory data missing',            'Critical'),
  ('PU-005', 'process_unit', 'Process unit description is blank — populate the description field.',                                                'Process unit description blank',                'Warning'),
  ('PU-006', 'process_unit', 'Process unit hierarchy (parent/child) is not consistent with the Area register structure.',                          'Process unit hierarchy inconsistent with area',  'Warning'),

-- =========================================================================
-- DOMAIN: MODEL_PART (3)
-- =========================================================================
  ('MPART-001', 'model_part', 'Model part description is not yet defined — required for data loading in downstream system.',  'Model part description not defined',    'Critical'),
  ('MPART-002', 'model_part', 'Model part referenced in Equipment Register does not exist in the Model Part register.',       'Model part not in model part register', 'Critical'),
  ('MPART-003', 'model_part', 'Model part number contains special characters not permitted — correct the format.',            'Model part number invalid characters',  'Warning'),

-- =========================================================================
-- DOMAIN: OTHER (8)
-- =========================================================================
  ('OTHER-001', 'other', 'Company name is not available for physical equipment tags — recommended to populate.',                                                     'Company name missing for tags',              'Warning'),
  ('OTHER-002', 'other', 'Company name contains double spaces — remove extra spaces from the company register.',                                                    'Company name has double spaces',             'Warning'),
  ('OTHER-003', 'other', 'Company name referenced in MTR is not available in the Company register.',                                                                'Company name not in company register',       'Critical'),
  ('OTHER-004', 'other', 'Company register values contain commas or special characters not permitted — remove invalid characters.',                                 'Company name contains invalid characters',    'Warning'),
  ('OTHER-005', 'other', 'Significant number of entries remain TBA or TBC — include all available information in this revision.',                                   'Many TBA or TBC entries in register',        'Warning'),
  ('OTHER-006', 'other', 'Document numbers are not available in the DMS or are still in NYI status.',                                                              'Documents not in DMS or in NYI status',      'Critical'),
  ('OTHER-007', 'other', 'Submission uses wrong file template — resubmit using the approved CIS template.',                                                        'Wrong CIS submission template used',          'Critical'),
  ('OTHER-008', 'other', 'General comment — data quality is improving but outstanding items from previous revision still require attention.',                       'Outstanding items from previous revision',    'Info')

) AS v(category_code, domain, template_text, short_template_text, severity);

COMMIT;

-- =============================================================================
-- Verification (run manually after applying)
-- =============================================================================
/*
SELECT domain, severity, COUNT(*) AS n
FROM audit_core.crs_comment_template
WHERE category_code IS NOT NULL
GROUP BY domain, severity
ORDER BY domain, severity;
-- Expected: 179 rows total, 12 domains

SELECT COUNT(*) AS total
FROM audit_core.crs_comment_template
WHERE category_code IS NOT NULL;
-- Expected: 179
*/
