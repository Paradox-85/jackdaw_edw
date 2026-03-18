# Jackdaw EDW – Infrastructure Architecture (v2.2)

**Last Updated**: March 18, 2026  
**Version**: 2.2 (Optimized dual-stack with operational focus)  
**Status**: Production-Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Stack 1: AI Infrastructure Core](#stack-1-ai-infrastructure-core)
4. [Stack 2: EDW Application Layer](#stack-2-edw-application-layer)
5. [Stack 3: VPS Services & Proxy](#stack-3-vps-services--proxy)
6. [DNS & Domain Routing](#dns--domain-routing)
7. [Security & Access Control](#security--access-control)
8. [Data Persistence & Storage](#data-persistence--storage)
9. [Inter-Service Communication](#inter-service-communication)
10. [Deployment Procedures](#deployment-procedures)
11. [Troubleshooting](#troubleshooting)
12. [Quick Reference](#quick-reference)

---

## Executive Summary

Jackdaw EDW operates as a **modular dual-stack architecture**:

| Component | Purpose | Location | Services |
|-----------|---------|----------|----------|
| **AI Infrastructure** | LLM, vector, graph databases | PVE (ai-infra-core stack) | 5 containers |
| **EDW Application** | Warehouse, ETL, UI, orchestration | PVE (jackdaw-edw stack) | 7 containers |
| **VPS Services** | Proxy, automation, monitoring | Remote VPS | 9 containers |
| **Total** | Complete platform | PVE + VPS | **18 containers** |

**Key metrics**: 3 Docker networks, 18+ public domains, 50+ GB storage, RTX 3090 GPU, Tailscale VPN backbone

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TAILSCALE VPN BACKBONE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────┐       ┌────────────────────────────────┐
│  │  VPS (Reverse Proxy & Services)│       │  Proxmox VE Node               │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━   │       │  (LXC: tensor-lxc, 10.10.10.50)
│  │                                │       │                                │
│  │  ├─ Caddy (HTTPS, 443)         │       │  ┌──────────────────────────┐ │
│  │  │  └─ TLS termination        │       │  │  ai_core_network Bridge  │ │
│  │  │     (Let's Encrypt ACME)   │       │  │  ━━━━━━━━━━━━━━━━━━━━━  │ │
│  │  │     All traffic → HTTPS    │◄─────┤──│  Stack 1: AI Infra       │ │
│  │  │                             │      │  │  ├─ Ollama (11434, GPU)  │ │
│  │  ├─ n8n (5678)                │      │  │  ├─ Neo4j (7474)         │ │
│  │  │  Workflow automation       │      │  │  ├─ Qdrant (6333)        │ │
│  │  │  [Prefect triggers]        │      │  │  ├─ Flowise (3001)       │ │
│  │  │                             │      │  │  └─ Infra-Postgres      │ │
│  │  ├─ Langfuse (3000)           │      │  │                          │ │
│  │  │  LLM observability         │      │  │  Stack 2: EDW App        │ │
│  │  │  [ClickHouse analytics]    │      │  │  ├─ Streamlit UI (8501)  │ │
│  │  │                             │      │  │  ├─ Prefect Server       │ │
│  │  ├─ Open WebUI (8080)         │      │  │  ├─ Prefect Worker       │ │
│  │  │  LLM chat UI               │      │  │  ├─ PostgreSQL (5432)    │ │
│  │  │                             │      │  │  ├─ Redis (6379)         │ │
│  │  ├─ PostgreSQL, Redis         │      │  │  ├─ DBGate (18978)       │ │
│  │  ├─ ClickHouse, Minio         │      │  │  └─ jackdaw-ui (build)   │ │
│  │  ├─ MCP Server (8080)         │      │  └──────────────────────────┘ │
│  │  └─ web_proxy network (local) │      │                                │
│  │                                │      │  Shared: /mnt/shared-data      │
│  └────────────────────────────────┘      └────────────────────────────────┘
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Key Principle: Decoupled stacks enable independent updates (AI stays stable
while EDW can be redeployed). Both communicate via ai_core_network bridge.
External access only via VPS Caddy (no direct PVE exposure to internet).
```

---

## Stack 1: AI Infrastructure Core

**Location**: `/mnt/stack/ai-infra-core/` | **Network**: `ai_core_network` (standard definition)

### Services

| Service | Image | Port | Storage | Purpose |
|---------|-------|------|---------|---------|
| **infra-postgres** | `postgres:16-bookworm` | 5432 | `infra_postgres_data` | Flowise metadata DB (`flowise_db`) |
| **ollama** | `ollama/ollama:latest` | 11434 | `./ollama_storage` | LLM inference (GPU-accelerated) |
| **neo4j** | `neo4j:latest` | 7474, 7687 | `./neo4j_data` | Graph database (relationships) |
| **flowise** | `flowiseai/flowise:latest` | 3001 | N/A | AI workflow orchestration UI |
| **qdrant** | `qdrant/qdrant:latest` | 6333 | `./qdrant_storage` | Vector storage (embeddings) |

### Environment Variables

```bash
CORE_NETWORK_NAME=ai_core_network
INFRA_DB_USER=infra_admin
INFRA_DB_PASS=[***REDACTED***]
NEO4J_USER=neo4j
NEO4J_PASSWORD=[***REDACTED***]
FLOWISE_USERNAME=flowiseadmin
FLOWISE_PASSWORD=[***REDACTED***]
SHARED_DB_HOST=postgres                    # Points to jackdaw-edw's postgres
SHARED_DB_USER=postgres_admin
SHARED_DB_PASS=[***REDACTED***]
```

### Key Configurations

- **Ollama GPU**: `deploy.resources.reservations.devices: [nvidia GPU, count: 1, capabilities: [gpu]]` (RTX 3090)
- **Ollama Storage**: Mounts both local `./ollama_storage` + read-only `/mnt/backup-hdd/.../Master-Data` for model artifacts
- **Qdrant Storage**: Similar dual mount (local embeddings + shared reference data)

---

## Stack 2: EDW Application Layer

**Location**: `/mnt/stack/jackdaw-edw/` | **Networks**: `default` (isolated) + `ai_core_network` (external)

### Services

| Service | Image | Port | Purpose | Key Config |
|---------|-------|------|---------|-----------|
| **postgres** | `postgres:16-bookworm` | 5432 | Main warehouse DB | Creates 2 databases: `engineering_core`, `prefect` |
| **redis** | `redis:alpine` | 6379 | Prefect message broker | Used by prefect-server & workers |
| **prefect-server** | `prefect:3-latest` | 4200 | Flow orchestration API | Cmd: `prefect server database upgrade -y && prefect server start --no-services` |
| **prefect-services** | `prefect:3-latest` | N/A | Background scheduler | Cmd: `prefect server services start` |
| **prefect-worker** | `prefect:3-latest` | N/A | Flow executor | Cmd: `pip install -r /mnt/shared-data/.../requirements.txt && prefect worker start` |
| **dbgate** | `dbgate/dbgate:latest` | 18978 | Database GUI (dev only) | `CONNECTIONS_LOCAL_ONLY=true` (security) |
| **jackdaw-ui** | custom build | 8501 | Streamlit analytics portal | Context: `/mnt/shared-data/.../scripts`; joins ai_core_network |

### Environment Variables

```bash
POSTGRES_USER=postgres_admin
POSTGRES_PASSWORD=[***REDACTED***]
POSTGRES_DB=engineering_core
PREFECT_DB=prefect
PGDATA=/var/lib/postgresql/data/pgdata
PUID=1000
PGID=1000
DBGATE_ADMIN_USER=admin
DBGATE_ADMIN_PASSWORD=[***REDACTED***]
EDW_VIEWER_PASSWORD=[***REDACTED***]
ADMIN_PASSWORD=[***REDACTED***]
```

### Key Configurations

**Prefect Server**: Splits API (`--no-services`) from background services (`services start`). This separation ensures workers can restart independently.

**Prefect Worker**: Runtime pip-install from `/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts/requirements.txt` enables flow code dependency management.

**DBGate**: Environment variables:
```yaml
CONNECTIONS=eng_db
LABEL_eng_db=Engineering_Core
SERVER_eng_db=postgres
ENGINE_eng_db=postgres@dbgate-plugin-postgres
LOGIN_PERMISSIONS_admin=connections/eng_db,settings/change,widgets/*,dbops/*
CONNECTIONS_LOCAL_ONLY=true
```

**jackdaw-ui Build**: 
- Context: `/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts`
- Dockerfile: `docker/jackdaw-ui/Dockerfile`
- Environment: `DATABASE_VIEWER_URL=postgresql://edw_viewer:${EDW_VIEWER_PASSWORD}@postgres:5432/${POSTGRES_DB}`
- Joins both `default` and `ai_core_network` for cross-stack access

### PostgreSQL Initialization

File: `./postgres/init/init-db.sql`

```sql
CREATE DATABASE engineering_core;
CREATE DATABASE prefect;
CREATE ROLE edw_viewer WITH LOGIN PASSWORD '[***REDACTED***]';
GRANT CONNECT ON DATABASE engineering_core TO edw_viewer;
GRANT USAGE ON SCHEMA project_core TO edw_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA project_core TO edw_viewer;
-- [Additional schema setup via migrations]
```

---

## Stack 3: VPS Services & Proxy

**Location**: `/var/lib/docker/compose/vps-services/` | **Network**: `web_proxy` (external)

### Services

| Service | Image | Port | Purpose | Depends On |
|---------|-------|------|---------|-----------|
| **postgres** | `postgres:latest` | 5432 | Metadata DB (n8n, Langfuse) | N/A |
| **redis** | `valkey/valkey:8-alpine` | 6379 | Cache + sessions | N/A |
| **clickhouse** | `clickhouse/clickhouse-server` | 8123 | Time-series analytics | N/A |
| **minio** | `minio/minio` | 9000, 9001 | S3-compatible storage | N/A |
| **n8n** | `n8nio/n8n:latest` | 5678 | Workflow automation | postgres (healthy) |
| **langfuse-web** | `langfuse/langfuse:3` | 3000 | LLM observability | postgres, clickhouse, redis |
| **open-webui** | `open-webui:main` | 8080 | LLM chat interface | N/A |
| **mcp-server** | `postgres-mcp:latest` | 8080 | Database API (Claude) | N/A |
| **caddy** | `caddy:2-alpine` | 80, 443 | Reverse proxy, TLS | N/A |

### Environment Variables & Key Configs

**postgres**:
```yaml
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=postgres
volumes: ./postgres_data:/var/lib/postgresql
healthcheck: pg_isready -U postgres (5s interval, 10 retries)
```

**n8n**:
```yaml
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
N8N_USER_MANAGEMENT_JWT_SECRET=${N8N_USER_MANAGEMENT_JWT_SECRET}
N8N_SECURE_COOKIE=true
WEBHOOK_URL=https://${N8N_HOSTNAME}
depends_on: postgres (service_healthy)
```

**langfuse-web**:
```yaml
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/postgres
NEXTAUTH_URL=https://${LANGFUSE_HOSTNAME}
CLICKHOUSE_URL=http://clickhouse:8123
REDIS_HOST=redis
depends_on: postgres, clickhouse, redis
```

**open-webui**:
```yaml
OLLAMA_BASE_URL=http://10.10.10.50:11434    # Cross-network to PVE Ollama
WEBUI_SECRET_KEY=${JWT_SECRET}
```

**mcp-server**:
```yaml
PGEDGE_DATA_DIR=/app/data
PGEDGE_CONFIG_FILE=/etc/pgedge/postgres-mcp.yaml
volumes: ./mcp-config:/etc/pgedge, ./mcp-data:/app/data
```

**caddy**:
```yaml
volumes:
  - ./Caddyfile:/etc/caddy/Caddyfile (read-only config)
  - ./caddy_data:/data (Let's Encrypt certificates)
  - ./caddy_config:/config (runtime state)
```

---

## DNS & Domain Routing

**Domain**: `adzv-pt.dev` | **Primary DNS**: [Registrar]

### DNS Records

```
A:    adzv-pt.dev              [VPS_PUBLIC_IP]

CNAME (all alias to root):
      jackdaw.edw              → Streamlit UI (10.10.10.50:8501)
      pve.prefect              → Prefect API (10.10.10.50:4200)
      pve.db                   → DBGate (10.10.10.50:18978)
      pve                      → Proxmox VE (10.10.10.1:8006)
      pve.pbs                  → Backup Server (10.10.10.20:8007)
      pve.pulse                → Monitoring (10.10.10.15:7655)
      pve.portainer            → Portainer (10.10.10.50:9000)
      pve.sftpgo               → File Server (10.10.10.60:8080/8090)
      ollama                   → Ollama (10.10.10.50:11434)
      neo4j                    → Neo4j (10.10.10.50:7474)
      flowise                  → Flowise (10.10.10.50:3001)
      n8n                      → n8n (local:5678)
      webui                    → Open WebUI (local:8080)
      langfuse                 → Langfuse (local:3000)
      ai-db                    → MCP Server (local:8080)
      searxng                  → SearXNG (local:8080)
      nanokvm                  → Out-of-band management (100.92.70.92:80)
```

### Caddy Configuration (Complete)

See `Caddyfile.optimized` for full TLS setup, security headers, and route definitions. Key features:
- Automatic Let's Encrypt renewal (30 days before expiry)
- HTTP→HTTPS redirect (port 80 always redirects to 443)
- Security headers on public-facing services (X-Frame-Options, X-Content-Type-Options, HSTS)
- Streaming support (Ollama chat endpoints)

---

## Security & Access Control

### PostgreSQL Roles

```sql
-- Admin role (warehouse)
CREATE ROLE postgres_admin WITH SUPERUSER LOGIN PASSWORD '[***REDACTED***]';

-- Read-only role (UI viewers)
CREATE ROLE edw_viewer WITH LOGIN PASSWORD '[***REDACTED***]';
GRANT CONNECT ON DATABASE engineering_core TO edw_viewer;
GRANT USAGE ON SCHEMA project_core TO edw_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA project_core TO edw_viewer;

-- Prefect service role (orchestration)
-- [Managed by Prefect itself]
```

### Network Isolation

| Layer | Method | Protection |
|-------|--------|-----------|
| **Public Internet** | Caddy TLS | HTTPS-only; self-signed backends accepted via Tailscale |
| **Inter-Region** | Tailscale VPN | Encrypted WireGuard tunnel; no direct public exposure |
| **Docker Containers (Cross-Stack)** | `ai_core_network` bridge | Private bridge; services use hostname DNS |
| **Docker Containers (VPS)** | `web_proxy` bridge | Private bridge; local only |
| **Host Firewall** | UFW rules | SSH restricted, Docker ports isolated |

### Tailscale ACL (Example)

```json
{
  "groups": {
    "group:admins": ["admin@company.com"],
    "group:engineers": ["eng@company.com"]
  },
  "acls": [
    {
      "action": "accept",
      "users": ["group:admins"],
      "ports": ["10.10.10.50:8501", "10.10.10.50:4200", "10.10.10.50:11434"]
    }
  ]
}
```

### TLS/SSL

- **Provider**: Let's Encrypt (automatic ACME)
- **Renewal**: Caddy handles automatically (30 days before expiry)
- **Certificate Storage**: `/data/caddy/certificates/` (persistent volume)
- **Protocols**: TLSv1.3 (preferred) + TLSv1.2 (fallback)

---

## Data Persistence & Storage

### Named Docker Volumes

| Volume | Stack | Size | Purpose | Lifecycle |
|--------|-------|------|---------|-----------|
| `postgres_data` | jackdaw-edw | 1.4 GB | Engineering warehouse DB | Persistent |
| `redis_data` | jackdaw-edw | ~50 MB | Prefect message queue snapshots | Persistent |
| `dbgate_data` | jackdaw-edw | ~50 MB | GUI connection configs | Persistent |
| `infra_postgres_data` | ai-infra-core | ~100 MB | Flowise metadata (`flowise_db`) | Persistent |
| `postgres_data` (VPS) | vps-services | ~500 MB | n8n + Langfuse metadata | Persistent |
| `clickhouse_data` (VPS) | vps-services | ~1 GB | LLM trace analytics | Persistent |
| `redis_data` (VPS) | vps-services | ~50 MB | Cache + sessions | Persistent |

### Bind Mounts (Host Filesystem)

| Mount | Source | Destination | Access | Purpose |
|-------|--------|-------------|--------|---------|
| Flow code | `/mnt/shared-data/.../scripts` | `/mnt/shared-data` (container) | read-write | Prefect flows, jackdaw-ui source |
| Ollama models | `/mnt/stack/ai-infra-core/ollama_storage` | `/root/.ollama` | read-write | LLM model cache |
| Master data | `/mnt/backup-hdd/.../Master-Data` | `/data/shared:ro` | read-only | Reference data for Ollama/Qdrant |
| Qdrant embeddings | `/mnt/stack/ai-infra-core/qdrant_storage` | `/qdrant/storage` | read-write | Vector embeddings |

### Access Patterns (`/mnt/shared-data`)

```
/mnt/shared-data/
├── ram-user/Jackdaw/
│   ├── prefect-worker/scripts/
│   │   ├── (flows/import_mdr.py)         ← Read by: prefect-worker
│   │   ├── (flows/export_eis.py)         ← Read by: prefect-worker
│   │   ├── docker/jackdaw-ui/Dockerfile  ← Read by: docker build (jackdaw-ui)
│   │   └── requirements.txt               ← Installed by: prefect-worker at startup
│   ├── Master-Data/                       ← Read by: Ollama, Qdrant (model initialization)
│   ├── MDR.xlsx, MTR-dataset.xlsx         ← Source data for import flows
│   └── Export/EIS/                        ← Written by: prefect-worker (flow outputs)
└── [other shared resources]
```

### Volume Initialization Behavior

- **Ollama**: First start pulls models (10+ min for large models). Use `ollama pull llama2` to pre-load.
- **Neo4j**: Empty directory on first start; creates `/data` subdirectories automatically.
- **Qdrant**: Auto-creates collections on first write.
- **PostgreSQL**: Runs `./postgres/init/init-db.sql` on first startup only.

### Backup & Recovery

**Automated PostgreSQL Backup** (cron on PVE host):
```bash
#!/bin/bash
docker exec postgres_db pg_dump -U postgres_admin engineering_core \
  | gzip > /mnt/backup-hdd/postgres_backups/engineering_core_$(date +%Y%m%d_%H%M%S).sql.gz
find /mnt/backup-hdd/postgres_backups/ -name "*.sql.gz" -mtime +7 -delete  # 7-day retention
```

**Restore PostgreSQL**:
```bash
cd /mnt/stack/jackdaw-edw
docker compose stop jackdaw-ui prefect-worker
gunzip < /mnt/backup-hdd/postgres_backups/engineering_core_20260318_020000.sql.gz \
  | docker compose exec -T postgres psql -U postgres_admin -d engineering_core
docker compose up -d jackdaw-ui prefect-worker
```

---

## Inter-Service Communication

### Cross-Stack Service Discovery

**Network**: `ai_core_network` (Docker bridge)

| From | To | Via | Purpose |
|------|----|----|---------|
| jackdaw-ui | ollama:11434 | DNS | LLM chat completions |
| jackdaw-ui | qdrant:6333 | DNS | Vector search |
| jackdaw-ui | neo4j:7687 | DNS | Graph queries |
| prefect-worker | (any ai_core_network service) | DNS | Flow task execution |
| infra-postgres | (VPS postgres) | SHARED_DB_HOST var | Cross-stack queries (optional) |

**Example (Python)**:
```python
import requests
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

# Ollama (cross-stack)
response = requests.post("http://ollama:11434/api/chat", 
                        json={"model": "llama2", "messages": [...]})

# Qdrant (cross-stack)
qdrant = QdrantClient(host="qdrant", port=6333)
results = qdrant.search(collection_name="embeddings", query_vector=[...])

# Neo4j (cross-stack)
driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", os.getenv("NEO4J_PASSWORD")))
```

### Prefect Flow Execution

```
User trigger (Streamlit) → Prefect API (port 4200) → PostgreSQL (prefect DB)
  → Redis (event published) → prefect-worker (polls) → Executes task
    → Task calls Ollama/Qdrant (via ai_core_network)
      → Results written to engineering_core DB → UI displays results
```

**Key**: Worker must join `ai_core_network` to access Ollama, Qdrant, etc.

---

## Deployment Procedures

### Phase 0: Prerequisites

- [ ] PVE LXC with Docker & Docker Compose installed
- [ ] Remote VPS with Docker & Docker Compose installed
- [ ] Tailscale VPN configured (PVE ↔ VPS encrypted tunnel)
- [ ] DNS records pointing to VPS public IP
- [ ] `.env` files prepared with credentials

### Phase 1: Network Setup

```bash
# On PVE
docker network create ai_core_network

# On VPS
docker network create web_proxy
```

### Phase 2: Deploy ai-infra-core Stack

```bash
cd /mnt/stack/ai-infra-core
cp /secure/location/ai-infra-core_.env .env
docker compose up -d

# Wait for services to initialize (especially Ollama GPU init)
sleep 30
docker compose ps
# Expected: all services "Up"
```

### Phase 3: Deploy jackdaw-edw Stack

```bash
cd /mnt/stack/jackdaw-edw
cp /secure/location/jackdaw-edw_.env .env
mkdir -p postgres/init
cp /secure/location/init-db.sql postgres/init/
docker compose up -d postgres

# Wait for PostgreSQL initialization
sleep 15
docker compose exec postgres pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
# Output: "accepting connections"

# Start remaining services
docker compose up -d redis prefect-server prefect-services prefect-worker dbgate jackdaw-ui
sleep 10
docker compose ps
```

### Phase 4: Deploy VPS Stack

```bash
cd /var/lib/docker/compose/vps-services
cp /secure/location/vps-services_.env .env
cp /secure/location/Caddyfile.optimized Caddyfile
mkdir -p mcp-config n8n_backups
# [Add postgres-mcp.yaml to mcp-config/]
docker compose up -d

# Verify Caddy certificates issued
sleep 15
docker compose logs caddy | grep -i "serving\|acme\|error"
```

### Phase 5: Register Prefect Flows

```bash
# Inside PVE (after jackdaw-edw stack is healthy)
cd /mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts

# Deploy flows to Prefect server
prefect deploy flows/import_mdr.py:import_mdr_flow -n "Import MDR" -p "default-agent-pool"
prefect deploy flows/export_eis.py:export_eis_flow -n "Export EIS" -p "default-agent-pool"

# Verify flows registered
prefect flow ls
```

### Phase 6: Smoke Test

```bash
# From any machine with internet
curl -I https://jackdaw.edw.adzv-pt.dev              # Should return 200 OK
curl -I https://pve.prefect.adzv-pt.dev/api/health   # Prefect health
curl -I https://ollama.adzv-pt.dev/api/tags          # Ollama model list
curl -I https://langfuse.adzv-pt.dev                 # Langfuse UI

# Full integration test
# 1. Open https://jackdaw.edw.adzv-pt.dev in browser
# 2. Navigate to "LLM Chat" tab
# 3. Type a message → should get response from Ollama
# 4. Check Langfuse (https://langfuse.adzv-pt.dev) for trace entry
```

---

## Troubleshooting

### Issue 1: Ollama Unreachable from VPS/UI

**Symptom**: `curl https://ollama.adzv-pt.dev/api/tags` returns 502 or timeout

**Root Cause**: 
- Tailscale tunnel down or misconfigured
- PVE firewall blocking port 11434
- Ollama not responding

**Resolution**:
```bash
# From VPS
ping 10.10.10.50                              # Test Tailscale connectivity
curl http://10.10.10.50:11434/api/tags       # Direct test (no Caddy)
# If fails, check PVE firewall:

# From PVE
sudo ufw status
docker exec ollama ollama list               # Check if Ollama running
docker compose logs ollama | tail -20        # Ollama logs
```

### Issue 2: Prefect Worker Not Registering

**Symptom**: Worker not showing in `prefect worker ls` on UI; flows stuck "Not Run"

**Root Cause**: 
- Worker can't reach Prefect API (network/DNS issue)
- Worker not joining ai_core_network
- requirements.txt not accessible

**Resolution**:
```bash
# From PVE
docker compose logs prefect-worker | grep -i "error\|api\|pool"
docker exec prefect-worker prefect config view              # Check config
docker inspect prefect-worker | jq '.NetworkSettings.Networks' # Check networks

# Restart worker
docker compose restart prefect-worker
```

### Issue 3: PostgreSQL Port Conflict

**Symptom**: `ERROR: bind: address already in use` on port 5432

**Root Cause**: 
- Host machine already has PostgreSQL running
- Old container not fully cleaned up

**Resolution**:
```bash
sudo lsof -i :5432                           # Find process
docker ps -a | grep postgres                # Check all containers
docker rm -f postgres_db                     # Force remove old container
docker compose up -d postgres                # Restart
```

### Issue 4: Caddy Certificate Not Renewing

**Symptom**: Certificate expires; HTTPS fails with cert error

**Root Cause**: 
- Caddy misconfigured for automatic renewal
- ACME challenge failing (usually DNS/port 80 issue)

**Resolution**:
```bash
# From VPS
docker exec caddy caddy list-certs           # View current certs
docker exec caddy caddy reload               # Trigger manual reload
docker compose logs caddy | grep -i "acme\|challenge"

# If ACME fails, verify:
curl -I http://adzv-pt.dev                   # HTTP accessible for ACME
# Caddy must reach Let's Encrypt (port 80/443 outbound required)
```

### Monitoring Commands

```bash
# Service health
docker compose ps                             # All services state
docker compose exec postgres pg_isready -U postgres_admin -d engineering_core

# Resource usage
docker stats --no-stream                     # CPU, memory, I/O per container

# Prefect status
curl http://10.10.10.50:4200/api/health      # Prefect health endpoint

# Database size
docker compose exec postgres du -sh /var/lib/postgresql/

# Log aggregation
docker compose logs -f jackdaw-ui            # Follow UI logs
docker compose logs --since 2h postgres      # Last 2 hours of postgres logs
```

---

## Quick Reference

### Environment Variables Checklist

**jackdaw-edw/.env** (11 vars):
```
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, PREFECT_DB, PGDATA,
PUID, PGID, DBGATE_ADMIN_USER, DBGATE_ADMIN_PASSWORD,
EDW_VIEWER_PASSWORD, ADMIN_PASSWORD
```

**ai-infra-core/.env** (10 vars):
```
CORE_NETWORK_NAME, INFRA_DB_USER, INFRA_DB_PASS,
NEO4J_USER, NEO4J_PASSWORD, FLOWISE_USERNAME, FLOWISE_PASSWORD,
SHARED_DB_HOST, SHARED_DB_USER, SHARED_DB_PASS
```

**vps-services/.env** (12 vars):
```
POSTGRES_PASSWORD, N8N_ENCRYPTION_KEY, N8N_USER_MANAGEMENT_JWT_SECRET,
N8N_HOSTNAME, JWT_SECRET, LANGFUSE_HOSTNAME, NEXTAUTH_URL,
NEXTAUTH_SECRET, LANGFUSE_SALT, ENCRYPTION_KEY, CLICKHOUSE_PASSWORD,
MINIO_ROOT_PASSWORD
```

### Key Commands

```bash
# === PVE ===
docker network create ai_core_network
docker compose -f /mnt/stack/ai-infra-core/docker-compose.yml up -d
docker compose -f /mnt/stack/jackdaw-edw/docker-compose.yml ps
docker compose exec postgres pg_dump -U postgres_admin engineering_core | gzip > backup.sql.gz

# === VPS ===
docker network create web_proxy
docker compose -f /var/lib/docker/compose/vps-services/docker-compose.yml up -d
docker exec caddy caddy reload                      # Zero-downtime config reload
docker compose logs caddy                           # Verify certificate renewal

# === Prefect ===
prefect worker ls                                   # List registered workers
prefect flow ls                                     # List deployed flows
prefect flow run -n "Import MDR"                    # Trigger flow manually

# === Debugging ===
curl https://jackdaw.edw.adzv-pt.dev/health        # UI health
curl https://ollama.adzv-pt.dev/api/tags           # Ollama models
curl https://langfuse.adzv-pt.dev/api/health       # Langfuse
docker stats --no-stream                           # Resource usage
```

### Service Matrix

| Service | Access | Network | Auth | Port |
|---------|--------|---------|------|------|
| Streamlit UI | `jackdaw.edw.adzv-pt.dev` | default | password | 8501 |
| Prefect API | `pve.prefect.adzv-pt.dev` | default | none | 4200 |
| Ollama | `ollama.adzv-pt.dev` | ai_core_network | none | 11434 |
| Neo4j | `neo4j.adzv-pt.dev` | ai_core_network | neo4j user | 7474 |
| Qdrant | internal only | ai_core_network | none | 6333 |
| n8n | `n8n.adzv-pt.dev` | web_proxy | JWT | 5678 |
| Langfuse | `langfuse.adzv-pt.dev` | web_proxy | OAuth | 3000 |
| Open WebUI | `webui.adzv-pt.dev` | web_proxy | optional | 8080 |
| DBGate | `pve.db.adzv-pt.dev` | default | admin | 18978 |
| MCP Server | `ai-db.adzv-pt.dev` | web_proxy | internal | 8080 |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Feb 2026 | Initial comprehensive documentation |
| 2.1 | Mar 2026 | VPS integration, Caddy optimization, security hardening |
| 2.2 | Mar 2026 | Optimized structure, eliminated redundancy, added troubleshooting & Access Patterns |

---

**Maintainer**: Andrei (Jackdaw EDW Project Lead)  
**Status**: ✅ Production-Ready  
**Next Review**: Q2 2026
