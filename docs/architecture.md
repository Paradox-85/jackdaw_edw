# Architecture Reference

> Load when needed: `@docs/architecture.md`

## Hardware
- CPU: AMD Ryzen 7 7700
- GPU: NVIDIA RTX 3090 (24 GB VRAM) — Ollama GPU inference
- Host: Proxmox LXC (Ubuntu 24) + Docker Compose

## Docker Services (from docker-compose.yml)

| Container | Image | Ports | Role |
|---|---|---|---|
| `postgres_db` | postgres:16-bookworm | 5432 | Primary DB (`engineering_core` + `prefect` + `flowise_db`) |
| `redis` | redis:alpine | — | Prefect message broker + cache |
| `prefect-server` | prefecthq/prefect:3-latest | 4200 | Orchestration API + UI |
| `prefect-services` | prefecthq/prefect:3-latest | — | Background Prefect services (depends on `prefect-server`) |
| `prefect-worker` | prefecthq/prefect:3-latest | — | Flow executor, pool: `local-pool` |
| `ollama` | ollama/ollama:latest | 11434 | Local LLM (GPU), models in `./ollama_storage` |
| `flowise` | flowiseai/flowise:latest | 3001 | AI agent builder (DB: `flowise_db`) |
| `qdrant` | qdrant/qdrant:latest | 6333 | Vector search, storage: `./qdrant_storage` |
| `neo4j` | neo4j:latest | 7474 (HTTP), 7687 (Bolt) | Graph DB, data: `./neo4j_data` |
| `dbgate_gui` | dbgate/dbgate:latest | 18978 | DB admin UI, pre-configured for `engineering_core` |
| `jackdaw-ui` | jackdaw-control-center:2.0 | 8501 | Streamlit Control Center — ETL triggers, reports, validation, LLM chat |

## Jackdaw UI — EDW Control Center

Streamlit multi-page application deployed as Docker service `jackdaw-ui` on LXC 200.

| Parameter | Value |
|---|---|
| External URL | `https://jackdaw.edw.adzv-pt.dev` |
| Internal port | `10.10.10.50:8501` |
| Build context | `edw/` root, Dockerfile at `docker/jackdaw-ui/Dockerfile` |
| DB access | Viewer queries: `edw_viewer` (SELECT only); Admin triggers: `postgres_admin` |
| Prefect API | `http://prefect-server:4200/api` |

**Pages:**

| Page | Role | Description |
|---|---|---|
| Home | Viewer | KPI dashboard: active tags, docs, service health, recent flow runs |
| Reports | Viewer | 4 built-in SQL reports + dynamic catalogue from `audit_core.report_metadata` |
| Tag History | Viewer | SCD audit trail from `audit_core.tag_status_history` with filters |
| Validation | Viewer | Violation stats from `audit_core.validation_result`, rule catalogue |
| LLM Chat | Viewer | Local Q&A via Ollama (RTX 3090) |
| CRS Assistant | Viewer | 🚧 Phase 2 stub |
| ETL Import | Admin | Trigger `sequential-master-sync` Prefect deployment |
| EIS Export | Admin | Trigger `export-tag-register-deployment` / `export-equipment-register-deployment` or direct query download |
| Services | Admin | Infra links (Prefect, DbGate), deployment health |

**DB roles:**
- `edw_viewer` — SELECT only on all 5 schemas. Used for all report/viewer queries.
- `postgres_admin` — full access. Used only for admin-triggered ETL audit queries.

## Key Configuration Facts
- **Prefect API URL**: `https://pve.prefect.adzv-pt.dev/api`
- **DB user**: `postgres_admin` / DB: `engineering_core`
- **Prefect worker** installs deps at startup from:
  `/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts/requirements.txt`
- **Ollama + Qdrant** mount shared data read-only:
  `/mnt/backup-hdd/sftpgo-data/ram-user/Jackdaw/Master-Data:/data/shared:ro`
- **DbGate** auth: `admin` user, connections restricted to `eng_db` only

## Service Dependencies
```
postgres ←─ prefect-server ←─ prefect-services
         ←─ prefect-server ←─ prefect-worker
         ←─ flowise
redis    ←─ prefect-server
```

## Data Access Paths
- Source EIS files: `/mnt/shared-data/ram-user/Jackdaw/`
- Project symlinks: `./data/current/` and `./data/_history/`
- Config: `config/db_config.yaml`

