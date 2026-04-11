# jackdaw_edw — Solution Architecture

> Detailed domain model, business logic, and module responsibilities.
> Context reference for planning and implementing new features.
> Last updated: 2026-04-11

***

## Purpose

Jackdaw EDW is a data engineering platform for oil & gas projects. It ingests
engineering tag master data from EIS (Engineering Information System) source files,
validates it against a CFIHOS-aligned ontology, resolves FK references to project
lookup tables, and produces certified EIS export registers in the required CSV format.
It also classifies incoming vendor review comments (CRS) using a deterministic
4-tier cascade, reducing manual classification workload.

Primary users: data engineers and EIS system administrators managing the tag register
lifecycle — from initial import through validation, export, and vendor comment resolution.

***

## Domain Model

### DB Schema Map

| Schema | Purpose | Key tables |
|---|---|---|
| `project_core` | Live project engineering data (SCD2) | `tag`, `document`, `property_value` |
| `ontology_core` | CFIHOS class/property definitions | `class`, `property`, `class_property`, `uom`, `uom_group`, `uom_alias`, `validation_rule` |
| `reference_core` | Project lookup tables (static references) | `area`, `process_unit`, `company`, `purchase_order`, `discipline`, `plant`, `site`, `article`, `model_part`, `sece` |
| `mapping` | Many-to-many associations (SCD2) | `tag_document`, `tag_sece`, `document_po` |
| `audit_core` | Audit trail, QA rules, CRS classification | `sync_run_stats`, `tag_status_history`, `export_validation_rule`, `validation_result`, `naming_rule`, `crs_comment`, `crs_llm_template_staging` |
| `app_core` | UI users and feedback | `ui_user`, `ui_feedback` |

### Core Concepts

**Tag** is the primary engineering object:
- Identified by `source_id` (immutable — maps 1:1 to source system row)
- Named by `tag_name` (immutable per business rule — changes flagged as `TAG_NAME_CHANGED`)
- Classified via `ontology_core.class` (e.g. `INSTRUMENT`, `VALVE`, `PIPELINE`)
- Carries `sync_status` (lifecycle of ETL) and `object_status` (`Active`/`Inactive`)
- Has FK links to area, process_unit, discipline, company, purchase_order, article, plant
- Live count: ~23,071 active tags (2026-04-10 sync)

**Property Value** is an EAV model:
- One row per (tag, class_property) pair in `project_core.property_value`
- Live counts: 88,009 Functional / 51,661 Physical / 9,890 Functional Physical (~149,560 total)
- `class_property.mapping_concept` determines EIS export routing:
  `ILIKE '%Functional%'` → seq 303 (file -010-);
  `ILIKE '%Physical%'` → seq 301 (file -011-);
  `'common'` → excluded (already in tag/equipment register columns)
- Values containing combined value+UoM ("490mm", "+60°C") are split during export transform

**Document Link** is an N:M association: `mapping.tag_document` links tags to MDR documents.
`mapping.document_po` links documents to purchase orders. SCD2 tracked.
Live count: 18,654 documents (unchanged since initial import).

**SECE** (Safety and Environmental Critical Element): `mapping.tag_sece` stores
the SECE group assignment for each tag. Classified via SECE reference table.

**CRS Comment** is a vendor review item: free-text observation against a specific tag
in the EIS register. Classified into `llm_category` (`CRS-C001`..`CRS-C229`) by the
4-tier cascade. Live count: 21,111 rows in `audit_core.crs_comment`.

***

## Data Architecture

### SCD2 Change Detection

SCD2 tables (carry `row_hash`): `project_core.tag`, `project_core.document`,
`project_core.property_value`, `mapping.tag_document`, `mapping.tag_sece`,
`mapping.document_po`, `audit_core.crs_comment`.

