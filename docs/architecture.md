# jackdaw_edw — Solution Architecture

> Domain model, data flows, and module responsibilities.
> Context reference for planning new features.
> Last updated: 2026-04-11

***
## Purpose

Jackdaw EDW ingests engineering tag data from EIS source files into a normalised
PostgreSQL database, validates it against CFIHOS ontology and project-specific
quality rules, and produces certified EIS export registers. It also classifies
vendor review comments (CRS) using a 4-tier LLM cascade. Primary users: data
engineers and EIS system administrators.

***
## Domain Model

### DB Schema Map

| Schema | Purpose | Key tables (live DB confirmed) |
|---|---|---|
| `project_core` | Live project data — SCD2 | `tag`, `document`, `property_value` |
| `ontology_core` | CFIHOS class/property definitions | `class`, `property`, `class_property`, `uom`, `uom_group`, `uom_alias`, `validation_rule` |
| `reference_core` | Project lookup tables | `area`, `process_unit`, `company`, `purchase_order`, `discipline`, `plant`, `site`, `article`, `model_part`, `sece` |
| `mapping` | Many-to-many links — SCD2 | `tag_document`, `tag_sece`, `document_po` |
| `audit_core` | Audit trail, QA rules, CRS | `sync_run_stats`, `tag_status_history`, `export_validation_rule`, `validation_result`, `naming_rule`, `crs_comment` + 7 CRS tables |
| `app_core` | UI users and feedback | `ui_user`, `ui_feedback` |

### Core Concepts

- **Tag** — primary engineering object; identified by `source_id`, named by `tag_name`; classified via `ontology_core.class`; carries `sync_status` and `object_status`
- **Property Value** — per-tag EAV instances in `project_core.property_value`; routed to EIS exports by `mapping_concept` (Functional / Physical / common)
- **Document Link** — tag-to-document N:M associations in `mapping.tag_document`; document-to-PO in `mapping.document_po`
- **SECE** — Safety and Environmental Critical Element mapping in `mapping.tag_sece`
- **CRS Comment** — vendor review comments in `audit_core.crs_comment`; classified by 4-tier cascade

***
## Data Architecture

### SCD2 Change Detection

SCD2 tables confirmed (carry `row_hash`): `project_core.tag`, `project_core.document`, `project_core.property_value`, `mapping.tag_document`, `mapping.tag_sece`, `mapping.document_po`, `audit_core.crs_comment`.

1. Source row hashed → MD5 of all field values joined with `|`
2. Hash unchanged → `sync_status = 'No Changes'`, skip DB writes
3. Hash changed → UPDATE record + INSERT `audit_core.tag_status_history` JSONB snapshot
4. Source ID absent → `sync_status = 'Deleted'`
5. New source ID → INSERT, `sync_status = 'New'`

### FK Resolution Pattern

Every FK field stored as `*_raw` (source verbatim) + resolved UUID.
Unresolved FK → `*_raw` preserved, FK column = NULL, WARNING logged. FKs never auto-created.

### Audit Layer

| Table | Purpose |
|---|---|
| `audit_core.sync_run_stats` | One row per flow run: start/end time, counts (created, updated, unchanged, deleted, errors) |
| `audit_core.tag_status_history` | JSONB snapshot of key fields before each tag change |
| `audit_core.validation_result` | QA violations grouped by `session_id` |
| `audit_core.export_validation_rule` | Rule catalogue: DSL conditions, fix expressions, tier, scope |
| `audit_core.naming_rule` | Naming convention rules (regex patterns per domain/category) |

### Key Status Values (live DB confirmed)

`sync_status`: `'No Changes'` (22 945) · `'Extended'` (126) · `'New'` / `'Updated'` / `'Deleted'` during sync runs
`object_status` (ADR-010): `'Active'` — `'Inactive'` is the soft-delete target; `'Deleted'` does not exist
`tag_status` (ADR-011): `'ACTIVE'` · `'VOID'` · `'ASB'` · `'AFC'` · `'Future'` · NULL — stored verbatim from EIS

***
## Import Modules

### import_ontology + import_reference
Populate `ontology_core` (class, property, class_property, uom, uom_group, uom_alias) and
`reference_core` (area, process_unit, discipline, company, plant, project, purchase_order,
article, model_part, sece) from EIS master files. All inserts use `ON CONFLICT DO NOTHING`.

### import_tag_data
Ingests EIS tag file → `project_core.tag` via SCD2. FK lookup caches loaded into memory per run.
Second-pass `sync_tag_hierarchy` resolves `parent_tag_id` after main UPSERT.
`TAG_NAME_CHANGED` violations written to `audit_core.validation_result` (Critical, non-blocking).

### import_doc_data
Ingests MDR → `project_core.document` + `mapping.tag_document` + `mapping.document_po`.
SCD2 change detection; N:M links rebuilt per sync.

### import_prop_data
Ingests property value EAV → `project_core.property_value`. Routed by `class_property.mapping_concept`.
Produces `'Extended'` sync_status for property-extended tag records.

**import_master_sync** — orchestrator: ontology → reference → tag data → tag hierarchy → doc data → property values.
***
## Export Modules

### EIS Export Pipeline (`etl/tasks/export_pipeline.py`)