## Data Flow
```
EIS Excel/CSV files (./data/current/)
        ↓
seed_ontology flow
        ↓  populates ontology_core + reference_core (CFIHOS classes, UoM, picklists)
sync_tag_data flow
        ↓  SCD2 UPSERT → project_core.tag + mapping.tag_document + mapping.tag_sece
        ↓  every change → audit_core.tag_status_history (JSONB snapshot)
sync_tag_hierarchy flow
        ↓  second pass → resolves tag.parent_tag_id

Tag & Equipment Registers:
export_tag_register flow         → EIS CSV (UTF-8 BOM, seq 003, -003-)
export_equipment_register flow   → EIS CSV (UTF-8 BOM, seq 004, -004-)

Property Values:
export_tag_properties flow       → EIS CSV (UTF-8 BOM, seq 303, -010-, Functional concept)
export_equipment_properties flow → EIS CSV (UTF-8 BOM, seq 301, -011-, Physical concept)

Reference Data:
export_area_register flow        → EIS CSV (UTF-8 BOM, seq 203, -017-)
export_process_unit flow         → EIS CSV (UTF-8 BOM, seq 204, -018-)
export_purchase_order flow       → EIS CSV (UTF-8 BOM, seq 214, -008-)
export_model_part flow           → EIS CSV (UTF-8 BOM, seq 209, -005-)

Ontology:
export_tag_class_properties flow → EIS CSV (UTF-8 BOM, seq 307, -009-)

Parallel enrichment:
  Neo4j  ← Tag→Parent, Tag→Doc graph edges
  Qdrant ← property_value embeddings via Ollama
  Flowise ← AI agents querying EDW
```

## AI Layer
| Component | Purpose |
|---|---|
| **Ollama** (RTX 3090) | Anomaly detection, description enrichment, NLP on engineering text |
| **Qdrant** | Semantic property search (find similar instruments by spec) |
| **Neo4j** | Impact-chain: "if this valve fails, which docs/systems are affected?" |
| **Flowise** | Business-user natural language interface to EDW data |

---

## Seed Flows

### seed_ontology
Populates reference tables from EIS-standard and project-specific master data files. Runs before any tag sync.

**Targets populated:**
- `ontology_core.class` — CFIHOS tag classes (e.g. `INSTRUMENT`, `VALVE`)
- `ontology_core.property`, `ontology_core.class_property` — property definitions per class
- `ontology_core.uom`, `ontology_core.uom_group` — units of measure
- `reference_core.area`, `reference_core.process_unit`, `reference_core.discipline` — project areas and units
- `reference_core.company`, `reference_core.plant`, `reference_core.project` — ownership entities
- `reference_core.purchase_order`, `reference_core.article`, `reference_core.model_part` — procurement chain

**Behaviour:** All seed inserts use `ON CONFLICT DO NOTHING` — idempotent, safe to re-run. No deletes from reference tables.

---

## Sync Flow (sync_tag_data)

Ingests EIS source file (Excel/CSV) into `project_core.tag` using SCD Type 2 change detection.

### SCD2 Algorithm
```
1. Read source file: dtype=str, na_filter=False (preserves literal "NA" strings)
2. Load FK lookup caches into memory (class, area, unit, discipline, po, company, article...)
3. Load existing tag cache: {source_id: (id, row_hash, sync_status, tag_name_in_db)}
4. For each source row:
   a. Compute MD5 hash of all field values joined with "|"
   b. source_id not in cache → INSERT tag, sync_status='New'
   c. hash == cached_hash → skip all DB writes, increment unchanged counter
   d. hash != cached_hash → UPDATE tag fields + INSERT audit_core.tag_status_history snapshot
5. source_id in cache but not in source file → UPDATE sync_status='Deleted'
6. Second pass (sync_tag_hierarchy): resolve parent_tag_id by tag_name lookup
```

### FK Resolution Pattern
Every raw FK field is stored both as `*_raw` (original source value) and resolved to a UUID FK. If the lookup misses, `*_raw` is preserved and the FK column is set to NULL — never auto-created. A WARNING is logged per unresolved FK.

### Audit (per tag change)
Every INSERT or UPDATE writes:
- `audit_core.sync_run_stats` — INSERT on flow start (run_id, source_file, start_time), UPDATE on completion (count_created, count_updated, count_unchanged, count_deleted, count_errors)
- `audit_core.tag_status_history` — JSONB snapshot of key fields before each change (tag_name, class_raw, area_raw, unit_raw, discipline_raw, po_raw, article_raw, design_company_raw)

