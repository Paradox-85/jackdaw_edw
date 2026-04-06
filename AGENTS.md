# AGENTS.md — Jackdaw EDW

## Stack
Prefect 3.0 | PostgreSQL async | Neo4j | Qdrant | Ollama
Python 3.10+ | SQLAlchemy 2.x | Pandas | Ruff | mypy

**References:** `docs/architecture.md` · `docs/file-specification.md` · `schema.sql`
**MCP:** `pgedge` (live DB) · `context7` (tech docs) · `playwright` (browser)

---

## Critical rules

1. **Never invent** DB columns, config keys, or library params — query pgedge MCP or ask
2. **Before ANY schema change** — validate against live DB via pgedge MCP
3. **After ANY schema change** — update `schema.sql` same commit
4. **Language** — ENGLISH: all code, SQL, comments, YAML, docs
5. **User responses** — RUSSIAN only
6. **Secrets** — `os.getenv()` only, never hardcode

---

## Context on demand

| Keywords | Load |
|----------|------|
| hash, SCD, sync_status, upsert, tag_history | `.opencode/context/etl-logic.md` |
| python, async, type hint, docstring | `.opencode/context/python-standards.md` |
| SQL, schema, UPSERT, CREATE TABLE, FK | `.opencode/context/sql-standards.md` |
| audit, log_entry, tag_status_history | `.opencode/context/audit-rules.md` |
| component, tsx, React, TanStack, shadcn | `.opencode/context/ui-standards.md` |
| EIS, export, seq | `.opencode/context/export-eis.md` |

---

## Agents

| Agent | Use for |
|-------|---------|
| `plan` | Analysis, spec writing, pgedge schema validation. Read-only. |
| `build` | Cloud execution (ZAI GLM). Token-conscious. ≤50 steps. |
| `local` | Local Qwen. Bulk generation, large files, no token pressure. |

**Subagents** (invoke via `@name`):
- `@etl-reviewer` — after any ETL task/flow file change
- `@schema-validator` — before/after schema changes
- `@etl-orchestrator` — complex multi-step tasks (new source, migration)

---

## Situation → action

| Situation | Action |
|-----------|--------|
| New data source | Plan agent → `@etl-orchestrator` |
| Schema change | Plan agent → `@schema-validator` → build/local |
| ETL file modified | Always invoke `@etl-reviewer` |
| Context > 70% | `/compact` then continue in new session |
| Large bulk generation | Switch to `local` agent |
| Architecture decision | Plan agent + pgedge MCP + `/model opus` |

---

## Code checklist

- [ ] Type hints + async/await on all functions
- [ ] SQL: schema-prefixed (`project_core.*`)
- [ ] FK: `.get(value) if value else None` + `_raw` + warning log
- [ ] SCD2 → `audit_core.tag_status_history` (old/new JSONB)
- [ ] Audit → `audit_core.sync_run_stats`
- [ ] `schema.sql` updated same commit
- [ ] No secrets in code
- [ ] DataFrame: `dtype=str, na_filter=False` · NaT→None before insert
- [ ] Errors: `get_run_logger()` not `print()`

---

## File layout

```

etl/flows/     etl/tasks/     sql/schema.sql (canonical)
config/        docs/          docs/plans/    (agent specs)
.opencode/agents/   .opencode/context/   .opencode/prompts/

```