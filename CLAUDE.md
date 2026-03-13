# EDW for Jackdaw — Claude Code Context

Engineering Data Warehouse for the **Jackdaw** offshore project (North Sea, PLANT_CODE=`JDA`).
Ingests EIS Excel/CSV exports → structured PostgreSQL → EIS CSV outputs.

---

## Language Policy
- **Responses to user**: Russian only
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
docs/                 # Technical documentation — always read before changing architecture
```

---

## Documentation Index (docs/)

**Always read relevant docs BEFORE making changes. Always update relevant docs AFTER making changes.**

| File | Purpose | Read when... |
|---|---|---|
| `docs/architecture.md` | Data flow diagram, flow execution order, ADR log, key design decisions | Before any structural change to flows, schema, or domain logic |
| `docs/infrastructure.md` | Hardware, Proxmox/LXC layout, Docker services, networking (Tailscale/Caddy), AI/ML stack, storage paths | Before any infra, Docker, or path-related change |
| `docs/file-specification.md` | Full spec for all source XLSX inputs (MDR, MTR, Reference Data, CFIHOS RDL) and EIS CSV outputs — column mappings, processing rules, FK resolution | Before touching any ETL read/write/export logic |

> **Rule**: If `docs/` content contradicts the code after a change — update `docs/` to match code, not the other way around.
> **Rule**: Do not append contradictions — delete or replace outdated blocks.

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

## Doc Maintenance Protocol (MANDATORY)

After **every** code change or planning session, Claude MUST:

1. **Read** `docs/architecture.md` — check for conflicts with the change just made
2. **Update** the relevant `docs/` file(s):
   - New flow or task added → update `docs/architecture.md` (Data Flow section)
   - ETL logic changed (SCD, hashing, FK) → update `docs/logic-manifesto.md`
   - Source/output file format changed → update `docs/file-specification.md`
   - New Docker service or infra change → update `docs/architecture.md` (Docker Services table)
3. **Rules for doc updates**:
   - Delete or replace outdated blocks — do not append contradictions
   - Keep descriptions concise, in English, without loss of meaning
   - Add an ADR (Architecture Decision Record) entry in `docs/architecture.md` for any significant structural decision

**Format for ADR entries in architecture.md:**
```
## ADR-NNN: [Short Title]
- **Date**: YYYY-MM-DD
- **Decision**: What was decided
- **Reason**: Why
- **Impact**: Which files/tables/flows are affected
```

---

## Coding Rules (always loaded)
See `.claude/rules/` — loaded automatically:
`python-standards` · `sql-standards` · `etl-logic` · `audit-rules` · `export-eis`