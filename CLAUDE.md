# EDW Jackdaw — Claude Code Guidelines

**Stack:** Prefect 3.0 | PostgreSQL (async) | Neo4j | Qdrant | Ollama | Pandas  
**MCP:** context7 (tech docs) | pgedge (`https://ai-db.adzv-pt.dev/mcp/v1`)  
**GitHub:** https://github.com/Paradox-85/jackdaw_edw

**References:** @docs/architecture.md | @docs/infrastructure.md | @sql/schema.sql

---

## 🔴 CRITICAL RULES (5)

1. **Never invent** DB columns, config keys, library params — query pgedge MCP or ask
2. **Before ANY schema/architecture change** — validate against live DB via pgedge MCP
3. **After any schema change** — update `schema.sql` immediately (same commit)
4. **Language** — ENGLISH ONLY: all code, SQL, comments, YAML, docs
5. **Responses to user** - RUSSIAN ONLY
6. **Secrets** — never hardcode: use `os.getenv("DATABASE_URL")` or `.env` (never commit)

---

## MCP Usage (MANDATORY)

| Situation | Use | Invoke |
|-----------|-----|--------|
| Tech choice, lib API, framework comparison | context7 | Auto-consulted for keywords |
| DB schema, cardinality, data quality check | pgedge | Query via MCP or ask Claude |
| Architecture decision | pgedge first, then context7 | Use `/model opus` + validation |

**Key URLs:**
- pgedge: `https://ai-db.adzv-pt.dev/mcp/v1`
- GitHub: `https://github.com/Paradox-85/jackdaw_edw`

---

## Model Selection

| Task | Model | Command |
|------|-------|---------|
| Debug, logs, syntax | Haiku 3.5 | `/model haiku` |
| ETL, SQL, Python, docs (everyday) | Sonnet 3.5 | `/model sonnet` ← default |
| Architecture, SCD strategy, optimization | Opus 4.6 | `/model opus` with `ultrathink` |

**Session Management:**
- `/compact` — Compact context at ~50% usage
- `/clear` — Clear context when switching tasks
- `/rewind` (Esc Esc) — Undo recent messages
- `/context` — Check current usage
- `/rename` — Label important sessions for reference

---

## Code Standards

### Python (Mandatory)
Type hints required, async/await for all PostgreSQL operations, Google-style docstrings.
```python
async def sync_tags(session: AsyncSession, tags: List[dict]) -> int:
    """Sync tags via SCD2 hash comparison.
    Args: session: AsyncSession. tags: list of tag dicts.
    Returns: upserted row count.
    """
    async with engine.begin() as conn:
        return (await conn.execute(upsert_stmt)).rowcount
```

### Pandas (Always)
Always `dtype=str, na_filter=False`; `None` before DB insert:
```python
df = pd.read_csv("data.csv", dtype=str, na_filter=False)
df["col"] = df["col"].str.strip().where(df["col"].notna(), None)
```

### SQL (Always Required)
Schema-prefix mandatory (`project_core.`, `audit_core.`, `mapping.`, `ontology_core.`); UUID via `gen_random_uuid()`; timestamps as `TIMESTAMP WITH TIME ZONE`.
```sql
SELECT t.id, t.tag_code FROM project_core.tag t
LEFT JOIN project_core.tag_parent p ON t.id = p.child_id
-- CREATE TABLE: id UUID PRIMARY KEY DEFAULT gen_random_uuid(), created_at TIMESTAMPTZ DEFAULT NOW()
```
→ Full DDL patterns in `.claude/skills/edw-sql-schema/SKILL.md`

### Foreign Key Resolution (Always)
Use `.get(key)` with None fallback; log warning on miss; preserve raw value in `_raw` column.
```python
company_id = lookup.get(company_name)
if not company_id and company_name:
    logger.warning(f"FK miss: {company_name}")
    record["_raw_company"] = company_name  # preserve; insert NULL FK
```

---

