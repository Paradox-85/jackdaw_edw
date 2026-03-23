# Jackdaw EDW — Administrator Help

> Version: 1.0.0 | Updated: 2026-03-23

---

## UI Navigation

The Control Center is a Streamlit application at `https://jackdaw.edw.adzv-pt.dev`.
All users must authenticate before accessing any page. Authentication is DB-backed via `app_core.ui_user` (bcrypt, viewer/admin roles).

### Available Pages

| Page | Role | Description |
|---|---|---|
| **Home** | Viewer + Admin | KPI dashboard (active tags, documents, last sync, open violations), service health, recent Prefect flow runs, Quick Sync trigger |
| **EIS Management** | **Admin only** | Trigger EIS export flows via Prefect, monitor deployment status, download exported CSV files |

> All other pages (Tag Register, Reports, Tag History, Validation, Help, Feedback, LLM Chat, CRS Assistant) are preserved in `ui/_hidden/` and are scheduled for Phase 2 / Phase 3 release.

### RBAC Rules

| Element | Viewer | Admin |
|---|---|---|
| Home KPIs and service health | visible | visible |
| Quick Sync trigger | hidden | visible |
| EIS Management page | hidden | visible |
| Prefect UI / DbGate links | hidden | visible |
| Sign out button | visible | visible |

---

## EIS Export — How It Works

### Triggering an Export

1. Navigate to **EIS Management** (admin login required)
2. Select one or more export flows from the list
3. Enter the document revision code (format: `[A-Z]\d{2}`, e.g. `A36`)
4. Click **Run Export** — the flow is triggered via the Prefect API

Alternatively, trigger from the command line on PVE:

```bash
prefect flow run -n "export-tag-register-deployment"
prefect flow run -n "export-equipment-register-deployment"
```

### Available Export Flows

| Flow | EIS Seq | Output file template |
|---|---|---|
| Tag Register | 003 | `JDAW-KVE-E-JA-6944-00001-003-{rev}.CSV` |
| Equipment Register | 004 | `JDAW-KVE-E-JA-6944-00001-004-{rev}.CSV` |
| Tag Properties | 303 | `JDAW-KVE-E-JA-6944-00001-010-{rev}.CSV` |
| Equipment Properties | 301 | `JDAW-KVE-E-JA-6944-00001-011-{rev}.CSV` |
| Area Register | 203 | `JDAW-KVE-E-JA-6944-00001-017-{rev}.CSV` |
| Process Unit | 204 | `JDAW-KVE-E-JA-6944-00001-018-{rev}.CSV` |
| Purchase Order | 214 | `JDAW-KVE-E-JA-6944-00001-008-{rev}.CSV` |
| Model Part | 209 | `JDAW-KVE-E-JA-6944-00001-005-{rev}.CSV` |
| Tag Class Properties | 307 | `JDAW-KVE-E-JA-6944-00001-009-{rev}.CSV` |
| Tag Connections | 212 | `JDAW-KVE-E-JA-6944-00001-006-{rev}.CSV` |
| Document Cross-Reference — All 8 | 408–420 | `...016..024-{rev}.CSV` |
| Doc→Site | 408 | `JDAW-KVE-E-JA-6944-00001-024-{rev}.CSV` |
| Doc→Plant | 409 | `JDAW-KVE-E-JA-6944-00001-023-{rev}.CSV` |
| Doc→Process Unit | 410 | `JDAW-KVE-E-JA-6944-00001-018-{rev}.CSV` |
| Doc→Area | 411 | `JDAW-KVE-E-JA-6944-00001-017-{rev}.CSV` |
| Doc→Tag | 412 | `JDAW-KVE-E-JA-6944-00001-016-{rev}.CSV` |
| Doc→Equipment | 413 | `JDAW-KVE-E-JA-6944-00001-019-{rev}.CSV` |
| Doc→Model Part | 414 | `JDAW-KVE-E-JA-6944-00001-020-{rev}.CSV` |
| Doc→Purchase Order | 420 | `JDAW-KVE-E-JA-6944-00001-022-{rev}.CSV` |

### Export Output Location

```
/mnt/shared-data/ram-user/Jackdaw/EIS_Exports/
```

Files are available for download directly from the EIS Management page.

### Export Invariants

- **Encoding**: UTF-8 BOM (`utf-8-sig`) — required by EIS system and Excel
- **Filter**: `object_status = 'Active'` applied at both SQL and Python layers
- **Revision format**: must match `^[A-Z]\d{2}$` — validated before any DB work
- **Built-in validation**: `apply_builtin_fixes()` runs automatically (fixes commas, NaN strings, encoding artefacts)
- **Audit**: every run writes to `audit_core.sync_run_stats`
- **Extension**: uppercase `.CSV`

---

## Prefect — Flow Management

### Key URLs

| Resource | URL |
|---|---|
| Prefect UI | `https://pve.prefect.adzv-pt.dev` |
| Prefect API | `http://prefect-server:4200/api` (internal) |

### CLI Commands (run on PVE LXC)

```bash
# List all registered flows and deployments
prefect flow ls
prefect deployment ls

# Trigger a flow manually
prefect flow run -n "export-tag-register-deployment"

# Check worker status
prefect worker ls

# View recent flow runs
prefect flow-run ls --limit 20
```

### Deployment Naming Convention

