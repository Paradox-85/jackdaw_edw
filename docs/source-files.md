# Source Files Reference (EIS Inputs)

> Load when needed: `@docs/source-files.md`
> All files accessed via `./data/current/` symlinks → `/mnt/shared-data/ram-user/Jackdaw/`
> Read with: `pd.read_excel(path, dtype=str, na_filter=False)`

---

## Ontology / Reference Data

### `JDAW-PT-D-JA-7880-00001_A05.xlsx` — RDL Master Ontology
Populates `ontology_core` and `reference_core`. Used by `seed_ontology` flow.

| Sheet | Key Columns | Target Table |
|---|---|---|
| `Tag class` | `Tag Class ID`, `Name` | `ontology_core.class` |
| `Equipment class` | `Equipment Class ID`, `Name` | `ontology_core.class` |
| `Property` | `Property ID`, `Name`, `Dimension ID` | `ontology_core.property` |
| `Unit of measure dimension` | `Unique ID`, `Dimension Name` | `ontology_core.uom_group` |
| `Unit of measure` | `Id`, `Name`, `Dimension ID` | `ontology_core.uom` |
| `Property picklist` | `Id`, `Name` | `ontology_core.validation_rule` |
| `Property picklist value ` | `Picklist ID`, `Picklist Item Name` | builds regex for `validation_rule.validation_value` |

**Note**: Use `read_sheet_smart(file, sheet, header_keyword)` — headers are not always row 0.

---

## Tag Register

### `001-TagRegister.xlsx` (or equivalent) — Master Tag List
**Sheet**: varies (check header row). ~18,000+ rows in MTR-dataset.
Target: `project_core.tag` (primary UPSERT via `sync_tag_data` flow).

Key source columns → DB mapping:
| Source Column | DB Field | Notes |
|---|---|---|
| `TAG_NAME` | `tag_name` UNIQUE | PK business key |
| `TAG_STATUS` | `tag_status` | e.g. `ASB`, `AFC`, `ACTIVE` |
| `TAG_CLASS_NAME` | `class_id` FK + `cls_raw` | FK via `class_lookup` |
| `PARENT_TAG_NAME` | `parent_tag_id` FK | resolved in second pass |
| `AREA_CODE` | `area_id` FK + `area_raw` | |
| `PROCESS_UNIT_CODE` | `process_unit_id` FK + `unit_raw` | |
| `DISCIPLINE_CODE` | `discipline_id` FK + `disc_raw` | |
| `PO_CODE` | `po_id` FK + `po_raw` | |
| `DESIGNED_BY_COMPANY_NAME` | `design_company_id` FK + `dco_raw` | |
| `MANUFACTURER_COMPANY_NAME` | `article_id` FK + `mfr_raw` | via `article_lookup` |
| `VENDOR_COMPANY_NAME` | FK company + `v_raw` | |
| `ARTICLE_CODE` | `article_id` FK + `art_raw` | |
| `TAG_DOC` | → `mapping.tag_document` | space-separated doc codes |
| `SAFETY_CRITICAL_ITEM _GROUP` | → `mapping.tag_sece` | space-separated SECE codes (note: trailing space in column name) |
| `SAFETY_CRITICAL_ITEM` | `safety_critical_item` | direct text field |
| `PRODUCTION_CRITICAL_ITEM` | `production_critical_item` | direct text field |
| `FROM_TAG` / `TO_TAG` | `from_tag_id` / `to_tag_id` FK | cable connections |
| `MC_PACKAGE_CODE` | `mc_package_code` | direct field |
| `EX CLASS` / `IP_GRADE` | direct fields | note space in `EX CLASS` |
| `MANUFACTURER_SERIAL_NUMBER` | `manufacturer_serial_number` | |
| `INSTALLATION_DATE` etc. | timestamps via `to_dt()` | |
| `PLANT_CODE` | `plant_id` FK | always `JDA` |

---

## Document Registers

### `MDR.xlsx` — Master Document Register
18,654 rows. Target: `project_core.document`.

