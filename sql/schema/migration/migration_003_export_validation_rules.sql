/*
Purpose: Create audit_core.export_validation_rule for configurable pre-export
         data quality checks. Rules are stored as DSL expressions interpreted
         at runtime by export_validation.py. Supports two modes:
           - built-in (is_builtin=true): auto-fix applied during export generation
           - full scan: results stored in audit_core.validation_result.
         Also creates audit_core.validation_result for storing full scan output
         and sync-time violations (e.g. TAG_NAME_CHANGED).
         Seeds 21 base rules + 21 extended rules (null/UoM/referential/topological).
Params:  None.
Output:  2 new tables + 2 indexes + 42 seed rows.
Errors:  IF NOT EXISTS guards make all DDL idempotent — safe to re-run.
Changes: 2026-03-12 — Initial implementation.
*/

-- ---------------------------------------------------------------------------
-- Table: audit_core.export_validation_rule
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_core.export_validation_rule (
    id              UUID    NOT NULL DEFAULT gen_random_uuid(),
    rule_code       TEXT    NOT NULL,
    scope           TEXT    NOT NULL,          -- 'common' | 'tag' | 'equipment' | 'sync'
    object_field    TEXT    NULL,              -- specific column this rule targets, NULL for multi-column rules
    description     TEXT    NULL,
    rule_expression TEXT    NOT NULL,          -- DSL violation condition (rows matching = violators)
    fix_expression  TEXT    NULL,              -- DSL fix applied in built-in mode; NULL = check-only
    is_builtin      BOOLEAN NOT NULL DEFAULT false,   -- run automatically during export generation
    is_blocking     BOOLEAN NOT NULL DEFAULT false,   -- block export if no fix and violation found
    severity        TEXT    NOT NULL DEFAULT 'Warning',  -- 'Critical' | 'Warning' | 'Info'
    object_status   TEXT    NOT NULL DEFAULT 'Active',
    CONSTRAINT export_validation_rule_pkey     PRIMARY KEY (id),
    CONSTRAINT export_validation_rule_code_key UNIQUE (rule_code)
);

