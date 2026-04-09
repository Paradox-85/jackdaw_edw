# EDW Jackdaw — Claude Code Guidelines

**Stack:** Prefect 3.0 | PostgreSQL (async) | Neo4j | Qdrant | Ollama | Pandas
**MCP:** context7 (tech docs) | pgedge (`https://ai-db.adzv-pt.dev/mcp/v1`)
**GitHub:** https://github.com/Paradox-85/jackdaw_edw
**References:** @docs/architecture.md @docs/file-specification.md

---

## 🔴 CRITICAL RULES
1. **Never invent** DB columns, config keys, library params — query pgedge MCP or ask
2. **Before ANY schema or architecture change** — validate against live DB via pgedge MCP or read `sql/schema/schema.sql`
3. **After ANY schema-related change** — ALWAYS update `sql/schema/schema.sql` in the same task and the same commit
4. **Database writes are FORBIDDEN** — NEVER modify the database directly: not via MCP, not via Python, not via Bash/psql. Database access is READ-ONLY only
5. **Session completion** — after debugging or implementation is complete, ALWAYS remind the user to run commit + push manually before ending the session
6. **Language** — ENGLISH ONLY: all code, SQL, comments, YAML, docs
7. **Responses to user in plans** — RUSSIAN ONLY
8. **Secrets** — never hardcode: use `os.getenv("DATABASE_URL")` or `.env` (never commit)

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
| Test coverage is low or feature just completed | suggest `/unit-test-expand etl/` |
| Documentation is scattered or outdated | suggest `/doc-refactor` |
| Complex multi-step task (new source, migration) | suggest `etl-orchestrator` subagent |
| No CI/CD pipeline yet | suggest `/setup-ci-cd` |
| End of debugging / implementation session | remind user to run manual `git status`, `git commit`, `git push` |

---

## MCP Usage (MANDATORY)

| Situation | Use |
|-----------|-----|
| Tech choice, lib API, framework | context7 — auto on keywords |
| DB schema, cardinality, data quality | pgedge — `query_database` / `get_schema_info` directly (never curl) |
| Architecture decision | pgedge first, then context7 — use `/model opus` |
| Any DB modification (INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/TRUNCATE) | FORBIDDEN — DB is read-only, change only code + `sql/schema/schema.sql` |

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
- [ ] If schema-related logic changed → `sql/schema/schema.sql` updated in the same commit
- [ ] No DB write paths used via MCP, Python, or Bash — read-only access only
- [ ] End of session: user reminded to commit + push manually
- [ ] DataFrame: `dtype=str, na_filter=False` · NaT→None before insert
- [ ] New tech → context7 · Architecture → pgedge + `schema-validator` subagent
- [ ] Errors: `get_run_logger()` not `print()`