Algorithm per sync run:
1. Read source file with `dtype=str, na_filter=False` — preserves literal `"NA"` strings
2. Load FK lookup caches into memory (one bulk query per reference table)
3. Load existing record cache: `{source_id: (id, row_hash, sync_status)}`
4. For each source row: compute `MD5("|".join(all_field_values))`
5. Hash unchanged → `sync_status = 'No Changes'`, **zero DB writes** (performance critical)
6. Hash changed → UPDATE record fields + INSERT `audit_core.tag_status_history` JSONB snapshot
7. Source ID absent from source file → `sync_status = 'Deleted'`
8. New source ID → INSERT, `sync_status = 'New'`

**Why `na_filter=False`:** EIS source files contain literal `"NA"` strings for
"not applicable" fields. Pandas default parsing converts these to `float NaN`,
which becomes `"nan"` when written to DB — causing false positives in the
`NO_NAN_STRINGS` validation rule. Setting `na_filter=False` preserves `"NA"` as-is.

### FK Resolution Pattern

Every FK field has two columns:
- `*_raw` — source value verbatim (always populated from source data)
- FK UUID column — resolved via in-memory lookup cache loaded at run start

If lookup misses: `*_raw` is preserved, FK column = NULL, WARNING logged.
FKs are **never auto-created** — unresolved references must be fixed in reference_core first.

This pattern ensures export SQL can JOIN on the UUID FK while preserving the original
source value for audit and troubleshooting (`*_FK_RESOLVED` validation rules catch misses).

### TAG_NAME_CHANGED Detection

`source_id` must always map to the same `tag_name`. If `source_id` exists in DB but
`tag_name` differs from source, a `TAG_NAME_CHANGED` violation (Critical severity, `sync`
scope) is written to `audit_core.validation_result`. The tag continues to sync —
violation is **non-blocking**.

### Audit Layer

| Table | Purpose |
|---|---|
| `audit_core.sync_run_stats` | One row per flow run; INSERT on start, UPDATE on completion with counts (created, updated, unchanged, deleted, errors, exported) |
| `audit_core.tag_status_history` | JSONB snapshot of key fields before each tag change — enables full field-level audit trail |
| `audit_core.validation_result` | QA violations grouped by `session_id`; `is_resolved` flag for tracking fixes |
| `audit_core.export_validation_rule` | Rule catalogue: DSL conditions, fix expressions, tier (L0–L4), scope, check_type |
| `audit_core.naming_rule` | Regex-based naming convention rules per domain/category; loaded by `crs_text_generalizer` at flow start |

### Key Status Values (live DB confirmed)

`sync_status`: `'No Changes'` (dominant — 22,945 tags on 2026-04-10) · `'Extended'`
(property additions — 126 on 2026-04-10) · `'New'` / `'Updated'` / `'Deleted'`

`object_status` (ADR-010): `'Active'` (exported) · `'Inactive'` (soft-deleted).
`'Deleted'` does not exist — `sync_status='Deleted'` is used when source removes a row.

`tag_status` (ADR-011): stored verbatim from EIS — `'ACTIVE'` · `'VOID'` · `'ASB'` ·
`'AFC'` · `'Future'` · NULL. Normalization deferred (see ADR-011).

***

## Import Modules

### import_ontology

Populates `ontology_core` from CFIHOS master files. All inserts use
`ON CONFLICT DO NOTHING` — idempotent, safe to re-run after source updates.

Targets: `class`, `property`, `class_property` (with `mapping_concept`), `uom`,
`uom_group`, `uom_alias` (alternative UoM representations → canonical `symbol_ascii`,
e.g. `"DEG C"` → `"degC"`, `"bar(g)"` → `"bar(g)"`).

### import_reference

Populates `reference_core` from project-specific master files. Same idempotent pattern.
Targets: `area`, `process_unit`, `discipline`, `company`, `plant`, `site`, `project`,
`purchase_order`, `article`, `model_part`, `sece`.
**Must run before `import_tag_data`** — tag sync loads FK lookup caches from reference_core.

### import_tag_data

Main SCD2 sync of the engineering tag register:
1. SCD2 algorithm applied to `project_core.tag`
2. Every resolved FK loaded as in-memory dict at start (no per-row queries)
3. All FK misses logged as WARNING; tracked via `*_FK_RESOLVED` validation rules
4. `TAG_NAME_CHANGED` detection runs in same pass
5. `audit_core.sync_run_stats` updated with final counts

