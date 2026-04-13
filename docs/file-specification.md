# EIS File Specification Reference — Complete Input & Output Guide

> Comprehensive specification for both source (input XLSX) and report (output CSV) files in Jackdaw EDW.
> All files accessed via `./data/` symlinks pointing to `/mnt/shared-data/`.
> Read source XLSX with: `pd.read_excel(path, dtype=str, na_filter=False)`

---

## Part 1: Source Files (Input XLSX) — Complete Inventory

Only 3 XLSX files are actively ingested as source data in Jackdaw EDW:

1. **`MDR.xlsx`** — Master Document Register (18,654 documents)
2. **`Master-Reference-Data.xlsx`** — Consolidated reference tables (site, plant, area, company, PO, discipline, etc.)
3. **`JDAW-PT-D-JA-7880-00001_A05.xlsx`** — CFIHOS RDL Ontology (tag classes, equipment classes, properties, UOM)

All source files are read with **`dtype=str, na_filter=False`** to preserve literal "NA" strings and prevent unintended type conversions.

### 1.1 Master Document Register (MDR.xlsx)

#### `MDR.xlsx` — Master Document Register
18,654 rows. Target: `project_core.document`. Primary source for all document metadata.

**Sheet**: `Sheet1` (standard single-sheet format)

| Source Column | DB Field | Type | Constraint | Notes |
|---|---|---|---|---|
| `DOCUMENT_NUMBER` | `doc_number` | TEXT | **UNIQUE** | Unique document identifier (e.g., `JDAW-KVE-E-IN-2347-00002-174`) |
| `DOCUMENT_TITLE` | `title` | TEXT | | Full descriptive title |
| `REVISION_CODE` | `rev` | TEXT | | Revision identifier (e.g., `C03`, `Z01`, `A35`) |
| `REVISION_DATE` | `rev_date` | DATE | format: `MM/DD/YYYY` | use `to_dt(val, format='%m/%d/%Y')` |
| `DOCUMENT_STATUS` | `status` | TEXT | e.g. `AFC`, `ASB`, `IFA` | Engineering lifecycle status |
| `REVISION_COMMENT` | `rev_comment` | TEXT | | Revision notes or change log |
| `REVISION_AUTHOR` | `rev_author` | TEXT | | Responsible person/team |
| `SITE_CODE` | → `site_id` FK | UUID | | Links to `reference_core.site` |
| `PLANT_CODE` | → `plant_id` FK | UUID | always `JDA` | Links to `reference_core.plant` |
| `PROJECT_CODE` | → `project_id` FK | UUID | e.g. `JDAW` | Links to `reference_core.project` |
| `AREA_CODE` | → `area_id` FK | UUID | | Links to `reference_core.area` |
| `DOCUMENT_TYPE_CODE` | `doc_type_code` | TEXT | e.g. `2347`, `B01`, `K05` | Document classification |
| `PO_CODE` | → `po_id` FK | UUID | | Links to `reference_core.purchase_order`; use `mapping.document_po` for N:M |
| `COMPANY_NAME` | → `company_id` FK | UUID | | Issuing company; links to `reference_core.company` |
| `MDR` | `mdr_flag` | BOOLEAN | **default: False** | Extract from `MDR` column (True/False); if empty/NA → False |
| `CREATED_DATE` | `created_date` | TIMESTAMP | | Document creation timestamp |
| `LAST_MODIFICATION_DATE` | `modified_date` | TIMESTAMP | | Last update timestamp |
| `DOCUMENT_TO_TAG_COUNT` | (informational) | INT | | Not stored; used for validation only |

**Processing Rules**:
- **MDR Flag**: Parse `MDR` column as boolean (case-insensitive: "True", "YES", "1" → True; else False)
- **Row Hashing**: Compute MD5 hash of all columns except timestamps to detect changes (SCD tracking)
- **Status Filter**: Only import rows with `object_status = 'Active'` at export time
- **N:M Document-PO Mapping**: Store in `mapping.document_po` (one document can link to multiple POs)

---

### 1.2 Tag Register (MTR-dataset.xlsx)

#### `MTR-dataset.xlsx` (or `205-Tag-register.xlsx` in EIS convention)
~18,000–25,000 rows. Target: `project_core.tag` + all related FK lookups.

**Sheet**: Varies (check for headers; may be named `Sheet1`, `Tag Register`, or derived)

