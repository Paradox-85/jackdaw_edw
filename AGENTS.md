# AGENTS.md — Jackdaw EDW

**Stack:** Prefect 3.0 · PostgreSQL (async) · Neo4j · Qdrant · Ollama  
**Python:** 3.10+ · SQLAlchemy 2.x · async/await  
**Hardware:** Ryzen 7 7700 · RTX 3090 (Ollama GPU)  
**Data:** `./data/` → symlinks to `/mnt/shared-data/`  
**GitHub:** https://github.com/Paradox-85/jackdaw_edw

---

## Non-Negotiable Rules

1. Never invent DB columns, config keys, or lib params — query pgedge MCP or ask
2. Schema changes → validate via pgedge MCP first, update `schema.sql` in same commit
3. All code, SQL, YAML, comments, docs — **English only**
4. Secrets via `os.getenv()` or `.env` — never hardcode, never commit
5. FK failures → use `.get()` + preserve raw value in `_raw` column + log warning
6. `get_run_logger()` for errors — never `print()`

---

## Dev Environment

```bash
pip install -r requirements.txt
cp .env.example .env

# Symlinks
ln -s /mnt/shared-data/raw ./data/raw
ln -s /mnt/shared-data/processed ./data/processed

# Services
docker-compose up -d

# Schema
psql -U edw_user -d edw_db < sql/schema.sql

# Prefect
prefect server start
prefect deploy --entrypoint etl/flows/tag_sync.py:main_pipeline --name "tag-sync-master"
```

---

## Testing

```bash
pytest etl/ -v                          # all unit tests
pytest tests/integration/ -v           # integration tests
pytest etl/ --cov=etl --cov-report=html

black etl/ && ruff check --fix etl/ && mypy etl/ --strict
pre-commit run --all-files
```

**Before any commit:** all tests green · `schema.sql` updated · no secrets in diff.

---

## Code Standards

### Python
```python
async def sync_tags(session: AsyncSession, tags: list[dict]) -> int:
    """Sync tags with hash comparison for SCD tracking."""
    ...
```
- Type hints mandatory · Black (line 100) · Ruff strict · single quotes · parameterized SQL

### SQL
```sql
-- Always schema-prefixed, never bare table names
INSERT INTO project_core.tag_history (id, tag_id, old_value, new_value, status, created_at)
VALUES (gen_random_uuid(), $1, $2, $3, 'Updated', CURRENT_TIMESTAMP);
```
- UUID PKs · `TIMESTAMP WITH TIME ZONE` always · schema prefix always

### SCD Type 2
- Hash-based UPSERT: write only if MD5 differs
- Every tag change → `audit_core.tag_status_history` (old/new JSONB)
- Hierarchy sync AFTER main sync completes

---

## Commit Format

```
[module] Brief description (50 chars max)

- What changed
- Why it changed
- Breaking changes (if any)
```

Modules: `etl/tasks` · `etl/flows` · `sql/schema` · `infra/docker` · `docs`

---

## Skills (load on demand)

| Keywords | Skill |
|----------|-------|
| hash, SCD, upsert, tag_history | `.claude/skills/scd2-rules/` |
| prefect, flow, task, deploy | `.claude/skills/prefect-etl-patterns/` |
| SQL, schema, FK, CREATE TABLE | `.claude/skills/edw-sql-schema/` |
| tsx, React, TanStack, shadcn | `.claude/skills/ui-react/` |
| component, design, Tailwind | `.claude/skills/frontend-design/` |

---

## MCP Usage

| Need | Tool |
|------|------|
| DB schema, cardinality, data quality | `pgedge` → `query_database` / `get_schema_info` |
| Tech docs, lib API, framework | `context7` (auto on keywords) |
| Architecture decision | pgedge first → context7 → Opus + ultrathink |

**Never use curl for DB queries** — pgedge MCP only.

---

## Debugging

```bash
# Prefect
tail -f logs/prefect.log | grep ERROR
prefect flow-run inspect <run-id>

# PostgreSQL
psql -U edw_user -d edw_db -c "SELECT * FROM pg_stat_activity;"

# Qdrant
curl http://localhost:6333/collections

# Ollama / GPU
ollama list && nvidia-smi
```

**Common issues:**
- `TooManyConnectionsError` → reduce `pool_size` or enable pgbouncer
- CUDA OOM → switch to smaller Ollama model (`neural-chat` not `llama2-70b`)
- Neo4j slow traversals → `CREATE INDEX ON :Tag(id)`