### sync_tag_hierarchy (second pass)

Separate flow that runs AFTER `import_tag_data`. Resolves `parent_tag_id` by
`tag_name` lookup. Separated because parent tags may not exist in DB until
the main sync inserts all new tags first.

### import_doc_data

Ingests MDR into `project_core.document` + N:M links:
`mapping.tag_document` and `mapping.document_po`.
SCD2 change detection on documents; N:M links rebuilt per sync.

### import_prop_data

Ingests property value EAV into `project_core.property_value`.
Records that add properties to an existing tag get `sync_status = 'Extended'`.
Routing by `class_property.mapping_concept` is resolved at export time, not import.

### import_master_sync (orchestrator)

Runs the full import sequence in order:
`import_ontology → import_reference → import_tag_data → sync_tag_hierarchy
→ import_doc_data → import_prop_data`

***

## Export Modules

### EIS Export Pipeline (`etl/tasks/export_pipeline.py`)

All export flows share a unified pipeline. Steps:

```
1. extract_fn(engine)
   → SQL query, WHERE object_status = 'Active', returns raw DataFrame

2. sanitize_dataframe()
   → encoding repair: mojibake (Â², â€œ), Unicode dashes, MM² artefacts
   → NaN → "" normalisation (IS_NULL checks in step 3 work on string columns)
   → MUST run before validation to avoid false ENCODING_ARTEFACTS violations

3. load_validation_rules(scope) + apply_builtin_fixes()
   → loads is_builtin=True, check_type='dsl' rules from export_validation_rule
   → scope IN ('common', <register_scope>) — both sets applied
   → auto-fix operations: normalize_pseudo_null, replace_nan, encoding_repair,
     replace, truncate, strip_edge_char, remove_char,
     normalize_na, normalize_boolean_case, normalize_uom_longform
   → violations collected; export NEVER aborted

4. transform_fn(fixed_df)
   → column rename and reorder to EIS spec column order
   → ACTION_STATUS / ACTION_DATE derivation
   → for files 010/011: _apply_value_uom_split()
     splits "490mm" → ("490","mm"), "+60°C" → ("+60","degC")
     UoM canonical form resolved via ontology_core.uom_alias (not hardcoded)
     Four regex patterns (_P1–_P4) handle structural split cases

5. write_csv()
   → sanitize_dataframe() second pass (transforms may reintroduce artefacts)
   → UTF-8 BOM encoding (utf-8-sig) — required for EIS system and Excel
   → filename: JDAW-KVE-E-JA-6944-00001-{seq}-{revision}.CSV

6. log_audit_end()
   → UPDATE audit_core.sync_run_stats (count_exported, end_time)
```

**Why second sanitize pass:** transform functions may concatenate strings or rename
columns in ways that reintroduce encoding artefacts. The second pass is idempotent.

**VALUE_UOM_COMBINED_IN_CELL rule** is `is_builtin=False` — it detects combined
value+UoM cells but does NOT fix them via DSL. The DSL engine works on a single
`pd.Series` and cannot write to two columns simultaneously; actual split happens in
`transform_fn` via `_apply_value_uom_split()`.

### EIS Register Summary

| Scope | EIS seq | File | Content |
|---|---|---|---|
| `tag` | 003 | `-003-` | Tag Register — all active tags |
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

`export_eis_data_deploy` orchestrates all EIS export flows in sequence.

***

## Validation Framework

Rules stored in `audit_core.export_validation_rule` (90 active). Two execution modes:

| Mode | When | Auto-fix | Results stored |
|---|---|---|---|
| Built-in | During every export run | Yes (if fix_expression defined) | Optional (`persist_violations=True`) |
| Full scan | On-demand audit | Never | Always to `audit_core.validation_result` |

**Tier classification (L0–L4) — live DB counts:**