| Source Column | DB Field | Type | Constraint | Notes |
|---|---|---|---|---|
| `TAG_NAME` | `tag_name` | TEXT | **UNIQUE** | Unique business key (e.g., `01-LIT-101`, `ESB1_BUSCABLE6_0202`) |
| `TAG_STATUS` | `tag_status` | TEXT | e.g. `Active`, `Void`, `ASB` | Engineering lifecycle status |
| `TAG_CLASS_NAME` | → `class_id` FK | UUID | | Link to `ontology_core.class`; store raw in `class_code_raw` |
| `TAG_DESCRIPTION` | `description` | TEXT | max 255 | Free-form technical description |
| `PARENT_TAG_NAME` | → `parent_tag_id` FK | UUID | | Self-join: resolve in second pass after all tags inserted |
| `AREA_CODE` | → `area_id` FK | UUID | | Link to `reference_core.area`; store raw in `area_code_raw` |
| `PROCESS_UNIT_CODE` | → `process_unit_id` FK | UUID | e.g. `1`=WELLS, `86`=HVAC | Link to `reference_core.process_unit`; store raw in `unit_code_raw` |
| `DISCIPLINE_CODE` | → `discipline_id` FK | UUID | | Link to discipline lookup; store raw in `discipline_code_raw` |
| `PO_CODE` | → `po_id` FK | UUID | | Link to `reference_core.purchase_order`; store raw in `po_code_raw` |
| `DESIGNED_BY_COMPANY_NAME` | → `design_company_id` FK | UUID | | Link to `reference_core.company` (design contractor) |
| `MANUFACTURER_COMPANY_NAME` | → `article_id` FK | UUID | | Link via `reference_core.article.manufacturer_id`; store raw in `mfr_raw` |
| `VENDOR_COMPANY_NAME` | → `vendor_id` FK | UUID | | Link to `reference_core.company` (supplier); store raw in `vendor_raw` |
| `COMPANY_NAME` | → `company_id` FK | UUID | | Manufacturing/operational company; store raw in `company_raw` |
| `ARTICLE_CODE` | → `article_id` FK | UUID | | Part/product code from vendor; store raw in `article_raw` |
| `TAG_DOC` | → `mapping.tag_document` | N:M | space-separated codes | Split on whitespace; create one mapping row per document code |
| `SAFETY_CRITICAL_ITEM_GROUP` | → `mapping.tag_sece` | N:M | space-separated codes | **⚠️ Column has trailing space in name** — use `row.get('SAFETY_CRITICAL_ITEM _GROUP')` |
| `SAFETY_CRITICAL_ITEM` | `safety_critical_flag` | BOOLEAN | Y/N or T/F | Safety classification |
| `PRODUCTION_CRITICAL_ITEM` | `production_critical_flag` | BOOLEAN | Y/N or T/F | Production criticality |
| `SAFETY_CRITICAL_ITEM_REASON_AWARDED` | `safety_reason` | TEXT | | Explanation for safety classification |
| `FROM_TAG` / `TO_TAG` | → `mapping.tag_connection` | N:M | cable connections | Create one row per (FROM_TAG, TO_TAG) pair |
| `MC_PACKAGE_CODE` | `mc_package_code` | TEXT | | Maintenance code package |
| `EX CLASS` | `ex_class` | TEXT | **⚠️ Column has internal space** — use `row.get('EX CLASS')` | Explosive atmosphere classification |
| `IP_GRADE` | `ip_grade` | TEXT | e.g. `IP65`, `IP67` | Ingress protection rating |
| `MANUFACTURER_SERIAL_NUMBER` | `mfr_serial_number` | TEXT | | Manufacturer-assigned serial |
| `INSTALLATION_DATE` | `installed_date` | TIMESTAMP | parse via `to_dt()` | Installation timestamp |
| `PLANT_CODE` | → `plant_id` FK | UUID | always `JDA` | Link to `reference_core.plant` |
| (implicit) | `row_hash` | TEXT | computed | MD5 hash for SCD change tracking |
| (implicit) | `sync_status` | TEXT | `New|Updated|Unchanged|Deleted` | SCD status from flow |
| (implicit) | `sync_timestamp` | TIMESTAMP | `now()` | Last sync time |

**Processing Rules**:
- **dtype=str, na_filter=False**: Preserve all string types; never auto-convert to NaN
- **Column Name Quirks**:
  - `SAFETY_CRITICAL_ITEM _GROUP` has **trailing space** — must use exact string
  - `EX CLASS` has **internal space** — must use exact string
- **Multi-value Fields**: `TAG_DOC` and `SAFETY_CRITICAL_ITEM_GROUP` are space-separated; split each and create separate mapping rows
- **Two-Phase Ingestion**:
  - **Phase 1**: Insert all tags, resolving all FKs except `parent_tag_id` (which may not be in DB yet)
  - **Phase 2**: Run separate `sync_tag_hierarchy` task to resolve parent-child relationships
- **FK Fallback**: If FK lookup fails, store the raw value in `_raw` column and leave the `_id` column NULL; record as warning/error in audit
- **Row Hashing**: Compute MD5 of all content columns (exclude timestamps, sync_status) to detect changes

---

### 1.3 Ontology & Reference Data (Master-Reference-Data.xlsx)

#### `Master-Reference-Data.xlsx` — Consolidated Reference Tables
This file contains ALL static reference data in separate sheets. Target: `reference_core.*` and ontology seeds.

**Sheets and Targets**:

| Sheet | Key Columns | Target Table | Rows | Purpose |
|---|---|---|---|---|
| `site` | `code`, `name`, `object_status` | `reference_core.site` | ~5 | Geographic sites (e.g., JD=Jackdaw, sw=Shearwater) |
| `plant` | `code`, `name`, `site_code`, `object_status` | `reference_core.plant` | ~5 | Production plants (e.g., JDA=Jackdaw plant) |
| `project` | `code`, `name`, `site_code`, `object_status` | `reference_core.project` | ~2 | Projects (e.g., JDAW=Jackdaw project) |
| `area` | `code`, `name`, `main_area_code`, `plant_code`, `object_status` | `reference_core.area` | ~205 | Area/zone hierarchy (e.g., F100, G100) |
| `sece` | `code`, `name`, `object_status` | `reference_core.sece` | ~35 | Safety/Environment/Criticality/Equipment codes (DS01, ER01, etc.) |
| `process_unit` | `code`, `name`, `plant_code`, `object_status` | `reference_core.process_unit` | ~37 | Process unit breakdown (e.g., 01=WELLS, 02=MANIFOLD) |
| `article` | `code`, `name`, `definition`, `article_type`, `manufacturer_company_name_raw`, `model_part_code_raw`, `object_status` | `reference_core.article` | ~4,960 | Vendor parts/equipment specifications (SKU catalog) |
| `company` | `code`, `name`, `address`, `town_city`, `country_code`, `is_manufacturer`, `is_supplier`, `object_status` | `reference_core.company` | ~660 | Companies (manufacturers, suppliers, contractors) |
| `purchase_order` | `code`, `name`, `definition`, `po_date`, `issuer_company_raw`, `receiver_company_raw`, `object_status` | `reference_core.purchase_order` | ~1,730 | Purchase orders (procurement documents) |
| `po_package` | `code`, `name`, `object_status` | `reference_core.po_package` | ~250 | PO groupings/packages (e.g., BL775=PIPE SUPPORTS) |
| `discipline` | `code`, `name`, `code_internal`, `object_status` | `reference_core.discipline` | ~10 | Engineering disciplines (EA=Electrical, MX=Mechanical, IN=Instrumentation) |
| `model_part` | `code`, `name`, `definition`, `manuf_company_raw`, `object_status` | `reference_core.model_part` | ~1,275 | Component models and parts (technical catalog) |
| `summary` | (metadata table) | (informational) | ~70 | Field listing for verification |

**Processing Rules**:
- All sheets have **headers in Row 1** (standard format)
- **FK columns with `_raw` suffix**: Store original text value; FK resolution via lookup (e.g., `manufacturer_company_name_raw` → lookup in company table)
- **`object_status` column**: Always `Active` in this reference file; used to filter at export time
- **Hierarchy**: `area.main_area_code` creates self-join parent-child relationship
- Read with: `pd.read_excel(file, sheet_name='sheet_name', dtype=str, na_filter=False)`

---

### 1.4 CFIHOS/RDL Ontology Master (JDAW-PT-D-JA-7880-00001_A05.xlsx)

#### `JDAW-PT-D-JA-7880-00001_A05.xlsx` — RDL (Reference Data Library)
This file contains CFIHOS ontology definition. Populates `ontology_core.*`. Version: v1.4, Date: 2019-10-17.

| Sheet | Key Columns | Target Table | Rows | Purpose |
|---|---|---|---|---|
| `Tag class` | Tag Class ID, Name, Definition, Description, Notes | `ontology_core.class` | ~300 | **Functional** tag classifications per CFIHOS (e.g., Pump, Valve, Transmitter) |
| `Tag class properties` | Tag Class Code, Property Code, Property Name, Is Mandatory | `ontology_core.class_property` + `mapping.class_property` | ~2,230 | **Functional**: property definitions required for each tag class |
| `Equipment class` | Equipment Class ID, Name, Definition, Description | `ontology_core.class` | ~330 | **Physical** equipment classifications (e.g., Rotating Machinery, Static Equipment) |
| `Equipment class props` | Equipment Class Code, Property Code, Property Name, Is Mandatory | `ontology_core.class_property` + `mapping.class_property` | ~3,650 | **Physical**: property definitions required for each equipment class |
| `Property` | Property ID, Name, Definition, Data Type, Unit of Measure Dimension, Picklist Name | `ontology_core.property` | ~800 | Property/attribute master (base definitions) |
| `Property picklist` | Picklist ID, Picklist Name, Description | `ontology_core.validation_rule` | ~200 | Enumeration sets (for constrained properties) |
| `Property picklist value` | Picklist ID, Picklist Item Code, Picklist Item Name | `ontology_core.validation_rule.validation_value` | ~5,340 | Individual enum values; generates regex `(val1\|val2\|val3)` |
| `Unit of measure` | UOM Code, UOM Name, UOM Symbol, Dimension Code | `ontology_core.uom` | ~138 | Individual UOM (bar, Pa, mm, kg, °C, kW, etc.) |
| `Unit of measure dimension` | Dimension Code, Dimension Name | `ontology_core.uom_group` | ~55 | UOM groupings (Pressure, Temperature, Length, Mass, Power, etc.) |

**Important Processing Notes**:

1. **Headers are NOT in Row 1**: Use dynamic header detection:
   - Search for row containing first data header (e.g., "Tag Class", "Property ID")
   - All metadata rows above headers (Document Version, Date Issued, etc.) should be skipped
   
2. **Class Concept Merging**:
   - If class appears in **both** `Tag class` AND `Equipment class`: `concept = 'Functional Physical'`
   - If only in `Tag class`: `concept = 'Functional'`
   - If only in `Equipment class`: `concept = 'Physical'`
   - Store as single row in `ontology_core.class` with deduplicated logic

3. **Class-Property Mapping** (conceptual):
   - For each (TagClass, Property) pair from `Tag class properties`: create mapping with `mapping_concept = 'Functional'`
   - For each (EquipmentClass, Property) pair from `Equipment class props`: create mapping with `mapping_concept = 'Physical'`
   - If same property maps to both Tag and Equipment class: merge row with `mapping_concept = 'Functional Physical'`
   - Store in `ontology_core.class_property` (or `mapping.class_property` depending on schema)

4. **Property Validation**:
   - If Property has non-empty `Picklist Name` (column G): Create `validation_rule` with:
     - `validation_type = 'picklist'`
     - `validation_value = regex` generated from all values in `Property picklist value` sheet
     - Example: For CFIHOS-50000003, extract all enum values → `(dry service|wet service)`
   - Link property → validation_rule via FK `property.validation_rule_id`