## Domain Logic — SCD Type 2 (Slowly Changing Dimensions)
Every change to `project_core.tag` must be logged to `project_core.tag_history` with status `New|Updated|Deleted`.

### Hash Computation (Mandatory)
```python
def compute_row_hash(row: dict) -> str:
    return md5(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()

if new_hash != existing_hash:
    await upsert_tag(db, record)
    await log_change(db, record_id, "Updated")
```

### Tag History Table Pattern
```sql
INSERT INTO project_core.tag_history (id, tag_id, old_value, new_value, status, created_at)
VALUES (
    gen_random_uuid(),
    $1,  -- tag_id (from project_core.tag.id)
    $2,  -- old_value (JSONB row snapshot)
    $3,  -- new_value (JSONB row snapshot)
    'Updated',  -- status: New | Updated | Deleted
    CURRENT_TIMESTAMP
);
```

### Audit Logging (Always)
```sql
INSERT INTO audit_core.log_entry (operation, table_name, rows_affected, success, error_message, created_at)
VALUES ('INSERT', 'project_core.tag', 1000, true, NULL, CURRENT_TIMESTAMP);
```

### Tag Hierarchy Resolution (Mandatory Order)
**CRITICAL:** Tag-to-Parent resolution must run **AFTER** main tag sync, **WITHIN SAME Prefect flow**.

```python
@flow(name="tag-sync-master")
async def sync_tags_master(config: dict):
    """Master ETL flow: strict task ordering required.
    
    Order is critical:
    1. Sync main tags (creates FK targets in project_core.tag)
    2. Resolve parent-child (references must exist first)
    3. Log changes (audit trail to tag_history + audit_core.log_entry)
    """
    # Step 1: Extract + Transform + Load main tags
    sync_result = await task_sync_tags(config["source_data"])
    
    # Step 2: Resolve parent relationships (after tags exist!)
    hierarchy_result = await task_resolve_hierarchy(config["hierarchy_mappings"])
    
    # Step 3: Log all changes
    history_result = await task_log_changes(sync_result)
    
    return {
        "tags_synced": sync_result,
        "hierarchy_resolved": hierarchy_result,
        "changes_logged": history_result
    }
```

## File Layout (Actual Project Structure)

```
edw/
├── data/            → /mnt/shared-data/{raw,processed,archive}
├── etl/flows/       tag_sync.py (entry: main_pipeline)
├── etl/tasks/       tag_sync.py (fetch, validate, upsert, hierarchy, log)
├── sql/schema.sql   canonical schema — check before any DB change
├── config/default.yaml
├── docs/            logic-manifesto.md | environment-setup.md
└── .claude/
    ├── settings.json
    ├── commands/    /new-source · /schema-change · /sync-debug
    ├── skills/      scd2-rules · edw-sql-schema · prefect-etl-patterns
    └── agents/      schema-validator (isolated, use: "use subagents to validate schema")
```

---

## Code Review Checklist

- [ ] **Type hints** on all functions; **async/await** correct (no blocking calls in async)
- [ ] **SQL schema-prefixed** (`project_core.`, `audit_core.`, `mapping.`, `ontology_core.`)
- [ ] **FK resolution:** `.get()` + None + warning log + `_raw` column preservation
- [ ] **SCD2 changes** logged to `project_core.tag_history` with `old_value` + `new_value` JSONB
- [ ] **Audit logged** to `audit_core.log_entry` (operation, table, rows, success)
- [ ] **`schema.sql` updated** in same commit if any DB change
- [ ] **Verification:** `pg_dump -d edw_db -s` diff clean vs `sql/schema.sql` (no drift)
- [ ] **No secrets** in code (`.env*`, `ssh/`, `logs/prod/` not exposed)
- [ ] **Tag hierarchy** resolved AFTER main sync (same Prefect flow, separate task)
- [ ] **DataFrame loads** with `dtype=str, na_filter=False`; NaT → None before insert
- [ ] **New tech used** → context7 consulted; **architecture change** → pgedge validated
- [ ] **Error handling** with logging via `get_run_logger()` (not `print()`)

---