```
SQL extract (WHERE object_status = 'Active')
  → sanitize_dataframe()     — encoding repair, NaN cleanup
  → load_validation_rules()  — DSL rules for scope
  → apply_builtin_fixes()    — auto-fix + violation collection
  → transform_*()            — EIS column order, date format
  → write_csv()              — UTF-8 BOM (.CSV), EIS filename
  → log_audit_end()          — update sync_run_stats
```

### EIS Register Summary

| Scope | EIS seq | Template | Content |
|---|---|---|---|
| `tag` | 003 | `-003-` | Tag Register |
| `equipment` | 004 | `-004-` | Master Equipment Register |
| `tag_property` | 303 | `-010-` | Tag property values (Functional) |
| `equipment_property` | 301 | `-011-` | Equipment property values (Physical) |
| `area` | 203 | `-017-` | Area Register |
| `process_unit` | 204 | `-018-` | Process Unit Register |
| `purchase_order` | 214 | `-008-` | Purchase Order Register |
| `model_part` | 209 | `-005-` | Model Part Register |
| `tag_class_property` | 307 | `-009-` | Tag Class Properties (ontology) |
| `tag_connections` | 212 | `-006-` | Tag Physical Connections |
| doc cross-refs | 408–420 | `-016-`–`-024-` | 8 Doc↔{Site, Plant, Area, PU, Tag, Equip, Model, PO} |

Property routing: `mapping_concept ILIKE '%Functional%'` → seq 303; `ILIKE '%Physical%'` → seq 301;
`common` rows excluded from property registers (already in tag/equipment registers).
`export_eis_data_deploy` orchestrates all EIS export flows.

***
## Validation Framework

**90 active rules** in `audit_core.export_validation_rule`. Two modes: **Built-in** (during export,
auto-fix applies, results optional) and **Full scan** (on-demand, no fixes, always stored).

| Tier | Name | check_type | Count | Status |
|---|---|---|---|---|
| L0 | Foundation | dsl | 9 | ✅ Implemented |
| L1 | Syntax & Encoding | dsl | 23 | ✅ Implemented |
| L2 | Completeness & Validity | dsl | 40 | ✅ Implemented |
| L3 | Topology & Cross-Reference | cross_field / cross_table / aggregate / graph | 16 | 🔲 Planned |
| L4 | Semantics | metadata (Ollama) | 2 | 🔲 Planned |

**Key validation queries:**

```sql
-- Open violations by tier and severity
SELECT r.tier, r.scope, vr.severity, count(*) as violations
FROM audit_core.validation_result vr
JOIN audit_core.export_validation_rule r ON vr.rule_code = r.rule_code
WHERE vr.is_resolved = false
GROUP BY r.tier, r.scope, vr.severity
ORDER BY r.tier, vr.severity;

-- FK resolution failures
SELECT rule_code, count(*) as cnt FROM audit_core.validation_result
WHERE is_resolved = false AND rule_code ILIKE '%_FK_%'
GROUP BY rule_code ORDER BY cnt DESC;

-- TAG_NAME_CHANGED violations
SELECT object_name, violation_detail, run_time FROM audit_core.validation_result
WHERE rule_code = 'TAG_NAME_CHANGED' AND is_resolved = false
ORDER BY run_time DESC;
```

***
## CRS Management

Classifies vendor review comments against the engineering tag register.
All 8 CRS tables confirmed in `audit_core`: `crs_comment` (LLM category, confidence, model, formal response),
`crs_comment_template` (KB; grows via Tier 3 feedback), `crs_comment_audit`, `crs_comment_validation`,
`crs_llm_template_staging`, `crs_template_query_map`, `crs_validation_query`, `crs_benchmark_example`.

**4-tier cascade** (`classify_crs_comments_deploy.py`): Tier 0 deterministic skip (~5–10%) →
Tier 1 KB template matching, threshold 0.92 (50–70%) → Tier 2 keyword rules (15–20%) →
Tier 3 Qwen3 LLM (5–10%). Tier 3 results feed back into KB to raise Tier 1 coverage over time.

***
## Adding New Functionality

| Goal | Where to start |
|---|---|
| New import source | `etl/flows/` new flow + `etl/tasks/` task + `sql/schema/schema.sql` |
| New EIS export field | Update SQL extract + `export_transforms.py` + `schema.sql` |
| New reference table | `reference_core` schema + `import_reference` + FK in `project_core.tag` |
| New validation rule | INSERT into `audit_core.export_validation_rule`; DSL for L0–L2; migration file |
| New ontology class/property | `import_ontology` + `ontology_core.class` + `class_property` links |
| Schema change | `/schema-change` → `sql/schema/schema.sql` updated in same commit |
| UI feature | `ui/pages/` new page + `ui/app.py` nav registration |

***
## Active ADRs

| ADR | Decision |
|---|---|
| ADR-008 | Property values routed by `mapping_concept`: Functional → seq 303, Physical → seq 301 |
| ADR-009 | Validation cleanup: removed duplicates, unified `NO_INVALID_CHARS`, extended DSL fix ops |
| ADR-010 | `object_status` soft-delete = `'Inactive'`; export filter `WHERE object_status = 'Active'` is correct |
| ADR-011 | `tag_status` stores EIS verbatim: `'ACTIVE'`, `'VOID'`, `'ASB'`, `'AFC'`, `'Future'` — normalization deferred |
| ADR-012 | UI v0.3.0: hidden LLM Chat (Phase 3), ETL Import; added Tag Register page; CRS module active |