### TAG_NAME_CHANGED Detection
Tag names are immutable per source system rules — a `source_id` must always map to the same `tag_name`. The sync flow detects violations:

```
For each source row where source_id already exists in DB:
    if tag_name_in_db != tag_name_in_source:
        log WARNING: TAG_NAME_CHANGED
        append violation dict to tag_name_violations list

At end of sync transaction:
    bulk INSERT tag_name_violations into audit_core.validation_result
    (rule_code='TAG_NAME_CHANGED', scope='sync', severity='Critical')
```

No tag update is blocked — the violation is recorded for audit. The tag continues to sync with its current (changed) name while the violation record flags it for review.

---

## Export Flows

### Export Flows — All 9 outputs

All flows implement the same pipeline via `run_export_pipeline()` in `etl/tasks/export_pipeline.py`.

| Flow file | EIS seq | File template | Scope | Default rev |
|---|---|---|---|---|
| `export_tag_register.py` | 003 | `-003-` | `tag` | A35 |
| `export_equipment_register.py` | 004 | `-004-` | `equipment` | A01 |
| `export_tag_properties.py` | 303 | `-010-` | `tag_property` | A01 |
| `export_equipment_properties.py` | 301 | `-011-` | `equipment_property` | A01 |
| `export_area_register.py` | 203 | `-017-` | `area` | A35 |
| `export_process_unit.py` | 204 | `-018-` | `process_unit` | A35 |
| `export_purchase_order.py` | 214 | `-008-` | `purchase_order` | A35 |
| `export_model_part.py` | 209 | `-005-` | `model_part` | A35 |
| `export_tag_class_properties.py` | 307 | `-009-` | `tag_class_property` | A35 |

Both tag and equipment register flows implement the same pipeline via `run_export_pipeline()` in `etl/tasks/export_pipeline.py`:

```
extract (SQL → raw DataFrame, WHERE object_status = 'Active')
    ↓
sanitize_dataframe()          — strip encoding artefacts (Â², mojibake, NaN strings)
    ↓
load_validation_rules()       — load DSL-only (check_type='dsl') builtin rules from DB
    ↓
apply_builtin_fixes()         — DSL-driven auto-fixes + violation collection
    ↓
transform_*()                 — rename columns, format dates, enforce EIS column order
    ↓
write_csv()                   — sanitize_dataframe() again (idempotent) → UTF-8 BOM CSV
    ↓
[optional] store_validation_results()  — persist violations if persist_violations=True
    ↓
log_audit_end()               — UPDATE audit_core.sync_run_stats (row_count, count_errors)
```

### Output File
- Naming: `JDAW-KVE-E-JA-6944-00001-003-{doc_revision}.CSV`
- Encoding: UTF-8 BOM (`utf-8-sig`) — required for EIS system and Excel
- Column order: strict per EIS spec JDAW-PT-D-JA-7739-00003
- Filter: SQL `WHERE object_status = 'Active'` + Python guard `df[df["object_status"] == "Active"]`

---

## Validation Framework

### Overview

The validation framework provides configurable, database-driven data quality checks for EIS export registers. Rules are stored in `audit_core.export_validation_rule` and interpreted at runtime by `etl/tasks/export_validation.py`.

### Two Modes

| Mode | When | Auto-fix | Results stored |
|---|---|---|---|
| **Built-in** | During export generation | Yes (if fix_expression defined) | Only in flow logs (optionally `validation_result`) |
| **Full scan** | On-demand audit run | Never | `audit_core.validation_result` |

**Built-in mode** (`apply_builtin_fixes`): applies only `is_builtin=true AND check_type='dsl'` rules. If a rule has `fix_expression`, the fix is applied to the in-memory DataFrame — the database value is never modified. If a rule has no `fix_expression` and `is_blocking=true`, the violation is logged as ERROR (the field will be empty in the report due to unresolved FK). **Export is never aborted** in either case.

**Full scan mode** (`run_full_scan`): applies all active DSL rules for the target scope. No fixes are applied. Every violation is collected and bulk-inserted into `audit_core.validation_result` with session grouping. L3/L4 (non-DSL) rules are excluded from both modes — they require custom executors not yet implemented.

### Rule Table Schema