5. **UOM Mapping**:
   - Create `ontology_core.uom_group` rows (Pressure, Length, etc.)
   - Create `ontology_core.uom` rows (bar, Pa, mm, kg, etc.)
   - Each UOM links to its dimension group via `uom.uom_group_id`
   - Link property → UOM dimension via `property.uom_group_id` (or property → uom directly if needed)

6. **Read Pattern**:
   ```python
   def read_rdl_sheet(file, sheet_name, header_keyword):
       """Dynamically locate headers in RDL sheets."""
       df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None, dtype=str)
       # Find row containing header_keyword
       header_row = None
       for idx, row in df_raw.iterrows():
           if header_keyword in str(row.values):
               header_row = idx
               break
       if header_row is not None:
           df = pd.read_excel(file, sheet_name=sheet_name, 
                             header=header_row, dtype=str, na_filter=False)
           return df.dropna(how='all')
       return None
   ```

---

## Part 2: Report Files (Output CSV)

All export CSVs use standard naming: `JDAW-KVE-E-JA-6944-00001-{SEQ}-{REVISION}.CSV`

- **Encoding**: UTF-8 with BOM (`utf-8-sig`) — mandatory for Excel compatibility
- **Delimiter**: comma (`,`)
- **Quote**: double-quote (`"`)
- **Null**: empty string (not `NULL`, `NA`, or `#N/A`)
- **Dates**: ISO 8601 format `YYYY-MM-DD`
- **Timestamps**: `YYYY-MM-DD HH:MM:SS`
- **Booleans**: Y/N or True/False (per export spec)

---

### 2.1 Spatial Reference Exports

#### EIS Seq 203 — Area Register
**File**: `JDAW-KVE-E-JA-6944-00001-017-{revision}.CSV`
**Flow**: `export_area_register_flow`
**Source**: `reference_core.area` WHERE `object_status = 'Active'`

| Column | Source | Notes |
|---|---|---|
| `PLANT_CODE` | `plant.code` | always `JDA` |
| `AREA_CODE` | `area.code` | unique per plant |
| `AREA_NAME` | `area.name` | |
| `MAIN_AREA_CODE` | `parent_area.code` (self-join) | hierarchy parent; empty if NULL |
| `PLANT_REF` | computed `'PLANT-' \|\| plant.code` | `PLANT-JDA` |

---

#### EIS Seq 204 — Process Unit Register
**File**: `JDAW-KVE-E-JA-6944-00001-018-{revision}.CSV`
**Flow**: `export_process_unit_flow`
**Source**: `reference_core.process_unit` WHERE `object_status = 'Active'`

| Column | Source | Notes |
|---|---|---|
| `PLANT_CODE` | `plant.code` | always `JDA` |
| `PROCESS_UNIT_CODE` | `process_unit.code` | integer identifier |
| `PROCESS_UNIT_NAME` | `process_unit.name` | |
| `COUNT_OF_TAGS` | SELECT COUNT(*) FROM `project_core.tag` | informational |

---

### 2.2 Primary Project Data Exports

#### **EIS Seq 205 — Tag Register (Primary Export)**
**File**: `JDAW-KVE-E-JA-6944-00001-003-{revision}.CSV`
**Flow**: `export_tag_register_flow`
**Source**: `project_core.tag` JOIN reference tables WHERE `object_status = 'Active'`

**Column order** (strict per JDAW-PT-D-JA-7739-00003):
```
PLANT_CODE · TAG_NAME · PARENT_TAG_NAME · AREA_CODE · PROCESS_UNIT_CODE ·
TAG_CLASS_NAME · TAG_STATUS · REQUISITION_CODE · DESIGNED_BY_COMPANY_NAME ·
COMPANY_NAME · PO_CODE · PRODUCTION_CRITICAL_ITEM · SAFETY_CRITICAL_ITEM ·
SAFETY_CRITICAL_ITEM_GROUP · SAFETY_CRITICAL_ITEM_REASON_AWARDED ·
TAG_DESCRIPTION · ACTION_STATUS · ACTION_DATE
```

| Column | Source | Notes |
|---|---|---|
| `PLANT_CODE` | `plant.code` | always `JDA` |
| `TAG_NAME` | `tag.tag_name` | unique identifier |
| `PARENT_TAG_NAME` | `parent_tag.tag_name` (self-join) | empty string if NULL (never literal 'unset') |
| `AREA_CODE` | `area.code` | FK resolve; empty if unmatched |
| `PROCESS_UNIT_CODE` | `process_unit.code` | FK resolve; empty if unmatched |
| `TAG_CLASS_NAME` | `tag_class.class_name` | FK resolve |
| `TAG_STATUS` | `tag.tag_status` | e.g. `Active`, `Retired`, `Void` |
| `REQUISITION_CODE` | `COALESCE(art.name, art.code)` via `reference_core.article` | article name; falls back to code |
| `DESIGNED_BY_COMPANY_NAME` | `company.name` (via `tag.design_company_id`) | FK resolve |
| `COMPANY_NAME` | `company.name` (via `po.issuer_id → company`) | issuing company of linked PO |
| `PO_CODE` | `COALESCE(po.name, po.code)` | PO name first, falls back to code |
| `PRODUCTION_CRITICAL_ITEM` | `tag.production_critical_item` | Boolean (Y/N) |
| `SAFETY_CRITICAL_ITEM` | `tag.safety_critical_item` | Boolean (Y/N) |
| `SAFETY_CRITICAL_ITEM_GROUP` | aggregated correlated subquery | via `mapping.tag_sece`; space-separated codes |
| `SAFETY_CRITICAL_ITEM_REASON_AWARDED` | `tag.safety_critical_item_reason_awarded` | free text |
| `TAG_DESCRIPTION` | `tag.description` | |
| `ACTION_STATUS` | `tag.sync_status` (renamed by transform) | SCD status: `New`, `Updated`, `No Changes`, `Deleted` |
| `ACTION_DATE` | MAX(`audit_core.tag_status_history.sync_timestamp`) | correlated subquery; formatted `YYYY-MM-DD` |

