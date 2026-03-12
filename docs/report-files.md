# Report Files Reference (EIS Outputs)

> Load when needed: `@docs/report-files.md`
> All outputs written to configured `storage.export_dir` (from `db_config.yaml`)
> Encoding: UTF-8 BOM (`utf-8-sig`) — mandatory for all EIS CSV exports

---

## EIS Tag Register — seq 003 (Primary Export)

**File**: `JDAW-KVE-E-JA-6944-00001-003-{doc_revision}.CSV`
**Flow**: `export_tag_register_flow`
**Source**: `project_core.tag` JOIN all FK tables WHERE `object_status = 'Active'`

Column order (strict per JDAW-PT-D-JA-7739-00003):
```
PLANT_CODE · TAG_NAME · PARENT_TAG_NAME · AREA_CODE · PROCESS_UNIT_CODE ·
TAG_CLASS_NAME · TAG_STATUS · REQUISITION_CODE · DESIGNED_BY_COMPANY_NAME ·
COMPANY_NAME · PO_CODE · PRODUCTION_CRITICAL_ITEM · SAFETY_CRITICAL_ITEM ·
SAFETY_CRITICAL_ITEM_GROUP · SAFETY_CRITICAL_ITEM_REASON_AWARDED ·
TAG_DESCRIPTION · ACTION_STATUS · ACTION_DATE
```
- `ACTION_STATUS` ← `tag.sync_status`
- `ACTION_DATE` ← `tag.sync_timestamp` formatted as `YYYY-MM-DD`
- `PARENT_TAG_NAME`: literal `'unset'` → empty string
- `SAFETY_CRITICAL_ITEM_GROUP`: aggregated via correlated subquery from `mapping.tag_sece`

---

## EIS Spatial Reference Outputs

### Process Unit Export — seq 204
**File**: `204-ProcessUnit.CSV`
**Source**: `reference_core.process_unit` JOIN `reference_core.plant`

| Column | Source |
|---|---|
| `PLANT_CODE` | `plant.code` |
| `PROCESS_UNIT_CODE` | `process_unit.code` |
| `PROCESS_UNIT_NAME` | `process_unit.name` |
| `COUNT_OF_TAGS` | COUNT from `project_core.tag` |

### Area Export — seq 203
**File**: `203-Area.CSV`
**Source**: `reference_core.area` JOIN `reference_core.plant`
205 areas for `PLANT_CODE=JDA`.

| Column | Source |
|---|---|
| `PLANT_CODE` | `plant.code` |
| `AREA_CODE` | `area.code` |
| `AREA_NAME` | `area.name` |
| `MAIN_AREA_CODE` | `area.main_area_code` |
| `PLANT_REF` | computed: `'PLANT-' || plant.code` |

---

## Document Register Outputs

### MDR Export
**Source**: `project_core.document` WHERE `mdr_flag = True`

| Column | Source |
|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` |
| `DOCUMENT_TITLE` | `document.title` |
| `REVISION_CODE` | `document.rev` |
| `REVISION_DATE` | `document.rev_date` formatted `MM/DD/YYYY` |
| `DOCUMENT_STATUS` | `document.status` |
| `SITE_CODE` | via `plant → site` FK chain |
| `PLANT_CODE` | `plant.code` |
| `PROJECT_CODE` | `project.code` |
| `AREA_CODE` | `document.area_code_raw` (stored as raw — no FK) |
| `DOCUMENT_TYPE_CODE` | `document.doc_type_code` |
| `PO_CODE` | via `purchase_order.code` |
| `COMPANY_NAME` | via `company.name` |
| `MDR` | `True`/`False` |

---

## Document-to-Entity Reference Outputs

### 413 — Document References to Equipment
**File**: `413-Document_References_to_Equipment.CSV`
**Source**: `mapping.tag_document` JOIN `project_core.tag` JOIN `project_core.document`

| Column | Source |
|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` |
| `PLANT_CODE` | `plant.code` via tag |
| `EQUIPMENT_NUMBER` | `tag.equipment_number` (format: `Equip_{tag_name}`) |

### 408 — Document References to Site
**File**: `408-Document_References_to_Site.CSV`

| Column | Source |
|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` |
| `SITE_CODE` | via `plant → site.code` |

### 409 — Document References to Plant
**File**: `409-Document_References_to_PlantCode.CSV`

| Column | Source |
|---|---|
| `DOCUMENT_NUMBER` | `document.doc_number` |
| `PLANT_CODE` | `plant.code` |

---

## Tag Hierarchy Report
**Source**: `project_core.tag` self-join on `parent_tag_id`
Used for Neo4j graph population and impact-chain analysis.

| Column | Source |
|---|---|
| `PLANT_CODE` | `plant.code` |
| `TAG_NAME` | `tag.tag_name` |
| `PARENT_TAG_NAME` | parent `tag.tag_name` (NULL → empty) |
| `FROM_TAG` | `from_tag.tag_name` (signal cable source) |
| `TO_TAG` | `to_tag.tag_name` (signal cable destination) |

---

## Export Invariants (apply to all EIS outputs)
- Encoding: always `utf-8-sig` (UTF-8 BOM)
- `sanitize_dataframe()` called unconditionally before write
- `object_status = 'Active'` filter enforced at both SQL and Python layers
- File extension uppercase: `.CSV` not `.csv`
- Audit record written to `audit_core.sync_run_stats` for every export run