```sql
audit_core.export_validation_rule (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code       TEXT UNIQUE NOT NULL,
    scope           TEXT NOT NULL,          -- 'common' | 'tag' | 'equipment' | 'sync'
    object_field    TEXT NULL,              -- specific column targeted, NULL for multi-column rules
    description     TEXT NULL,
    rule_expression TEXT NOT NULL,          -- DSL violation condition (matching rows = violators)
    fix_expression  TEXT NULL,              -- DSL auto-fix for built-in mode; NULL = check-only
    is_builtin      BOOLEAN NOT NULL DEFAULT false,  -- run during export generation
    is_blocking     BOOLEAN NOT NULL DEFAULT false,  -- field-level data impact (log ERROR vs WARNING)
    severity        TEXT NOT NULL DEFAULT 'Warning', -- 'Critical' | 'Warning' | 'Info' | 'Error'
    object_status   TEXT NOT NULL DEFAULT 'Active',
    -- Added migration_005:
    tier            TEXT NULL,              -- QA priority level: 'L0'|'L1'|'L2'|'L3'|'L4'
    category        TEXT NULL,             -- rule category (Foundation|Encoding|Syntax|Limits|
                                           --   Validity|Completeness|Referential|UoM|
                                           --   Topology|CrossField|Semantics)
    source_ref      TEXT NULL,             -- traceability: spec doc number or techRules ref
    check_type      TEXT NOT NULL DEFAULT 'dsl',  -- executor: 'dsl'|'cross_field'|'cross_table'|
                                                   --           'aggregate'|'graph'|'metadata'
    sort_order      INTEGER NULL           -- display order within tier (for UI/reports)
)
```

`scope` controls which exports load the rule:
- `common` — loaded by all export flows (tag + equipment)
- `tag` — tag register export only (`export_tag_register`)
- `equipment` — equipment register export only (`export_equipment_register`)
- `tag_property` — tag property values export (`export_tag_properties`, seq 303)
- `equipment_property` — equipment property values export (`export_equipment_properties`, seq 301)
- `area` — area register export (`export_area_register`, seq 203)
- `process_unit` — process unit register export (`export_process_unit`, seq 204)
- `purchase_order` — purchase order register export (`export_purchase_order`, seq 214)
- `model_part` — model part register export (`export_model_part`, seq 209)
- `tag_class_property` — tag class properties export (`export_tag_class_properties`, seq 307)
- `sync` — sync-time rules (e.g. TAG_NAME_CHANGED); not evaluated via DSL engine

**Note:** scopes `area`, `process_unit`, `purchase_order`, `model_part`, `tag_class_property` have no
rules seeded yet — `load_validation_rules()` will return an empty list and log a warning.

### Validation Result Table Schema

```sql
audit_core.validation_result (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID NOT NULL,          -- groups all results from one scan run
    run_time         TIMESTAMP NOT NULL DEFAULT now(),
    rule_code        TEXT NOT NULL,
    scope            TEXT NOT NULL,
    severity         TEXT NOT NULL DEFAULT 'Warning',
    object_type      TEXT NULL,              -- 'tag' | 'document' | 'property_value' etc.
    object_id        UUID NULL,              -- FK to the violating record
    object_name      TEXT NULL,              -- human-readable identifier (tag_name, equip_no)
    violation_detail TEXT NULL,              -- description of the violation
    column_name      TEXT NULL,              -- column where violation was found
    original_value   TEXT NULL,              -- raw violating value (truncated to 200 chars)
    is_resolved      BOOLEAN NOT NULL DEFAULT false,
    -- Added migration_005:
    tier             TEXT NULL,              -- inherited from rule at scan time
    category         TEXT NULL,             -- inherited from rule at scan time
    check_type       TEXT NULL              -- inherited from rule at scan time
)
```

Indexes: `idx_val_result_session (session_id)`, `idx_val_result_object_id (object_id)`

### Tier Classification (L0–L4)

Rules are classified by QA priority tier per `master_qa_techRules.md`:

| Tier | Name | Description | Blocking behaviour |
|---|---|---|---|
| **L0** | Foundation | Identity fields — tag must exist and have a status and class | Always Critical, blocks meaningful export |
| **L1** | Syntax & Encoding | Format correctness — encoding, length limits, valid value sets | Auto-fixed where possible; otherwise Warning/Critical |
| **L2** | Completeness & Validity | Mandatory attributes, pseudo-NULL format, UoM rules, FK resolution | Warning/Critical depending on field importance |
| **L3** | Topology & Cross-Reference | Parent-child hierarchy, doc links, cross-table consistency | Require custom executor (not yet DSL) |
| **L4** | Semantics | ML-assisted description quality (Ollama) | metadata-only until Ollama executor implemented |

### check_type / Executor Routing

`check_type` determines which engine processes the rule:

| check_type | Engine | Status |
|---|---|---|
| `dsl` | Standard DSL parser in `export_validation.py` | ✅ Implemented — all L0/L1/L2 rules |
| `cross_field` | Intra-DataFrame conditional logic | 🔲 Planned (L3 rules) |
| `cross_table` | JOIN against another DB table | 🔲 Planned (L3 rules) |
| `aggregate` | COUNT/GROUP BY across rows | 🔲 Planned (L3 rules) |
| `graph` | Neo4j Cypher query | 🔲 Planned (L3 cyclic check) |
| `metadata` | Traceability record only — not executed | ✅ Stored for future Ollama/manual use |

`load_validation_rules()` filters to `COALESCE(check_type, 'dsl') = 'dsl'` — non-DSL rules are never passed to the DSL engine, preventing parse errors on descriptive rule_expressions.

### DSL — rule_expression (violation condition)

```
<col_spec> <op> [<value>]
<clause1> AND <clause2>
```

`col_spec`:
- `*` — apply to all object (string) columns; combine results with OR
- `COLUMN_NAME` — case-insensitive column lookup; rule skipped if column absent

Operators:

| Operator | Example | Notes |
|---|---|---|
| `contains "X"` | `* contains ","` | Case-sensitive substring |
| `icontains "X"` | `PO_CODE icontains "-VOID"` | Case-insensitive substring |
| `max_length N` | `COMPANY_NAME max_length 30` | Violation if `len(value) > N` |
| `is_null` | `EQUIPMENT_NUMBER is_null` | Matches NULL, empty string, `"none"` |
| `not_null` | `area_code_raw not_null` | Inverse of is_null |
| `matches_regex "pat"` | `TAG_STATUS matches_regex "^(?!(Active\|Void\|Future\|Hold)$).*"` | Python re, violation on match |
| `has_encoding_artefacts` | `* has_encoding_artefacts` | Detects UTF-8 mojibake and Win-1252 leakage (Â², â€œ etc.) |

**Implementation note:** `has_encoding_artefacts` calls `series.fillna("").astype(str).apply(...)` — the `fillna("")` guard is required because object-dtype columns may contain float NaN values that would cause `TypeError` inside the lambda.

`AND` requires both sub-clauses to be true on the same row (used for FK checks: `raw_field not_null AND resolved_col is_null`).

### DSL — fix_expression (auto-fix for built-in mode)

| fix_expression | Action |
|---|---|
| `replace "X" "Y"` | Replace all occurrences of X with Y (literal, not regex) |
| `replace_nan` | Replace exact-match `nan`/`NaN` strings with empty string |
| `remove_char "X"` | Remove all occurrences of character X |
| `truncate N` | Truncate string to at most N characters |
| `encoding_repair` | Apply `clean_engineering_text()` from `export_transforms` — repairs mojibake, removes control chars |

Fix is applied to the column identified by the rule's `col_spec`. For `AND` clauses and wildcard `*` rules, fix is applied to all object columns.

### is_blocking Semantics

`is_blocking` describes visible data impact in the report — it does **not** abort the export.

| is_blocking | fix_expression | Outcome |
|---|---|---|
| true | defined | Fix applied → field correct in report → log INFO |
| true | NULL | FK unresolved → field empty in report (NULL from JOIN) → log ERROR |
| false | defined | Fix applied → log WARNING |
| false | NULL | Field may be empty → log WARNING |

`count_errors` in `audit_core.sync_run_stats` reflects the total count of violations (fixed + unfixed).

### Seed Rules Summary

**Total: 69 rules** (42 from migration_003 + 27 from migration_005)

#### migration_003 rules — Base Set (42 rules)

**Common — Encoding/Syntax (7):**

| rule_code | tier | is_builtin | is_blocking | fix |
|---|---|---|---|---|
| `NO_COMMA_IN_VALUES` | L1 | ✓ | ✓ | `replace "," ";"` |
| `NO_NAN_STRINGS` | L1 | ✓ | ✓ | `replace_nan` (fixed: exact regex match) |
| `NO_INVALID_CHARS` | L1 | ✓ | — | `remove_char "<"` |
| `DECIMAL_DOT_SEPARATOR` | L1 | — | — | — |
| `COMPANY_NAME_MAX_30` | L1 | ✓ | — | `truncate 30` |
| `TAG_DESC_MAX_255` | L1 | ✓ | — | `truncate 255` |
| `ENCODING_ARTEFACTS` | L1 | ✓ | — | `encoding_repair` |