Key columns:
| Column | Notes |
|---|---|
| `DOCUMENT_NUMBER` | Unique PK (e.g. `JDAW-KVE-E-IN-2347-00002-174`) |
| `DOCUMENT_TITLE` | |
| `REVISION_CODE` | e.g. `C03`, `Z01`, `A35` |
| `REVISION_DATE` | date string — use `to_dt()` |
| `DOCUMENT_STATUS` | e.g. `AFC`, `ASB`, `IFA` |
| `SITE_CODE` / `PLANT_CODE` / `PROJECT_CODE` | FK lookups |
| `AREA_CODE` | FK reference_core.area |
| `DOCUMENT_TYPE_CODE` | e.g. `2347`, `B01`, `K05` |
| `PO_CODE` | FK reference_core.purchase_order |
| `COMPANY_NAME` | FK reference_core.company |
| `MDR` | Boolean — True = in MDR subset |
| `DOCUMENT_TO_TAG_COUNT` | informational only |

### `MTR-dataset.xlsx` — Material/Tag Register (wide format)
Very wide rows (100+ columns). Contains full tag attributes including EAV properties.
Used for tag sync AND property value population.
Key identifier columns: `TAG_NAME`, `PLANT_CODE`, `TAG_STATUS`, `TAG_CLASS_NAME`.
CFIHOS properties identified by `CFIHOS-XXXXXXXX` codes.
Template source: `AKSO_Tag Properties Templates_Rev6`.

---

## Spatial Reference Files

### `203-Area.xlsx` — Area Codes
Sheet: `EIS_203 AREA` | 205 rows | Target: `reference_core.area`

| Column | Notes |
|---|---|
| `PLANT_CODE` | always `JDA` |
| `AREA_CODE` | unique code (e.g. `F100`, `G100`, `L100`) |
| `AREA_NAME` | descriptive name |
| `MAIN_AREA_CODE` | parent area grouping |
| `PLANT_REF` | `PLANT-JDA` |

### `204-ProcessUnit.xlsx` — Process Unit Codes
Sheet: `EIS_204 PROCESS UNIT` | 34 rows | Target: `reference_core.process_unit`

| Column | Notes |
|---|---|
| `PLANT_CODE` | always `JDA` |
| `PROCESS_UNIT_CODE` | integer code (e.g. `1`=WELLS, `86`=HVAC, `84`=MAIN POWER) |
| `PROCESS_UNIT_NAME` | |
| `COUNT_OF_TAGS` | informational |

---

## Document-to-Entity Mapping Files
Used to populate `mapping.*` tables and Neo4j edges.

| File | Sheet | Columns | Purpose |
|---|---|---|---|
| `413-Document_References_to_Equipment.xlsx` | Sheet1 | `DOCUMENT_NUMBER`, `PLANT_CODE`, `EQUIPMENT_NUMBER` | Doc↔Equipment links |
| `408-Document_References_to_Site.xlsx` | Sheet1 | `DOCUMENT_NUMBER`, `SITE_CODE` | Doc↔Site |
| `409-Document_References_to_PlantCode.xlsx` | Sheet1 | `DOCUMENT_NUMBER`, `PLANT_CODE` | Doc↔Plant |
| Tag hierarchy data | within MTR | `FROM_TAG`, `TO_TAG`, `PARENT_TAG_NAME` | Signal cable routes + parent-child |

---

## Important Source Quirks
- `SAFETY_CRITICAL_ITEM _GROUP` has a **trailing space** in the column name — use `row.get('SAFETY_CRITICAL_ITEM _GROUP')`
- `EX CLASS` has a **space** in name — use `row.get('EX CLASS')`
- `TAG_DOC` is space-separated multi-value: split and process each code separately
- MTR rows contain computed RAM expressions (e.g. `=16385/383353`) in some ID fields — treat as raw strings
- CFIHOS property codes in format `CFIHOS-XXXXXXXX` identify ontology properties
- Dates in MDR use mixed formats — always use `to_dt()`, never direct cast