-- ---------------------------------------------------------------------------
-- Table: audit_core.validation_result
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_core.validation_result (
    id               UUID      NOT NULL DEFAULT gen_random_uuid(),
    session_id       UUID      NOT NULL,
    run_time         TIMESTAMP NOT NULL DEFAULT now(),
    rule_code        TEXT      NOT NULL,
    scope            TEXT      NOT NULL,
    severity         TEXT      NOT NULL DEFAULT 'Warning',
    object_type      TEXT      NULL,     -- 'tag' | 'document' | 'property_value' etc.
    object_id        UUID      NULL,     -- id of the violating record
    object_name      TEXT      NULL,     -- human-readable identifier (tag_name, doc_number)
    violation_detail TEXT      NULL,
    column_name      TEXT      NULL,     -- column where violation was found
    original_value   TEXT      NULL,     -- raw violating value
    is_resolved      BOOLEAN   NOT NULL DEFAULT false,
    CONSTRAINT validation_result_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_val_result_session
    ON audit_core.validation_result (session_id);

CREATE INDEX IF NOT EXISTS idx_val_result_object_id
    ON audit_core.validation_result (object_id);

-- ---------------------------------------------------------------------------
-- Seed: initial validation rules
-- DSL rule_expression describes violation condition (matching rows are violators).
-- DSL fix_expression describes auto-fix applied in built-in export mode.
-- ---------------------------------------------------------------------------
INSERT INTO audit_core.export_validation_rule
    (rule_code, scope, description, rule_expression, fix_expression, is_builtin, is_blocking, severity)
VALUES
    -- Common rules — apply to all EIS export registers
    (
        'NO_COMMA_IN_VALUES',
        'common',
        'No commas in text fields — commas break CSV column parsing',
        '* contains ","',
        'replace "," ";"',
        true, true, 'Warning'
    ),
    (
        'NO_NAN_STRINGS',
        'common',
        'No literal nan/NaN strings in any cell — pandas export artefact',
        '* icontains "nan"',
        'replace_nan',
        true, true, 'Warning'
    ),
    (
        'NO_INVALID_CHARS',
        'common',
        'No < characters in text fields',
        '* contains "<"',
        'remove_char "<"',
        true, false, 'Warning'
    ),
    (
        'DECIMAL_DOT_SEPARATOR',
        'common',
        'Decimal values must use . not , as separator (e.g. JDA-0,75" is invalid)',
        '* matches_regex "\\d+,\\d+"',
        NULL,
        false, false, 'Warning'
    ),
    (
        'COMPANY_NAME_MAX_30',
        'common',
        'COMPANY_NAME must not exceed 30 characters per EIS specification',
        'COMPANY_NAME max_length 30',
        'truncate 30',
        true, false, 'Warning'
    ),
    (
        'TAG_DESC_MAX_255',
        'common',
        'TAG_DESCRIPTION must not exceed 255 characters (120 recommended for Aveva sync)',
        'TAG_DESCRIPTION max_length 255',
        'truncate 255',
        true, false, 'Warning'
    ),
    -- Tag register rules
    (
        'AREA_FK_RESOLVED',
        'tag',
        'If area_code_raw is set the area FK must resolve — unresolved area excluded from export',
        'area_code_raw not_null AND area_code is_null',
        NULL,
        false, false, 'Warning'
    ),
    -- Equipment register rules
    -- Note: equip_no IS NOT NULL is already enforced by the export SQL WHERE clause,
    -- so this rule only fires in full scan mode against unfiltered data.
    (
        'EQUIP_NO_NOT_NULL',
        'equipment',
        'EQUIPMENT_NUMBER is null or empty — equipment rows require a number (full scan only)',
        'EQUIPMENT_NUMBER is_null',
        NULL,
        false, false, 'Critical'
    ),
    -- Sync-time rules (detected in code, not evaluated via DSL)
    (
        'TAG_NAME_CHANGED',
        'sync',
        'tag_name changed for an existing source_id — prohibited in source system',
        'source_id exists AND tag_name differs from stored value',
        NULL,
        false, false, 'Critical'
    ),
    -- Encoding artefact repair — common, built-in, auto-fixed by clean_engineering_text()
    (
        'ENCODING_ARTEFACTS',
        'common',
        'UTF-8 mojibake and Win-1252 byte leakage (Â², â€œ etc.) — auto-repaired by clean_engineering_text',
        '* has_encoding_artefacts',
        'encoding_repair',
        true, false, 'Info'
    ),
    -- FK resolution rules — tag register scope
    -- Pattern: raw field set but resolved output column is NULL (JOIN did not match)
    (
        'CLASS_FK_RESOLVED',
        'tag',
        'TAG_CLASS_NAME is NULL but tag_class_raw is set — class code not found in ontology_core.class',
        'tag_class_raw not_null AND tag_class_name is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'PROCESS_UNIT_FK_RESOLVED',
        'tag',
        'PROCESS_UNIT_CODE is NULL but process_unit_raw is set — unit not found in reference_core.process_unit',
        'process_unit_raw not_null AND process_unit_code is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'PLANT_FK_RESOLVED',
        'common',
        'PLANT_CODE is NULL but plant_raw is set — plant not found in reference_core.plant',
        'plant_raw not_null AND plant_code is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'DESIGN_CO_FK_RESOLVED',
        'tag',
        'DESIGNED_BY_COMPANY_NAME is NULL but design_company_name_raw is set — company not found in reference_core.company',
        'design_company_name_raw not_null AND designed_by_company_name is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'PO_FK_RESOLVED',
        'tag',
        'PO_CODE is NULL but po_code_raw is set — purchase order not found in reference_core.purchase_order',
        'po_code_raw not_null AND po_code is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'ARTICLE_FK_RESOLVED',
        'tag',
        'REQUISITION_CODE is NULL but article_code_raw is set — article not found in reference_core.article',
        'article_code_raw not_null AND requisition_code is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'PARENT_TAG_FK_RESOLVED',
        'tag',
        'PARENT_TAG_NAME is empty but parent_tag_raw is set — parent tag not found in project_core.tag',
        'parent_tag_raw not_null AND parent_tag_name is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'DISCIPLINE_FK_RESOLVED',
        'tag',
        'discipline_code_raw is set but discipline_id is NULL — discipline not found in reference_core.discipline (full scan only)',
        'discipline_code_raw not_null AND discipline_code_raw not_null',
        NULL,
        false, false, 'Warning'
    ),
    -- FK resolution rules — equipment register scope
    (
        'MODEL_PART_FK_RESOLVED',
        'equipment',
        'MODEL_PART_NAME is NULL but model_part_raw is set — model part not found in reference_core.model_part',
        'model_part_raw not_null AND model_part_name is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'MANUFACTURER_FK_RESOLVED',
        'equipment',
        'MANUFACTURER_COMPANY_NAME is NULL but manufacturer_company_raw is set — company not found in reference_core.company',
        'manufacturer_company_raw not_null AND manufacturer_company_name is_null',
        NULL,
        true, true, 'Warning'
    ),
    (
        'VENDOR_FK_RESOLVED',
        'equipment',
        'VENDOR_COMPANY_NAME is NULL but vendor_company_raw is set — company not found in reference_core.company',
        'vendor_company_raw not_null AND vendor_company_name is_null',
        NULL,
        true, true, 'Warning'
    ),

    -- -----------------------------------------------------------------------
    -- Section 2: Null / NA / TBC / zero-value logic
    -- -----------------------------------------------------------------------

    -- Mandatory field blank — any column marked Mandatory in the RDL must not be empty.
    -- Rule expression is intentionally descriptive: actual enforcement requires per-field
    -- configuration (object_field column) matched against the RDL mandatory list.
    (
        'MANDATORY_NOT_EMPTY',
        'common',
        'RDL-mandatory fields must not be physically empty — use TBC if value is unknown, NA if not applicable',
        'mandatory_field is_null',
        NULL,
        false, false, 'Critical'
    ),

    -- Literal "0" in any text field — rejected by customer except for real physical zeros.
    -- False-positive-prone as wildcard; refine to specific columns when known.
    (
        'NO_INFORMATIONAL_ZERO',
        'common',
        'Value "0" in a text property field is rejected unless it represents a real physical zero (e.g. lower design temperature, normal operating pressure)',
        '* matches_regex "^0$"',
        NULL,
        false, false, 'Warning'
    ),

    -- Heater wattage must be a positive number — "0" wattage is physically meaningless.
    (
        'HEATER_WATTAGE_POSITIVE',
        'equipment',
        'WATTAGE must be a positive value — zero wattage is not accepted for heaters',
        'WATTAGE matches_regex "^0$"',
        NULL,
        false, false, 'Critical'
    ),

    -- MANUFACTURER_SERIAL_NUMBER must be filled — TBC for unknown, "BULK MATERIAL" for bulk items.
    -- NA is prohibited per approved TQ: bulk/piping/supports use "BULK MATERIAL", not NA.
    (
        'SERIAL_NO_NOT_EMPTY',
        'equipment',
        'MANUFACTURER_SERIAL_NUMBER must not be empty — use TBC if serial is unknown, BULK MATERIAL for bulk/piping/supports',
        'MANUFACTURER_SERIAL_NUMBER is_null',
        NULL,
        false, false, 'Critical'
    ),

    -- NA is explicitly prohibited for serial numbers on bulk material — must say "BULK MATERIAL".
    (
        'SERIAL_NO_NO_NA_FOR_BULK',
        'equipment',
        'MANUFACTURER_SERIAL_NUMBER must not contain NA for bulk material items — approved phrase is "BULK MATERIAL" per TQ',
        'MANUFACTURER_SERIAL_NUMBER icontains "NA"',
        NULL,
        false, false, 'Warning'
    ),

    -- -----------------------------------------------------------------------
    -- Section 3: Unit of Measure logic
    -- -----------------------------------------------------------------------

    -- When PROPERTY_VALUE is NA, UOM column must be blank — customer rejects "NA / mm" pairs.
    (
        'UOM_BLANK_WHEN_VALUE_NA',
        'common',
        'PROPERTY_VALUE_UOM must be empty when PROPERTY_VALUE is NA — customer rejects non-blank UOM alongside NA value',
        'PROPERTY_VALUE icontains "NA" AND PROPERTY_VALUE_UOM not_null',
        NULL,
        false, false, 'Warning'
    ),

    -- When PROPERTY_VALUE is TBC, UOM column must be blank.
    (
        'UOM_BLANK_WHEN_VALUE_TBC',
        'common',
        'PROPERTY_VALUE_UOM must be empty when PROPERTY_VALUE is TBC — customer rejects non-blank UOM alongside TBC value',
        'PROPERTY_VALUE icontains "TBC" AND PROPERTY_VALUE_UOM not_null',
        NULL,
        false, false, 'Warning'
    ),

    -- UOM for area must use Aveva syntax "mm2", not "square millimeters" (Shell style).
    (
        'AREA_UNIT_AVEVA_FORMAT',
        'common',
        'Area unit must use Aveva format "mm2" — "square millimeters" / "square mm" are rejected',
        'PROPERTY_VALUE_UOM icontains "square millimeter"',
        NULL,
        false, false, 'Warning'
    ),

    -- Combined value+UOM in a single cell (e.g. "490mm") — value and UOM must be in separate columns.
    (
        'VALUE_UOM_COMBINED_IN_CELL',
        'common',
        'PROPERTY_VALUE must not contain embedded UOM — e.g. "490mm" is invalid; use Value=490 and UOM=mm in separate columns',
        'PROPERTY_VALUE matches_regex "\\d+(mm|cm|m|kg|bar|kPa|°C|kW|kVA|rpm|Hz|V|A|l/s|m3/h)"',
        NULL,
        false, false, 'Warning'
    ),

    -- Count properties must have an empty UOM — "pcs", "units" etc. are rejected.
    (
        'COUNT_PROPERTY_UOM_EMPTY',
        'common',
        'PROPERTY_VALUE_UOM must be empty for count/dimensionless properties — remove "pcs", "units" etc.',
        'PROPERTY_VALUE_UOM icontains "pcs"',
        NULL,
        false, false, 'Warning'
    ),

    -- -----------------------------------------------------------------------
    -- Section 4: Cross-file referential integrity
    -- Note: these rules cannot be evaluated via the DSL engine against a single
    -- DataFrame. rule_expression is intentionally descriptive text — runtime
    -- enforcement requires dedicated custom checks outside apply_builtin_fixes().
    -- -----------------------------------------------------------------------

    -- Any tag referenced in TAG_PROPERTY_VALUE_CSV / DOC_REF / PHYSICAL_CONNECTION must
    -- exist in TAG_CSV with object_status = 'Active'.
    (
        'TAG_ACTIVE_IN_MASTER',
        'tag',
        'Every tag referenced in property-value, document-ref, or physical-connection files must exist in TAG_CSV with status ACTIVE',
        'cross_file: referenced_tag_name NOT IN tag_csv WHERE object_status = ''Active''',
        NULL,
        false, false, 'Critical'
    ),

    -- Document numbers used in any reference matrix must exist in DOCUMENT_MASTER_CSV.
    (
        'DOC_EXISTS_IN_MDR',
        'common',
        'Every document number used in reference matrices must exist in DOCUMENT_MASTER_CSV — documents with status NYI (Not Yet Issued) are not allowed',
        'cross_file: referenced_doc_number NOT IN document_master_csv OR doc_status = ''NYI''',
        NULL,
        false, false, 'Critical'
    ),

    -- PO codes with -VOID suffix are explicitly prohibited.
    (
        'PO_CODE_NOT_VOID',
        'common',
        'PO_CODE must not contain the -VOID suffix — voided purchase orders cannot be referenced',
        'PO_CODE icontains "-VOID"',
        NULL,
        false, false, 'Critical'
    ),

    -- All PO codes linked to tags or documents must exist in PURCHASE_ORDER_CSV.
    (
        'PO_CODE_EXISTS_IN_MASTER',
        'common',
        'PO_CODE must exist in reference_core.purchase_order — unresolved PO codes are not accepted',
        'cross_file: po_code NOT IN purchase_order_csv',
        NULL,
        false, false, 'Warning'
    ),

    -- Equipment number must follow strict naming: tag ESB1_BUSCABLE6_0202 → equip Equip_ESB1_BUSCABLE6_0202.
    -- Underscores must not be replaced with spaces.
    (
        'EQUIP_TAG_PREFIX_MATCH',
        'equipment',
        'EQUIPMENT_NUMBER must match the tag name with "Equip_" prefix — underscore-to-space substitution is prohibited',
        'cross_file: equipment_number != concat(''Equip_'', tag_name)',
        NULL,
        false, false, 'Warning'
    ),

    -- Tags with VOID or DELETED status must not appear in any cross-reference matrix.
    (
        'VOID_DELETED_EXCLUDED_FROM_XREF',
        'tag',
        'Tags with status VOID or DELETED must be excluded from all cross-reference matrices (doc-to-tag, physical connections etc.)',
        'cross_file: tag_name IN xref_matrix WHERE object_status IN (''VOID'',''DELETED'')',
        NULL,
        false, false, 'Critical'
    ),

    -- -----------------------------------------------------------------------
    -- Section 5: Topological and classification checks
    -- -----------------------------------------------------------------------

    -- PROCESS_UNIT_CODE is strictly mandatory for all tags.
    (
        'PROCESS_UNIT_MANDATORY',
        'tag',
        'PROCESS_UNIT_CODE is mandatory for all tags — must not be empty',
        'PROCESS_UNIT_CODE is_null',
        NULL,
        false, false, 'Critical'
    ),

    -- AREA_CODE is strongly expected (auto-rejected for SWA infrastructure tags without it).
    (
        'AREA_CODE_EXPECTED',
        'tag',
        'AREA_CODE is strongly expected — tags without AREA_CODE are auto-rejected for Shearwater (SWA) infrastructure scope',
        'AREA_CODE is_null',
        NULL,
        false, false, 'Warning'
    ),

    -- Equipment class must exactly match ISM reference dictionary (no free-text variants).
    -- Cannot validate via DSL alone — requires lookup against ontology_core.class.
    (
        'CLASS_MATCHES_RDL',
        'tag',
        'TAG_CLASS_NAME must exactly match an entry in the ISM reference dictionary — free-text variants (e.g. "analyser instrument" vs "analyser element") are rejected',
        'cross_file: tag_class_name NOT IN ontology_core.class WHERE object_status = ''Active''',
        NULL,
        false, false, 'Critical'
    ),

    -- Abstract/parent classes (e.g. "Pump") must not be used — must use concrete leaf class.
    (
        'NO_ABSTRACT_CLASS',
        'tag',
        'Abstract or parent equipment classes (e.g. "Pump") must not be used — use concrete subclasses (e.g. "Centrifugal Pump") so that the correct property set is inherited',
        'cross_file: tag_class_name IN ontology_core.class WHERE is_abstract = true',
        NULL,
        false, false, 'Critical'
    ),

    -- Each active physical tag must have at least one document link (P&ID, Datasheet etc.).
    (
        'TAG_MIN_ONE_DOCUMENT',
        'tag',
        'Each active physical tag must have at least one document link in DOC_REF_TO_TAG — absence of documents is a red validation error',
        'cross_file: tag_id NOT IN mapping.tag_document',
        NULL,
        false, false, 'Critical'
    ),

    -- Duplicate rows in the physical connection matrix are prohibited.
    (
        'PHYSICAL_CONNECTION_NO_DUPLICATE',
        'tag',
        'Duplicate rows in TAG_PHYSICAL_CONNECTION_CSV (same FROM_TAG / TO_TAG pair) are prohibited',
        'cross_file: duplicate (from_tag, to_tag) in tag_physical_connection_csv',
        NULL,
        false, false, 'Warning'
    ),

    -- FROM_TAG and TO_TAG in physical connections must reference existing active tags.
    (
        'PHYSICAL_CONNECTION_TAGS_VALID',
        'tag',
        'FROM_TAG and TO_TAG in physical connection matrix must reference existing active tags — orphan connection references are not accepted',
        'cross_file: from_tag OR to_tag NOT IN tag_csv WHERE object_status = ''Active''',
        NULL,
        false, false, 'Critical'
    )

ON CONFLICT (rule_code) DO NOTHING;