**Common — Validity/Referential (3):**

| rule_code | tier | is_builtin | is_blocking | fix |
|---|---|---|---|---|
| `PLANT_FK_RESOLVED` | L2 | ✓ | ✓ | — |
| `PO_CODE_NOT_VOID` | L1 | — | — | — |
| `MANDATORY_NOT_EMPTY` | L2 | — | — | — (metadata) |

**Tag — FK Resolution (9):**

| rule_code | tier | is_builtin | is_blocking |
|---|---|---|---|
| `AREA_FK_RESOLVED` | L2 | — | — |
| `CLASS_FK_RESOLVED` | L2 | ✓ | ✓ |
| `PROCESS_UNIT_FK_RESOLVED` | L2 | ✓ | ✓ |
| `DESIGN_CO_FK_RESOLVED` | L2 | ✓ | ✓ |
| `PO_FK_RESOLVED` | L2 | ✓ | ✓ |
| `ARTICLE_FK_RESOLVED` | L2 | ✓ | ✓ |
| `PARENT_TAG_FK_RESOLVED` | L2 | ✓ | ✓ |
| `DISCIPLINE_FK_RESOLVED` | L2 | — | — |
| `PROCESS_UNIT_MANDATORY` | L2 | — | — |
| `AREA_CODE_EXPECTED` | L2 | — | — |

**Tag — Topology/Referential (6, full-scan descriptive):**
`TAG_ACTIVE_IN_MASTER`, `CLASS_MATCHES_RDL`, `NO_ABSTRACT_CLASS`, `TAG_MIN_ONE_DOCUMENT`,
`PHYSICAL_CONNECTION_NO_DUPLICATE`, `PHYSICAL_CONNECTION_TAGS_VALID`, `VOID_DELETED_EXCLUDED_FROM_XREF`
→ all L3, check_type=`cross_table` or `aggregate`

**Equipment — FK Resolution + Completeness (5):**
`EQUIP_NO_NOT_NULL`, `MODEL_PART_FK_RESOLVED`, `MANUFACTURER_FK_RESOLVED`, `VENDOR_FK_RESOLVED`
→ all L2; `EQUIP_TAG_PREFIX_MATCH` → L3 `cross_table`

**Equipment — Null/UoM Logic (10):**
`NO_INFORMATIONAL_ZERO`, `HEATER_WATTAGE_POSITIVE`, `SERIAL_NO_NOT_EMPTY`, `SERIAL_NO_NO_NA_FOR_BULK`,
`UOM_BLANK_WHEN_VALUE_NA`, `UOM_BLANK_WHEN_VALUE_TBC`, `AREA_UNIT_AVEVA_FORMAT`,
`VALUE_UOM_COMBINED_IN_CELL`, `COUNT_PROPERTY_UOM_EMPTY`
→ L2, check_type=`dsl`

**Cross-file (2):** `DOC_EXISTS_IN_MDR`, `PO_CODE_EXISTS_IN_MASTER` → L3 `cross_table`

**Sync-time (1):** `TAG_NAME_CHANGED` → L0, check_type=`metadata`, detected in code not DSL

#### migration_005 rules — Gap Analysis Extension (27 rules)

**L0 — Foundation (3):**

| rule_code | is_builtin | is_blocking | severity |
|---|---|---|---|
| `TAG_NAME_NOT_NULL` | ✓ | ✓ | Critical |
| `TAG_STATUS_NOT_NULL` | ✓ | ✓ | Critical |
| `TAG_CLASS_NOT_NULL` | ✓ | ✓ | Critical |

**L1 — Syntax & Validity (8):**

| rule_code | is_builtin | fix |
|---|---|---|
| `TAG_DESC_MAX_120` | — | `truncate 120` |
| `TAG_STATUS_VALID_VALUES` | — | — |
| `SAFETY_CRITICAL_VALID_VALUES` | — | — |
| `SECE_SEMICOLON_DELIMITER` | ✓ | `replace "," ";"` |
| `PIPE_TAG_NO_TRAILING_DASH` | — | — |
| `DESC_NO_DOUBLE_SPACE` | ✓ | `replace "  " " "` |
| `DESC_NO_FROM_TO_SUFFIX` | — | — |
| `PO_CODE_NOT_VOID_SUFFIX` | — | — |

**L2 — Completeness & Validity (9):**

