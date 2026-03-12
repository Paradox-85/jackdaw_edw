# EDW for Jackdaw — Claude Code Context

Engineering Data Warehouse for the **Jackdaw** offshore project (North Sea, PLANT_CODE=`JDA`).
Ingests EIS Excel/CSV exports → structured PostgreSQL → EIS CSV outputs.

---

## Language Policy
- **Responses to user**: English only
- **Code** (Python, SQL, YAML, Bash, Cypher): all comments, docstrings, variable names in English
- No mixing: `# Extract tags` ✅ | `# Извлечь теги` ❌

---

## Stack
| Layer | Technology | Details |
|---|---|---|
| Orchestration | Prefect 3.0 | `prefect-server` + `prefect-services` + `prefect-worker` |
| Primary DB | PostgreSQL 16 (`engineering_core`) | container: `postgres_db:5432` |
| Graph | Neo4j | Tag↔Parent, Tag↔Doc impact chains |
| Vector | Qdrant | Semantic search on `property_value` |
| LLM | Ollama (RTX 3090, GPU) | Local inference, no internet |
| Transform | Pandas 2.x + SQLAlchemy 2.x | |
| DB GUI | DbGate | port 18978, db: `engineering_core` |

Full service list: `docker-compose.yml` in project root.

---

## Domain Objects
- **Tag** — engineering object, unique per plant (e.g. `JDA-21-LIT-101`)
- **Document** — project deliverable with unique `doc_number` (e.g. `JDAW-KVE-E-HX-2334-00001`)
- **Property Value** — EAV model: class → property → value (CFIHOS ontology)
- **SECE** — Safety Critical Element (`SAFETY_CRITICAL_ITEM_GROUP` in source)
- **Article** — vendor catalog item linked to tag via `article_id`

---

## Project Structure
```
etl/flows/            # Prefect @flow — orchestration entry points
etl/tasks/            # Prefect @task — atomic reusable units
etl/tasks/common.py   # load_config(), get_db_engine_url()
sql/schema/schema.sql # CANONICAL schema — only source of truth for table/column names
config/db_config.yaml # DB connection, file paths, schema names
data/current/         # Symlinks → /mnt/shared-data/ram-user/Jackdaw/
data/_history/        # Symlinks → historical snapshots
```

---

## Non-Negotiable Rules (always apply)
1. **Zero hallucination**: never invent columns or tables. Check `schema.sql` first.
2. **Schema prefix always**: `project_core.tag` — never bare `tag`
3. **FK resolution**: `lookup.get(value) if value else None` — never auto-create reference data
4. **Pandas read**: `dtype=str, na_filter=False` — always, no exceptions
5. **Audit**: every flow writing project data MUST log to `audit_core.sync_run_stats`
6. **SCD2**: every tag change MUST write to `audit_core.tag_status_history` (snapshot JSONB)
7. **Transactions**: `with engine.begin() as conn:` for all DML

---

## Flow Execution Order
```
seed_ontology → sync_tag_data → sync_tag_hierarchy → export_tag_register
```
`sync_tag_hierarchy` is always a second pass — runs after main UPSERT in same master flow.

---

## Reference Docs (load on demand with @)
- Architecture + infra: `@docs/architecture.md`
- Source file schemas (inputs): `@docs/source-files.md`
- EIS output schemas (reports): `@docs/report-files.md`

## Coding Rules (always loaded)
See `.claude/rules/` — loaded automatically:
`python-standards` · `sql-standards` · `etl-logic` · `audit-rules` · `export-eis`