**SCD Tracking**: All tag changes logged to `project_core.tag_history` (Status = New/Updated/Deleted).

---

#### EIS Seq 206 — Equipment Register
**File**: `JDAW-KVE-E-JA-6944-00001-004-{revision}.CSV`
**Flow**: `export_equipment_register_flow`
**Source**: `project_core.tag` WHERE `object_status = 'Active'` AND `equip_no IS NOT NULL`

| Column | Source | Notes |
|---|---|---|
| `EQUIPMENT_NUMBER` | `tag.equip_no` | equipment identifier |
| `PLANT_CODE` | `plant.code` via `tag.plant_id` | LEFT JOIN; empty if NULL |
| `TAG_NAME` | `tag.tag_name` | linked tag name |
| `EQUIPMENT_CLASS_NAME` | `class.name` via `tag.class_id` | LEFT JOIN; empty if FK NULL |
| `MANUFACTURER_COMPANY_NAME` | `company.name` via `tag.manufacturer_id` | LEFT JOIN; empty if FK NULL |
| `MODEL_PART_NAME` | `model_part.name` via `tag.model_id` | LEFT JOIN; empty if FK NULL |
| `MANUFACTURER_SERIAL_NUMBER` | `tag.serial_no` | |
| `PURCHASE_DATE` | `purchase_order.po_date` via `tag.po_id` | TEXT; DD.MM.YYYY format |
| `VENDOR_COMPANY_NAME` | `company.name` via `tag.vendor_id` | LEFT JOIN; empty if FK NULL |
| `INSTALLATION_DATE` | `tag.install_date` | |
| `STARTUP_DATE` | hardcoded `'NA'` | not available in source |
| `PRICE` | hardcoded `'NA'` | not available in source |
| `WARRANTY_END_DATE` | hardcoded `'NA'` | not available in source |
| `PART_OF` | `po_package.code` via `po.package_id` | LEFT JOIN chain; empty if unresolved |
| `TECHIDENTNO` | hardcoded `'NA'` | not available in source |
| `ALIAS` | hardcoded `'NA'` | not available in source |
| `EQUIPMENT_DESCRIPTION` | `tag.description` | |
| `ACTION_DATE` | MAX(`audit_core.tag_status_history.sync_timestamp`) | correlated subquery; formatted `YYYY-MM-DD` |

---

#### EIS Seq 209 — Model Part Register
**File**: `JDAW-KVE-E-JA-6944-00001-005-{revision}.CSV`
**Flow**: `export_model_part_flow`
**Source**: `project_core.tag` INNER JOIN `reference_core.model_part` ON `tag.model_id = model_part.id`
WHERE `tag.object_status = 'Active'` AND `tag.tag_status NOT IN ('VOID', '')`;
DISTINCT ON `model_part.id` to deduplicate multi-tag references.

| Column | Source | Notes |
|---|---|---|
| `MANUFACTURER_COMPANY_NAME` | `company.name` via `model_part.manufacturer_id` | LEFT JOIN; empty if FK NULL |
| `MODEL_PART_NAME` | `model_part.name` | |
| `MODEL_DESCRIPTION` | `model_part.definition` | empty string if NULL |
| `EQUIPMENT_CLASS_NAME` | `class.name` via `tag.class_id` | LEFT JOIN; empty if FK NULL |

---

### 2.3 Property & Classification Exports

#### EIS Seq 303 — Tag Property Values (EAV)
**File**: `JDAW-KVE-E-JA-6944-00001-010-{revision}.CSV`
**Flow**: `export_tag_properties_flow`
**Source**: `project_core.property_value` JOIN `ontology_core.class_property`
WHERE `pv.object_status = 'Active'`
  AND `cp.mapping_concept ILIKE '%Functional%'`
  AND `cp.mapping_concept NOT ILIKE '%common%'`

**Routing logic**: строки из `project_core.property_value` направляются в этот файл если их маппинг (`ontology_core.class_property.mapping_concept`) содержит подстроку `Functional` (без учёта регистра). Строки с `mapping_concept` содержащим `common` исключены из обоих property-регистров. Строки с составным `'Functional Physical'` попадают как в seq 303, так и в seq 301.

| Column | Source | Notes |
|---|---|---|
| `PLANT_CODE` | `plant.code` | via `tag.plant_id` LEFT JOIN |
| `TAG_NAME` | `tag.tag_name` | INNER JOIN (обязателен) |
| `PROPERTY_NAME` | `ontology_core.property.name` | human-readable property name |
| `PROPERTY_VALUE` | `property_value.property_value` | actual value |
| `PROPERTY_VALUE_UOM` | resolved via `ontology_core.uom_alias` → `uom.symbol_ascii`; lowercase | canonical unit symbol |

---