| rule_code | is_builtin | is_blocking |
|---|---|---|
| `TAG_DESC_NOT_NULL` | — | ✓ |
| `AREA_CODE_NOT_NULL` | — | ✓ |
| `PROCESS_UNIT_NOT_NULL` | — | ✓ |
| `SECE_GROUP_NOT_NULL` | — | — |
| `PSEUDO_NULL_NA_FORMAT` | ✓ | — |
| `PSEUDO_NULL_DATE_FORMAT` | — | — |
| `PROP_VALUE_ZERO_NOT_ALLOWED` | — | — |
| `EQUIP_MANUFACTURER_NOT_NULL` | — | ✓ |
| `EQUIP_MODEL_NOT_NULL` | — | ✓ |

**L3 — Topology & CrossField (6, check_type ≠ 'dsl', is_builtin=false):**
`PARENT_TAG_STATUS_VALID` (cross_table), `CYCLIC_PARENT_REFERENCE` (graph),
`SINGLE_PARENT_RULE` (aggregate), `TAG_MIN_DOC_LINK` (aggregate),
`IN_SERVICE_STARTUP_DATE` (cross_field), `DATE_SEQUENCE_VALID` (cross_field)

**L4 — Semantics (2, check_type='metadata', is_builtin=false):**
`DESC_FUNCTIONAL_NOT_CLASS_COPY`, `DESC_FUTURE_TAG_EXCEPTION`

### FK rules pattern

`*_FK_RESOLVED` rules use: `raw_field not_null AND output_col is_null`
→ fires when a raw value was provided but the JOIN to the reference table produced no match.
Raw fields are included in the export SQL SELECT but dropped by `transform_*` before CSV write.

### Migration History

| Migration | Date | Purpose |
|---|---|---|
| `migration_003_export_validation_rules.sql` | 2026-03-12 | Create tables + seed 42 base rules |
| `migration_004_fix_nan_strings_rule.sql` | 2026-03-13 | Fix `NO_NAN_STRINGS`: `icontains "nan"` → `matches_regex "(?i)^nan$"` (false-positive fix) |
| `migration_005_validation_rule_schema_v2.sql` | 2026-03-13 | ADD tier, category, check_type, source_ref, sort_order to rule table; tier/category/check_type to validation_result |
| `migration_005_update_existing_rules.sql` | 2026-03-13 | Backfill tier/category/check_type/source_ref on all 42 existing rules |
| `migration_005_new_validation_rules.sql` | 2026-03-13 | INSERT 27 new rules (L0×3, L1×8, L2×9, L3×6, L4×2) from gap analysis |
| `migration_006_property_value_validation_rules.sql` | 2026-03-13 | INSERT 10 rules for scopes 'tag_property' and 'equipment_property' (L0×4, L1×4, L2×2) |
| `migration_007_validation_rules_cleanup.sql` | 2026-03-13 | DELETE 5 rules (4 duplicates + DESC_NO_DOUBLE_SPACE); UPDATE 6 rules (typo fix, tune, engine extensions); INSERT 6 new rules (5 DSL + 1 aggregate metadata) |

### Key Code Locations

| File | Responsibility |
|---|---|
| `etl/tasks/export_validation.py` | DSL parser, evaluator, fix interpreter, load_validation_rules, run_full_scan, store_validation_results |
| `etl/tasks/export_pipeline.py` | run_export_pipeline orchestrator — extract → sanitize → validate → transform → write → audit |
| `etl/tasks/export_transforms.py` | clean_engineering_text(), sanitize_dataframe(), EIS column transforms |
| `etl/flows/export_tag_register.py` | Tag Register export (EIS seq 003, scope='tag') |
| `etl/flows/export_equipment_register.py` | Master Equipment Register export (EIS seq 004, scope='equipment') |
| `etl/flows/export_tag_properties.py` | Tag Property Values export (EIS seq 303, scope='tag_property') |
| `etl/flows/export_equipment_properties.py` | Equipment Property Values export (EIS seq 301, scope='equipment_property') |
| `etl/flows/export_area_register.py` | Area Register export (EIS seq 203, scope='area') |
| `etl/flows/export_process_unit.py` | Process Unit Register export (EIS seq 204, scope='process_unit') |
| `etl/flows/export_purchase_order.py` | Purchase Order Register export (EIS seq 214, scope='purchase_order') |
| `etl/flows/export_model_part.py` | Model Part Register export (EIS seq 209, scope='model_part') |
| `etl/flows/export_tag_class_properties.py` | Tag Class Properties export (EIS seq 307, scope='tag_class_property') |
| `sql/schema/schema.sql` | Canonical table definitions (single source of truth) |
| `docs/validation_rules_gap_analysis.md` | Full gap analysis vs QA spec; source for migration_005 rules |