Deployments follow the pattern `export-<name>-deployment`. The UI EIS Management page queries Prefect for all deployments matching `export-%` and displays their live status.

### Worker Diagnostics

```bash
# View worker logs
docker compose logs prefect-worker --tail=50

# Restart a stuck worker
docker compose restart prefect-worker

# Verify worker networks (must include ai_core_network)
docker inspect prefect-worker | grep -A5 Networks
```

> On startup, the worker automatically installs Python dependencies from:
> `/mnt/shared-data/ram-user/Jackdaw/EDW-repository/prefect-worker/scripts/requirements.txt`

---

## Architecture Overview

### Stack

| Component | Technology | Internal Address | Public URL |
|---|---|---|---|
| UI | Streamlit 1.x | `jackdaw-ui:8501` | `jackdaw.edw.adzv-pt.dev` |
| Orchestration | Prefect 3.x | `prefect-server:4200` | `pve.prefect.adzv-pt.dev` |
| Primary DB | PostgreSQL 16 | `postgres:5432` | — |
| Vector search | Qdrant | `qdrant:6333` | — |
| Graph DB | Neo4j | `neo4j:7687` | `neo4j.adzv-pt.dev` |
| LLM inference | Ollama (RTX 3090) | `ollama:11434` | `ollama.adzv-pt.dev` |
| DB admin | DbGate | `dbgate:18978` | `pve.db.adzv-pt.dev` |
| Reverse proxy | Caddy (VPS) | — | TLS termination for all domains |

### Dual-Stack Deployment

```
PVE LXC (tensor-lxc, 10.10.10.50)
├── Stack 1: ai-infra-core    — Ollama, Neo4j, Qdrant, Flowise, infra-postgres
└── Stack 2: jackdaw-edw      — postgres, redis, prefect-*, dbgate, jackdaw-ui

VPS (Remote)
└── Stack 3: vps-services     — Caddy, n8n, Langfuse, Open WebUI, MCP Server
```

Cross-stack communication uses the `ai_core_network` Docker bridge and Tailscale VPN.
PVE is never exposed directly to the internet — all external traffic goes through Caddy on the VPS.

### Database Schema Namespaces

| Schema | Contents |
|---|---|
| `project_core` | Tags, documents, property values, equipment |
| `ontology_core` | CFIHOS classes, properties, UOM |
| `reference_core` | Areas, process units, companies, purchase orders, plants |
| `mapping` | Tag↔Document, Tag↔SECE links |
| `audit_core` | Sync run stats, tag change history, validation results, validation rules |
| `app_core` | UI users (`ui_user` — login credentials and roles) |

### DB Access Roles

| Role | Access | Used by |
|---|---|---|
| `postgres_admin` | Full (superuser) | Prefect flows, admin UI actions |
| `edw_viewer` | SELECT on `project_core`, `audit_core`, `ontology_core`, `reference_core`, `mapping` | Viewer UI queries |

---

## Common Commands

### Service Health

```bash
# From any internet-connected machine
curl -I https://jackdaw.edw.adzv-pt.dev
curl https://pve.prefect.adzv-pt.dev/api/health
curl https://ollama.adzv-pt.dev/api/tags

# On PVE
docker compose ps                   # all container states
docker stats --no-stream            # CPU/RAM per container
docker compose exec postgres pg_isready -U postgres_admin -d engineering_core
```

### Database

```bash
# Quick access via DBGate UI
open https://pve.db.adzv-pt.dev

# Manual backup
docker compose exec postgres pg_dump -U postgres_admin engineering_core \
  | gzip > /mnt/backup-hdd/postgres_backups/manual_$(date +%Y%m%d_%H%M%S).sql.gz
```

### User Management

Users are stored in `app_core.ui_user`. Passwords are bcrypt-hashed. Roles: `viewer` or `admin`.

```sql
-- Add a new user (run via DBGate or psql)
INSERT INTO app_core.ui_user (username, password_hash, role, is_active)
VALUES ('newuser', crypt('password', gen_salt('bf')), 'viewer', true);

-- Deactivate a user
UPDATE app_core.ui_user SET is_active = false WHERE username = 'olduser';
```

---

## Configuration Files

| File | Purpose |
|---|---|
| `config/config.yaml` | DB connection, file storage paths |
| `docker/jackdaw-edw_docker-compose.yml` | EDW stack compose definition |
| `.env` | Secrets (not in git — stored alongside compose file) |
| `sql/schema/schema.sql` | Canonical DDL for all tables — single source of truth |

### Key Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres_admin:...@postgres:5432/engineering_core` | Admin DB connection |
| `DATABASE_VIEWER_URL` | falls back to `DATABASE_URL` | Read-only viewer DB connection |
| `PREFECT_API_URL` | `http://prefect-server:4200/api` | Prefect API endpoint |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama inference endpoint |
| `EIS_EXPORT_DIR` | `/mnt/shared-data/ram-user/Jackdaw/EIS_Exports/` | Export file output directory |

---

## Full Documentation

| Document | Contents |
|---|---|
| `docs/architecture.md` | Docker services, data flows, SCD2 algorithm, ADRs |
| `docs/infrastructure.md` | Network topology, DNS records, TLS, deployment procedures |
| `docs/file-specification.md` | Input XLSX specs and EIS CSV column definitions |
| `docs/design_system.md` | UI design system — colors, typography, RBAC display rules |