#### EIS Seq 301 — Equipment Property Values (EAV)
**File**: `JDAW-KVE-E-JA-6944-00001-011-{revision}.CSV`
**Flow**: `export_equipment_properties_flow`
**Source**: `project_core.property_value` JOIN `ontology_core.class_property`
WHERE `pv.object_status = 'Active'`
  AND `cp.mapping_concept ILIKE '%Physical%'`
  AND `cp.mapping_concept NOT ILIKE '%common%'`

**Routing logic**: строки из `project_core.property_value` направляются в этот файл если их маппинг содержит подстроку `Physical`. Логика зеркальна seq 303. Строки с `'Functional Physical'` дублируются в оба файла.

| Column | Source | Notes |
|---|---|---|
| `PLANT_CODE` | `plant.code` | via `tag.plant_id` LEFT JOIN |
| `EQUIPMENT_NUMBER` | `tag.equip_no` (alias from `project_core.tag`) | format: `Equip_<tag_name>` |
| `PROPERTY_NAME` | `ontology_core.property.name` | human-readable property name |
| `PROPERTY_VALUE` | `property_value.property_value` | actual value |
| `PROPERTY_VALUE_UOM` | resolved via `ontology_core.uom_alias` → `uom.symbol_ascii`; lowercase | canonical unit symbol |

---

#### EIS Seq 307 — Tag Class Properties (file 009)
**File**: `JDAW-KVE-E-JA-6944-00001-009-{revision}.CSV`
**Flow**: `export_schema_flow` (unified entry) / `export_tag_class_properties_flow` (standalone) — `etl/flows/export_schema_deploy.py`

**Source table**: `project_core.property_value`
**Scope**: DISTINCT class × property pairs where:
- `ontology_core.class.concept ILIKE '%Functional%'`
- `project_core.property_value.mapping_concept_raw ILIKE '%Functional%'`
- `project_core.property_value.object_status != 'inactive'` (case-insensitive)

**Status**: Active — exported in EIS full package (`export_eis_data_deploy.py`, step 11)

| Column | Source | Notes |
|---|---|---|
| `TAG_CLASS_NAME` | `ontology_core.class.name` | e.g., Pressure Transmitter, Valve |
| `TAG_PROPERTY_NAME` | `ontology_core.property.name` | human-readable property name |

---

#### Equipment Class Properties (file 009b — stub, not deployed)
**File**: `JDAW-KVE-E-JA-6944-00001-009b-{revision}.CSV`
**Flow**: `export_equipment_class_properties_flow` (`etl/flows/export_schema_deploy.py`)

**Source table**: `project_core.property_value`
**Scope**: DISTINCT class × property pairs where:
- `ontology_core.class.concept ILIKE '%Physical%'`
- `project_core.property_value.mapping_concept_raw ILIKE '%Physical%'`
- `project_core.property_value.object_status != 'inactive'` (case-insensitive)

**Status**: Stub — not deployed. Enable by passing `export_schemas=["tag","equipment"]` to `export_schema_flow`.

| Column | Source | Notes |
|---|---|---|
| `EQUIPMENT_CLASS_NAME` | `ontology_core.class.name` | e.g., Rotating Machinery, Static Equipment |
| `EQUIPMENT_PROPERTY_NAME` | `ontology_core.property.name` | human-readable property name |

---

### 2.4 Physical Connections & References

#### EIS Seq 212 — Tag Physical Connections
**File**: `JDAW-KVE-E-JA-6944-00001-006-{revision}.CSV`
**Flow**: `export_tag_connections_flow`
**Source**: `project_core.tag` WHERE `object_status = 'Active'` AND `tag_status NOT IN ('VOID', 'Future')` AND (`from_tag_raw` OR `to_tag_raw` non-empty)

| Column | Source | Notes |
|---|---|---|
| `PLANT_CODE` | `plant.code` via `tag.plant_id` | always `JDA` |
| `FROM_TAG_NAME` | `tag.from_tag_raw` | exported verbatim — may be open-end label or zone comment |
| `TO_TAG_NAME` | `tag.to_tag_raw` | exported verbatim — may be open-end label or zone comment |

---

#### EIS Seq 214 — Purchase Order Register
**File**: `JDAW-KVE-E-JA-6944-00001-008-{revision}.CSV`
**Flow**: `export_purchase_order_flow`
**Source**: `reference_core.purchase_order` WHERE `object_status = 'Active'`

| Column | Source | Notes |
|---|---|---|
| `COMPANY_NAME` | `company.name` via `purchase_order.issuer_id` | LEFT JOIN; empty if FK NULL |
| `PO_CODE` | `purchase_order.name` | PO name (hyphenated format e.g. `JA-EE047-1000`) |
| `PO_DESCRIPTION` | `purchase_order.definition` | free-text description |
| `PO_RECEIVER_COMPANY_NAME` | `company.name` via `purchase_order.receiver_id` | LEFT JOIN; empty if FK NULL |
| `PO_DATE` | `purchase_order.po_date` | TEXT; format DD.MM.YYYY (stored verbatim, no reformat) |

---

### 2.5 Document Cross-Reference Exports

**Flow**: `export_document_crossref_flow` (`etl/flows/export_document_crossref.py`) — runs all 8 registers; each also available as standalone flow.

**Common document filter gate (all 8 exports)**:
- `document.object_status = 'Active'`
- `document.mdr_flag = TRUE`
- `document.status IS NOT NULL` AND `UPPER(document.status) != 'CAN'`

