# EDW Jackdaw — Claude Code Guidelines

**Stack:** Prefect 3.0 | PostgreSQL (async) | Neo4j | Qdrant | Ollama | Pandas
**MCP:** context7 (tech docs) | pgedge (`https://ai-db.adzv-pt.dev/mcp/v1`)
**GitHub:** https://github.com/Paradox-85/jackdaw_edw
**References:** @docs/architecture.md @docs/file-specification.md

---

## 🔴 CRITICAL RULES
1. **Never invent** DB columns, config keys, library params — query pgedge MCP or ask
2. **Before ANY schema/architecture change** — validate against live DB via pgedge MCP
3. **After any schema change** — update `schema.sql` immediately (same commit)
4. **Language** — ENGLISH ONLY: all code, SQL, comments, YAML, docs
5. **Responses to user in plans** — RUSSIAN ONLY
6. **Secrets** — never hardcode: use `os.getenv("DATABASE_URL")` or `.env` (never commit)

---

## 📚 Context on Demand
| Keywords in conversation | Rule loaded |
| :-- | :-- |
| hash, SCD, sync_status, upsert, tag_history | `rules/etl-logic.md` |
| python, async, docstring, clean_string, type hint | `rules/python-standards.md` |
| SQL, schema, UPSERT, CREATE TABLE, FK | `rules/sql-standards.md` |
| audit, log_entry, tag_status_history | `rules/audit-rules.md` |
| EIS, export, seq, sequence | `rules/export-eis.md` |
| component, tsx, React, TanStack, shadcn, Tailwind | `rules/ui-standards.md` |
| MCP fails, unavailable, empty response | `rules/mcp-decision.md` |

---

## 🗂️ Available Commands & Agents

| Situation | Action |
|-----------|--------|
| Adding new data source | suggest `/new-source` |
| ANY database schema change | suggest `/schema-change` + **launch `schema-validator` subagent** |
| Prefect flow fails | suggest `/sync-debug` |
| Validate schema design | **launch `schema-validator` subagent** |
| After writing/modifying ETL task or flow file | suggest `etl-reviewer` subagent |
| Context approaching 70% | suggest `/compact-edw` |
| Before first commit / after major changes | suggest `/push-all` |
| Test coverage is low or feature just completed | suggest `/unit-test-expand etl/` |
| Documentation is scattered or outdated | suggest `/doc-refactor` |
| Complex multi-step task (new source, migration) | suggest `etl-orchestrator` subagent |
| No CI/CD pipeline yet | suggest `/setup-ci-cd` |

---

## MCP Usage (MANDATORY)

| Situation | Use |
|-----------|-----|
| Tech choice, lib API, framework | context7 — auto on keywords |
| DB schema, cardinality, data quality | pgedge — `query_database` / `get_schema_info` directly (never curl) |
| Architecture decision | pgedge first, then context7 — use `/model opus` |

---

## Model Selection & Session

| Task | Model | Command |
|------|-------|---------|
| Debug, logs, syntax | Haiku 3.5 | `/model haiku` |
| ETL, SQL, Python, docs | Sonnet 3.5 | `/model sonnet` ← default |
| Architecture, SCD, optimization | Opus 4.6 | `/model opus` + `ultrathink` |

`/compact-edw` · `/compact` · `/clear` · `/rewind` · `/context` · `/rename`

---

## File Layout
`etl/flows/` · `etl/tasks/` · `sql/schema.sql` (canonical) · `config/default.yaml` · `docs/`
`.claude/`: `commands/` · `rules/` · `skills/` · `agents/` · `settings.json`

---

## Code Review Checklist
- [ ] Type hints + async/await · SQL schema-prefixed · FK: `.get()` + `_raw` + warning log
- [ ] SCD2 → `audit_core.tag_status_history` (old/new JSONB) · Audit → `audit_core.sync_run_stats`
- [ ] `schema.sql` updated same commit · No secrets · Hierarchy AFTER main sync
- [ ] DataFrame: `dtype=str, na_filter=False` · NaT→None before insert
- [ ] New tech → context7 · Architecture → pgedge + `schema-validator` subagent
- [ ] Errors: `get_run_logger()` not `print()`