---

## ADR-010: object_status Soft-Delete Value Discrepancy
- **Date**: 2026-03-16
- **Decision**: Canonical soft-delete value for `project_core.tag.object_status` is `'Inactive'`, not `'Deleted'`.
- **Reason**: Audit via MCP-server query confirmed actual data: 23 071 rows with `'Active'`, 1 034 rows with `'Inactive'`. Value `'Deleted'` does not exist in the table. The `sync_status` column uses `'Deleted'` to mark removed tags, while `object_status` transitions to `'Inactive'`. Documentation and `sql-standards.md` were incorrect.
- **Impact**: `docs/architecture.md` updated. `.claude/rules/sql-standards.md` updated. Export filters `WHERE object_status = 'Active'` remain correct — they already exclude `'Inactive'` rows.

## ADR-011: tag_status Canonical Values in Source Data
- **Date**: 2026-03-16
- **Decision**: `project_core.tag.tag_status` stores EIS-source values verbatim. Actual values confirmed via MCP: `'ACTIVE'` (uppercase), `'VOID'` (uppercase), `'ASB'`, `'AFC'`, `'Future'`, NULL.
- **Reason**: The validation rule `TAG_STATUS_VALID_VALUES` was written assuming EIS delivers lowercase `'Active'`, `'Void'`, `'Future'`, `'Hold'` — which does not match the real data. `'ASB'` and `'AFC'` are legitimate EIS project statuses not in the original rule. Normalization of tag_status requires business decision; deferred to separate task.
- **Impact**: Rule `TAG_STATUS_VALID_VALUES` will produce false-positive violations for all `'ACTIVE'`/`'VOID'` tags. No code change in this ADR — tracked as a separate fix task.

## ADR-009: Validation Rules Cleanup & Power Query Gap Closure
- **Date**: 2026-03-13
- **Decision**: Удалены 4 дублирующих правила (`PROCESS_UNIT_MANDATORY`, `AREA_CODE_EXPECTED`, `PO_CODE_NOT_VOID`, `TAG_MIN_ONE_DOCUMENT`) и устаревшее `DESC_NO_DOUBLE_SPACE`. Исправлена опечатка в `DISCIPLINE_FK_RESOLVED`. Расширен `clean_engineering_text()` на покрытие Unicode hyphens, en/em-dashes, MM² artefacts и consecutive spaces. Добавлены 3 новые fix-операции в DSL-движок (`normalize_na`, `normalize_boolean_case`, `normalize_uom_longform`). Вместо отдельных правил на каждый символ введено универсальное `NO_INVALID_CHARS` + `UNSET_VALUE_IN_ANY_FIELD` для покрытия всех полей всех отчётов.
- **Reason**: Ревью `docs/validation_rules_review_summary.md` выявило дублирование правил, опечатку, пробелы в покрытии Power Query логики из `ex-data-extractor-help.txt`. Структурные символы (дефисы, пробелы, MM²) должны устраняться единым pipeline, а не отдельными правилами.
- **Impact**: `migration_007`, `etl/tasks/export_validation.py` (`_fix_series`), `etl/tasks/export_transforms.py` (`clean_engineering_text`).

## ADR-008: Property Value Export Routing by mapping_concept
- **Date**: 2026-03-13
- **Decision**: `project_core.property_value` строки маршрутизируются в два отдельных EIS-файла на основе `ontology_core.class_property.mapping_concept`:
  - `ILIKE '%Functional%' AND NOT ILIKE '%common%'` → seq 303 (file `-010-`)
  - `ILIKE '%Physical%' AND NOT ILIKE '%common%'` → seq 301 (file `-011-`)
  - Строки с `mapping_concept = 'common'` из обоих файлов исключены — они уже присутствуют в Tag/Equipment Register.
  - Строки с `mapping_concept = 'Functional Physical'` попадают в оба файла одновременно (корректное поведение по спецификации CFIHOS).
- **Reason**: `mapping_concept` может содержать составные значения (`'Functional Physical'`), поэтому точное равенство неприемлемо — используется `ILIKE '%...%'`.
- **Impact**: новые файлы `etl/flows/export_tag_properties.py`, `etl/flows/export_equipment_properties.py`; новые transform-функции в `etl/tasks/export_transforms.py`; новые validation rule scope `'tag_property'` и `'equipment_property'` в `migration_006`.