**Common tag filter (seq 410, 411, 412, 413, 414)**:
- `tag.object_status = 'Active'`
- `UPPER(COALESCE(tag.tag_status, '')) NOT IN ('VOID', '')`

**FK resolution**: unresolved FKs → empty string in CSV (no raw values exported).

---

#### EIS Seq 408 — Document References to Site
**File**: `JDAW-KVE-E-JA-6944-00001-024-{revision}.CSV`
**Flow**: `export_doc_to_site_flow`
**Source**: `project_core.document` → `plant.site_id` → `reference_core.site` (LEFT JOIN chain)

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `SITE_CODE` | `site.code` via `document.plant_id → plant.site_id` | LEFT JOIN; empty if unresolved |

---

#### EIS Seq 409 — Document References to Plant
**File**: `JDAW-KVE-E-JA-6944-00001-023-{revision}.CSV`
**Flow**: `export_doc_to_plant_flow`
**Source**: `project_core.document` LEFT JOIN `reference_core.plant`

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `PLANT_CODE` | `plant.code` via `document.plant_id` | LEFT JOIN; empty if unresolved |

---

#### EIS Seq 410 — Document References to Process Unit
**File**: `JDAW-KVE-E-JA-6944-00001-018-{revision}.CSV`
**Flow**: `export_doc_to_process_unit_flow`
**Source**: `mapping.tag_document` → `project_core.tag` → `reference_core.process_unit`; DISTINCT pairs

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `PLANT_CODE` | `plant.code` via `tag.plant_id` | LEFT JOIN; empty if unresolved; DISTINCT |
| `PROCESS_UNIT_CODE` | `process_unit.code` via `tag.process_unit_id` | LEFT JOIN; empty if FK NULL; DISTINCT |

---

#### EIS Seq 411 — Document References to Area
**File**: `JDAW-KVE-E-JA-6944-00001-017-{revision}.CSV`
**Flow**: `export_doc_to_area_flow`
**Source**: `mapping.tag_document` → `project_core.tag` → `reference_core.area`; DISTINCT pairs

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `AREA_CODE` | `area.code` via `tag.area_id` | LEFT JOIN; empty if FK NULL; DISTINCT |

---

#### EIS Seq 412 — Document References to Tag
**File**: `JDAW-KVE-E-JA-6944-00001-016-{revision}.CSV`
**Flow**: `export_doc_to_tag_flow`
**Source**: `mapping.tag_document` WHERE `mapping_status = 'Active'`

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `PLANT_CODE` | `plant.code` via `tag.plant_id` | LEFT JOIN; empty if unresolved |
| `TAG_NAME` | `tag.tag_name` | |

---

#### EIS Seq 413 — Document References to Equipment
**File**: `JDAW-KVE-E-JA-6944-00001-019-{revision}.CSV`
**Flow**: `export_doc_to_equipment_flow`
**Source**: `mapping.tag_document` → `project_core.tag` WHERE `class.concept ILIKE '%Physical%'` AND `tag.equip_no IS NOT NULL`

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `PLANT_CODE` | `plant.code` via `tag.plant_id` | LEFT JOIN; empty if unresolved |
| `EQUIPMENT_NUMBER` | `tag.equip_no` | Only tags with Physical class (INNER JOIN on `ontology_core.class`) |

---

#### EIS Seq 414 — Document References to Model Part
**File**: `JDAW-KVE-E-JA-6944-00001-020-{revision}.CSV`
**Flow**: `export_doc_to_model_part_flow`
**Source**: `mapping.tag_document` → `project_core.tag` → `reference_core.model_part` (via `tag.model_id`); DISTINCT pairs

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `PLANT_CODE` | `plant.code` via `tag.plant_id` | LEFT JOIN; empty if unresolved |
| `MODEL_PART_CODE` | `model_part.code` via `tag.model_id` | INNER JOIN; DISTINCT |

---

#### EIS Seq 420 — Document References to Purchase Order
**File**: `JDAW-KVE-E-JA-6944-00001-022-{revision}.CSV`
**Flow**: `export_doc_to_po_flow`
**Source**: `mapping.document_po` WHERE `mapping_status = 'Active'`; `purchase_order.object_status = 'Active'`