| Tier | Name | check_types | Count | Builtin | Status |
|---|---|---|---|---|---|
| L0 | Foundation | dsl(7) + aggregate(1) + metadata(1) | 9 | 7 | ✅ Implemented |
| L1 | Syntax & Encoding | dsl(23) | 23 | 15 | ✅ Implemented |
| L2 | Completeness & Validity | dsl(39) + metadata(1) | 40 | 18 | ✅ Implemented |
| L3 | Topology & Cross-Reference | cross_table(9) + aggregate(3) + cross_field(2) + dsl(1) + graph(1) | 16 | 0 | 🔲 Planned |
| L4 | Semantics | metadata(2) | 2 | 0 | 🔲 Planned |

**DSL rule_expression operators:**

| Operator | Example | Notes |
|---|---|---|
| `contains "X"` | `* contains ","` | Case-sensitive substring match |
| `icontains "X"` | `PO_CODE icontains "-VOID"` | Case-insensitive |
| `max_length N` | `COMPANY_NAME max_length 30` | Violation if `len > N` |
| `is_null` | `EQUIPMENT_NUMBER is_null` | Matches NULL, `""`, `"none"` |
| `not_null` | `area_code_raw not_null` | Inverse of is_null |
| `matches_regex "pat"` | `TAG_STATUS matches_regex "^(?!Active).*"` | Python re, violation on match |
| `has_encoding_artefacts` | `* has_encoding_artefacts` | Detects mojibake, Win-1252 leakage |

FK rules pattern: `raw_field not_null AND output_col is_null` → fires when source
provided a value but JOIN to reference table produced no match.

**Key validation queries:**

```sql
-- Open violations by tier and severity
SELECT r.tier, r.scope, vr.severity, count(*) as violations
FROM audit_core.validation_result vr
JOIN audit_core.export_validation_rule r ON vr.rule_code = r.rule_code
WHERE vr.is_resolved = false
GROUP BY r.tier, r.scope, vr.severity
ORDER BY r.tier, vr.severity;

-- FK resolution failures (field empty in export CSV)
SELECT rule_code, count(*) as cnt
FROM audit_core.validation_result
WHERE is_resolved = false AND rule_code ILIKE '%_FK_%'
GROUP BY rule_code ORDER BY cnt DESC;

-- TAG_NAME_CHANGED violations (source system integrity issue)
SELECT object_name, violation_detail, run_time
FROM audit_core.validation_result
WHERE rule_code = 'TAG_NAME_CHANGED' AND is_resolved = false
ORDER BY run_time DESC;

-- Recent sync run summary
SELECT target_table, start_time, count_created, count_updated,
       count_unchanged, count_deleted, count_errors, count_exported
FROM audit_core.sync_run_stats
ORDER BY start_time DESC LIMIT 10;
```

***

## CRS Management

Classifies vendor review comments (CRS — Comment Response Sheet) against the
engineering tag register. Primary table: `audit_core.crs_comment` (21,111 rows;
all `status='RECEIVED'` as of 2026-04-08 — classification pipeline not yet run).

### Business Context

