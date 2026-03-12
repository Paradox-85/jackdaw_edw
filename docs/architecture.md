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
export_tag_register flow
        ↓  Reverse ETL → EIS CSV (UTF-8 BOM, seq 003)

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

### export_tag_register / export_equipment_register

Both flows implement the same pipeline:

```
extract (SQL → raw DataFrame)
    ↓
sanitize_dataframe()          — strip encoding artefacts (Â², mojibake, NaN strings)
    ↓
apply_builtin_fixes()         — DSL-driven auto-fixes from export_validation_rule table
    ↓
transform_*()                 — rename columns, format dates, enforce EIS column order
    ↓
write_csv()                   — sanitize_dataframe() again (idempotent) → UTF-8 BOM CSV
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
| **Built-in** | During export generation | Yes (if fix_expression defined) | Only in flow logs |
| **Full scan** | On-demand audit run | Never | `audit_core.validation_result` |

**Built-in mode** (`apply_builtin_fixes`): applies only `is_builtin=true` rules. If a rule has `fix_expression`, the fix is applied to the in-memory DataFrame — the database value is never modified. The corrected value goes into the CSV. If a rule has no `fix_expression` and `is_blocking=true`, the violation is logged as ERROR (the field will be empty in the report due to unresolved FK). **Export is never aborted** in either case.

**Full scan mode** (`run_full_scan`): applies all active rules for the target scope. No fixes are applied. Every violation is collected and bulk-inserted into `audit_core.validation_result` with session grouping.

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
    severity        TEXT NOT NULL DEFAULT 'Warning', -- 'Critical' | 'Warning' | 'Info'
    object_status   TEXT NOT NULL DEFAULT 'Active'
)
```

`scope` controls which exports load the rule:
- `common` — loaded by all export flows (tag + equipment)
- `tag` — tag register export only
- `equipment` — equipment register export only
- `sync` — sync-time rules (e.g. TAG_NAME_CHANGED); not evaluated via DSL

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
    original_value   TEXT NULL,              -- raw violating value
    is_resolved      BOOLEAN NOT NULL DEFAULT false
)
```

Indexes: `idx_val_result_session (session_id)`, `idx_val_result_object_id (object_id)`

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
| `contains "X"` | `* contains ","` | case-sensitive substring |
| `icontains "X"` | `* icontains "nan"` | case-insensitive substring |
| `max_length N` | `COMPANY_NAME max_length 30` | violation if `len(value) > N` |
| `is_null` | `EQUIPMENT_NUMBER is_null` | matches NULL, empty string, `"none"` |
| `not_null` | `area_code_raw not_null` | inverse of is_null |
| `matches_regex "pat"` | `* matches_regex "\\d+,\\d+"` | Python re, violation on match |
| `has_encoding_artefacts` | `* has_encoding_artefacts` | detects UTF-8 mojibake and Win-1252 byte leakage |

`AND` requires both sub-clauses to be true on the same row (used for FK checks: `raw_field not_null AND resolved_col is_null`).

### DSL — fix_expression (auto-fix for built-in mode)

| fix_expression | Action |
|---|---|
| `replace "X" "Y"` | replace all occurrences of X with Y |
| `replace_nan` | replace literal `nan`/`NaN` strings with empty string |
| `remove_char "X"` | remove all occurrences of character X |
| `truncate N` | truncate string to at most N characters |
| `encoding_repair` | apply `clean_engineering_text()` from export_transforms — repairs mojibake, removes control chars |

Fix is applied to the column identified by the rule's `col_spec`. For `AND` clauses and wildcard rules, fix is applied to all object columns (`*`).

### Seed Rules (migration_003)

| rule_code | scope | is_builtin | is_blocking | severity | fix |
|---|---|---|---|---|---|
| `NO_COMMA_IN_VALUES` | common | ✓ | ✓ | Warning | `replace "," ";"` |
| `NO_NAN_STRINGS` | common | ✓ | ✓ | Warning | `replace_nan` |
| `NO_INVALID_CHARS` | common | ✓ | — | Warning | `remove_char "<"` |
| `DECIMAL_DOT_SEPARATOR` | common | — | — | Warning | — |
| `COMPANY_NAME_MAX_30` | common | ✓ | — | Warning | `truncate 30` |
| `TAG_DESC_MAX_255` | common | ✓ | — | Warning | `truncate 255` |
| `ENCODING_ARTEFACTS` | common | ✓ | — | Info | `encoding_repair` |
| `PLANT_FK_RESOLVED` | common | ✓ | ✓ | Warning | — |
| `AREA_FK_RESOLVED` | tag | — | — | Warning | — |
| `CLASS_FK_RESOLVED` | tag | ✓ | ✓ | Warning | — |
| `PROCESS_UNIT_FK_RESOLVED` | tag | ✓ | ✓ | Warning | — |
| `DESIGN_CO_FK_RESOLVED` | tag | ✓ | ✓ | Warning | — |
| `PO_FK_RESOLVED` | tag | ✓ | ✓ | Warning | — |
| `ARTICLE_FK_RESOLVED` | tag | ✓ | ✓ | Warning | — |
| `PARENT_TAG_FK_RESOLVED` | tag | ✓ | ✓ | Warning | — |
| `DISCIPLINE_FK_RESOLVED` | tag | — | — | Warning | — |
| `EQUIP_NO_NOT_NULL` | equipment | — | — | Critical | — |
| `MODEL_PART_FK_RESOLVED` | equipment | ✓ | ✓ | Warning | — |
| `MANUFACTURER_FK_RESOLVED` | equipment | ✓ | ✓ | Warning | — |
| `VENDOR_FK_RESOLVED` | equipment | ✓ | ✓ | Warning | — |
| `TAG_NAME_CHANGED` | sync | — | — | Critical | — |

FK rules (`*_FK_RESOLVED`) use the pattern: `raw_field not_null AND output_col is_null` — fires when a raw value was provided but the JOIN to the reference table produced no match. Raw fields are included in the export SQL SELECT but dropped by `transform_*` before CSV write (not in `_TAG_REGISTER_COLUMNS` / `_EQUIPMENT_REGISTER_COLUMNS`).

`EQUIP_NO_NOT_NULL` and `DISCIPLINE_FK_RESOLVED` are full-scan only (`is_builtin=false`) because the export SQL already filters out those rows.

### is_blocking Semantics

`is_blocking` describes visible data impact in the report — it does **not** abort the export.

| is_blocking | fix_expression | Outcome |
|---|---|---|
| true | defined | fix applied → field correct in report → log INFO |
| true | NULL | FK unresolved → field empty in report (NULL from JOIN) → log ERROR |
| false | defined | fix applied → log WARNING |
| false | NULL | field may be empty → log WARNING |

`count_errors` in `audit_core.sync_run_stats` reflects the total count of `is_blocking` violations with no fix.