| Column | Source | Notes |
|---|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` | |
| `REVISION_CODE` | `document.rev` | revision code (e.g. `C03`, `A35`) |
| `PO_CODE` | `purchase_order.name` via `mapping.document_po.po_id` | hyphenated format e.g. `JA-EE047-1000` |
| `PLANT_CODE` | `plant.code` via `document.plant_id` | LEFT JOIN; empty if unresolved |
| `COMPANY_NAME` | `company.name` via `purchase_order.issuer_id` | issuing company name |

---

## JDAW EIS Code Matrix

Unified mapping between EIS sequence numbers, input sources, and output codes:

| EIS Seq | Source XLSX | Output CSV Code | Output Filename | Semantic Content | Data Layer |
|---|---|---|---|---|---|
| 203 | 203-Area.xlsx | `-017-` | Area.CSV | Area spatial hierarchy | reference |
| 204 | 204-ProcessUnit.xlsx | `-018-` | ProcessUnit.CSV | Process unit breakdown | reference |
| 205 | 205-Tag-register.xlsx | `-003-` | Tag-register.CSV | **Tag master data** | **project** |
| 206 | 206-Equipment-register.xlsx | `-004-` | Equipment.CSV | Equipment assets | project |
| 209 | 209-Model-Part-register.xlsx | `-005-` | ModelPart.CSV | Component catalog | reference |
| 212 | 212-Tag Physical Connection.xlsx | `-006-` | TagConnections.CSV | Signal cables/wiring | mapping |
| 214 | 214-Purchase-order.xlsx | `-008-` | PurchaseOrder.CSV | Purchase orders | reference |
| 301 | 301-Equipment-property-value.xlsx | `-011-` | EquipmentProperties.CSV | Equipment EAV | project |
| 303 | 303-Tag-property-value.xlsx | `-010-` | TagProperties.CSV | Tag EAV (CFIHOS) | project |
| 307 | 307-Tag-class-properties.xlsx | `-009-` | TagClassProperties.CSV | Class property schema | ontology |
| 408 | 408-Document_References_to_Site.xlsx | `-024-` | DocToSite.CSV | Doc↔Site links | mapping |
| 409 | 409-Document_References_to_PlantCode.xlsx | `-023-` | DocToPlant.CSV | Doc↔Plant links | mapping |
| 410 | 410-Document_References_to_ProcessUnit.xlsx | `-018-` | DocToProcessUnit.CSV | Doc↔ProcessUnit links | mapping |
| 411 | 411-Document_References_to_Area.xlsx | `-017-` | DocToArea.CSV | Doc↔Area links | mapping |
| 412 | 412-Document_References_to_Tag.xlsx | `-016-` | DocToTag.CSV | Doc↔Tag links | mapping |
| 413 | 413-Document_References_to_Equipment.xlsx | `-019-` | DocToEquipment.CSV | Doc↔Equipment links | mapping |
| 414 | 414-Document_References_to_ModelPart.xlsx | `-020-` | DocToModelPart.CSV | Doc↔ModelPart links | mapping |
| 420 | 420-Document_References_to_PurchaseOrder.xlsx | `-022-` | DocToPurchaseOrder.CSV | Doc↔PO links | mapping |

---

## Export Invariants (All EIS Outputs)

- **Encoding**: always `utf-8-sig` (UTF-8 with BOM for Excel)
- **Sanitization**: `sanitize_dataframe()` called unconditionally before write
- **Status filter**: `object_status = 'Active'` enforced at both SQL and Python layers
- **File extension**: uppercase `.CSV` not `.csv`
- **Audit record**: every export run writes to `audit_core.sync_run_stats` with revision metadata
- **Revision pattern**: `{doc_revision}` = document revision code (e.g., `A36`, `B01`)
- **Null handling**: SQL NULLs → empty string in CSV; literal 'NA' → preserved as-is (dtype=str, na_filter=False)
- **FK resolution**: unresolved FKs result in empty column value; original raw value always stored in `_raw` column for audit
- **Validation**: Built-in rules applied via `apply_builtin_fixes()` (see `etl/tasks/export_validation.py`)

---

## Python Code Mapping (from eis-csv-creator.py)

```python
doc_revision = "A36"
eis_registers = {
    "203-Area.xlsx": "JDAW-KVE-E-JA-6944-00001-017-{0}.CSV",
    "204-ProcessUnit.xlsx": "JDAW-KVE-E-JA-6944-00001-018-{0}.CSV",
    "205-Tag-register.xlsx": "JDAW-KVE-E-JA-6944-00001-003-{0}.CSV",
    "206-Equipment-register.xlsx": "JDAW-KVE-E-JA-6944-00001-004-{0}.CSV",
    "209-Model-Part-register.xlsx": "JDAW-KVE-E-JA-6944-00001-005-{0}.CSV",
    "212-Tag Physical Connection.xlsx": "JDAW-KVE-E-JA-6944-00001-006-{0}.CSV",
    "214-Purchase-order.xlsx": "JDAW-KVE-E-JA-6944-00001-008-{0}.CSV",
    "301-Equipment-property-value.xlsx": "JDAW-KVE-E-JA-6944-00001-011-{0}.CSV",
    "303-Tag-property-value.xlsx": "JDAW-KVE-E-JA-6944-00001-010-{0}.CSV",
    "307-Tag-class-properties.xlsx": "JDAW-KVE-E-JA-6944-00001-009-{0}.CSV",
    "408-Document_References_to_Site.xlsx": "JDAW-KVE-E-JA-6944-00001-024-{0}.CSV",
    "409-Document_References_to_PlantCode.xlsx": "JDAW-KVE-E-JA-6944-00001-023-{0}.CSV",
    "410-Document_References_to_ProcessUnit.xlsx": "JDAW-KVE-E-JA-6944-00001-018-{0}.CSV",
    "411-Document_References_to_Area.xlsx": "JDAW-KVE-E-JA-6944-00001-017-{0}.CSV",
    "412-Document_References_to_Tag.xlsx": "JDAW-KVE-E-JA-6944-00001-016-{0}.CSV",
    "413-Document_References_to_Equipment.xlsx": "JDAW-KVE-E-JA-6944-00001-019-{0}.CSV",
    "414-Document_References_to_ModelPart.xlsx": "JDAW-KVE-E-JA-6944-00001-020-{0}.CSV",
    "420-Document_References_to_PurchaseOrder.xlsx": "JDAW-KVE-E-JA-6944-00001-022-{0}.CSV",
}
```

---

## Reference Documentation

- **Architecture**: `@docs/architecture.md`
- **Infrastructure**: `@docs/infrastructure.md`
- **Database Schema**: `@docs/schema.sql`