Vendor engineers submit free-text observations about specific tags (e.g. "Tag HIS0163
missing DESIGN_PRESSURE", "Document JDAW-KVE-... not linked"). Each comment must be
categorised into a `llm_category` (CRS-C001..CRS-C229) and a formal response drafted.
Manual categorisation of hundreds of comments per review cycle is the problem this
module solves.

### CRS Tables (code-referenced)

| Table | Purpose |
|---|---|
| `audit_core.crs_comment` | Main table: one row per comment. Tracks `status`, `llm_category`, `classification_tier`, `llm_category_confidence`, `deferred_reason` |
| `audit_core.crs_llm_template_staging` | Tier 3 results staged for human review before KB promotion; `ON CONFLICT (template_hash)` increments occurrence_count |
| `audit_core.naming_rule` | Tag/doc regex patterns loaded by `crs_text_generalizer` at startup; can be updated without code changes |

### 4-Tier Classification Cascade

Comments enter with `status='RECEIVED'`. Each tier either classifies (→ `IN_REVIEW`)
or defers (→ `DEFERRED`) or passes to the next tier.

**Tier 0 — Deterministic Pre-filter (~5–10% skipped)**

Pure Python + single batch `prefetch_tag_statuses()` DB call. Speed: ~500k records/sec.

Skip reasons (written to `deferred_reason`):
- `INFORMATIONAL` — comment matches phrases like "For information", "See attached",
  "FYI", "No action required", "Noted", "OK", "Acknowledged"; also wrapper rows
  from multi-comment groups with empty individual comment text
- `TAG_NOT_IN_EDW` — `tag_name` set but `tag_id` is NULL (unresolved in EDW)
- `TAG_INACTIVE` — `tag_status` is VOID/VOIDED/VOIDD/CANCELLED/INACTIVE
  (ASB is intentionally NOT skipped — valid operational status)
- `TAG_NO_STATUS` — `tag_status` is NULL (tag not finalised)
- `TAG_OBJECT_INACTIVE` — `object_status = 'Inactive'` in project_core.tag

**Tier 1 — KB Template Matching (~50–70% after warm-up, threshold 0.92)**

Matches normalised comment text against KB templates.
Speed: ~50k records/sec (one bulk DB query + in-memory fuzzy matching).

Text normalisation before matching:
- Doc numbers (`JDAW-KVE-E-JA-6944-00001-016`) → `DOCREF`
- Tag names (`HIS0163`, `JDA-SB-V3C-F001`) → `TAGREF`
- Standalone numbers → `NUM`; file extensions `.xlsx` removed

Matching:
1. Exact MD5 hash match (O(1) — dominant path after KB warm-up)
2. Fuzzy `SequenceMatcher` ratio ≥ 0.92 (domain-restricted pool)

After 3-4 batches, KB warms up and Tier 1 handles the majority of comments.
New Tier 3 results feed back into the KB via `crs_llm_template_staging`
(human review required before promotion to trusted templates).

**Tier 2 — Keyword Classifier (~15–20%)**

Two-pass deterministic classification. No DB, no LLM. Speed: ~200k records/sec.

Pass 1 — SheetRule (confidence 0.95): classify by `detail_sheet` column value:
- `"No Doc Reference"`, `"Missing Doc"` → `MISSING_DOCUMENT_LINK` (CRS-C031)
- `"Tag Description"` → `TAG_DESCRIPTION_ISSUE` (CRS-C002)
- `"Safety Critical"` → `SAFETY_CRITICAL_MISSING` (CRS-C013)
- `"From To Tag"` → `MISSING_FROM_TO_LINK` (CRS-C045)
- `"Plant Code"` → `WRONG_LOCATION` (CRS-C029)
- `"Tag Class"`, `"Wrong Class"` → `WRONG_TAG_CLASS` (CRS-C004)
- `"Duplicate"` → `DUPLICATE_TAG` (CRS-C016)
- `"Not Found"` → `TAG_NOT_FOUND` (CRS-C011)

Pass 2 — KeywordRule (confidence 0.85): regex against comment text.
Covers: `MISSING_DOCUMENT_LINK`, `TAG_NOT_FOUND`, `MISSING_PROPERTY`,
`WRONG_TAG_CLASS`, `TAG_DESCRIPTION_ISSUE`, `SPELLING_ERROR`,
`MISSING_FROM_TO_LINK`, `SAFETY_CRITICAL_MISSING`, `WRONG_LOCATION`,
`DUPLICATE_TAG`, `WRONG_TAG_STATUS`.

**Group-by optimisation:** Tier 2 groups comments by generalised error pattern
(tag names and doc numbers replaced with `<TAG>` / `<DOC>` placeholders via
`crs_text_generalizer.generalize_comment()`). Classification runs ONCE per unique
template and is broadcast to all rows in the group — O(M) not O(N).

**Tier 2.5 — Benchmark Matcher**

Matches against `audit_core.crs_benchmark_example` (gold standard examples curated
manually). Speed: ~1–2k records/sec (`difflib.SequenceMatcher` + wildcard patterns
ending with `%`). Guard: `1ooN` advisory voting notation overridden to
`NEEDSNEWCATEGORY` regardless of benchmark match. Graceful degradation if table missing.

**Tier 3 — Qwen3 LLM (~5–10%)**

Called only for comments that passed all previous tiers unmatched. Uses local Ollama
instance (Qwen3 model, thinking disabled). Batch size 32 — reduces Ollama overhead
~85% vs one-by-one calls. Valid categories: CRS-C001..CRS-C229 (229 codes).

Result routing: `confidence ≥ 0.7` → `IN_REVIEW`; `< 0.7` → `DEFERRED`.
Tier 3 results staged to `crs_llm_template_staging` (min_confidence 0.85,
excludes `OTHER`/`GENERAL_COMMENT`). Human approves → promotes to KB template table.

### CRS Status Lifecycle

```
RECEIVED → [Tier 0] → DEFERRED (informational / inactive tag)
         → [Tier 1] → IN_REVIEW (KB match >= 0.92)
         → [Tier 2] → IN_REVIEW (sheet / keyword match)
         → [Tier 2.5] → IN_REVIEW (benchmark match)
         → [Tier 3] → IN_REVIEW (LLM confidence >= 0.7)
                    → DEFERRED  (LLM confidence < 0.7)
IN_REVIEW → [human review] → RESOLVED / APPROVED / CLOSED
```

### Key CRS Queries

```sql
-- Classification coverage by tier
SELECT classification_tier, status, count(*) as cnt
FROM audit_core.crs_comment
GROUP BY classification_tier, status ORDER BY classification_tier;

-- Top categories (what vendors flag most)
SELECT llm_category, count(*) as cnt
FROM audit_core.crs_comment
WHERE status != 'DEFERRED'
GROUP BY llm_category ORDER BY cnt DESC LIMIT 15;

-- Unresolved backlog by category
SELECT llm_category, count(*) as pending
FROM audit_core.crs_comment
WHERE status = 'IN_REVIEW'
GROUP BY llm_category ORDER BY pending DESC;

-- Staging entries pending human review
SELECT suggested_category, occurrence_count, confidence, last_seen_at
FROM audit_core.crs_llm_template_staging
WHERE object_status = 'PendingReview'
ORDER BY occurrence_count DESC;
```

***

## Adding New Functionality

| Goal | Where to start |
|---|---|
| New import source | `etl/flows/` new flow + `etl/tasks/` task + `sql/schema/schema.sql` |
| New EIS export field | Update SQL extract query + `export_transforms.py` transform function |
| New reference table | `reference_core` schema + `import_reference` + FK in `project_core.tag` + `*_FK_RESOLVED` validation rule |
| New validation rule (L0–L2) | INSERT into `audit_core.export_validation_rule` with `check_type='dsl'`; add migration file |
| New validation rule (L3) | Implement custom executor in `export_validation.py`; update `check_type` routing |
| New ontology class/property | `import_ontology` + `ontology_core.class` + `class_property` rows + `mapping_concept` |
| New CRS category | Add to Tier 2 `SHEET_RULES` / `KEYWORD_RULES` + seed KB template |
| New CRS skip reason | Add to Tier 0 `_INFO_PATTERN` or `_SKIP_STATUSES` constant |
| Schema change | `/schema-change` → `sql/schema/schema.sql` + migration file in same commit |
| New UI page | `ui/pages/` new page + `ui/app.py` nav registration |

***

## Active ADRs

| ADR | Decision |
|---|---|
| ADR-008 | Property values routed by `mapping_concept`: Functional → seq 303 (-010-), Physical → seq 301 (-011-); `'common'` excluded from property registers |
| ADR-009 | Validation cleanup: removed duplicates, unified `NO_INVALID_CHARS`, extended DSL with `normalize_na`, `normalize_boolean_case`, `normalize_uom_longform` fix ops |
| ADR-010 | `object_status` soft-delete = `'Inactive'` (not `'Deleted'`); export filter `WHERE object_status = 'Active'` is correct |
| ADR-011 | `tag_status` stored verbatim from EIS: `'ACTIVE'`/`'VOID'` uppercase, `'ASB'`/`'AFC'` project-specific; normalization deferred |
| ADR-012 | UI v0.3.0: hidden LLM Chat (Phase 3), CRS Assistant active, ETL Import → Home Quick Sync; added Tag Register page |
