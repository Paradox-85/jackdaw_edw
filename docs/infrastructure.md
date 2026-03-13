# Jackdaw — Master Technical Specification

> **Scope:** Full infrastructure reference for the Jackdaw EDW platform.  
> **Purpose:** Single source of truth for hardware, virtualization, containers, networking, and service stack.  
> **Language:** English. All paths, ports, and credentials as deployed.

---

## 1. Hardware

| Component | Spec |
|---|---|
| **CPU** | AMD Ryzen 7 7700 (8c/16t, Zen 4, AM5) — Curve Optimizer: −60 |
| **GPU** | NVIDIA GeForce RTX 3090 · 24 GB GDDR6X · PCIe riser |
| **RAM** | 32 GB DDR5 · Dual-channel · 5200 MHz · EXPO enabled |
| **Motherboard** | Gigabyte B650M D3HP (Micro-ATX) |
| **OS Drive** | KIOXIA EXCERIA 480 GB SATA SSD — Proxmox PVE root |
| **Fast NVMe** | Samsung 990 EVO Plus 1 TB · PCIe 4.0×4 / 5.0×2 — LXC roots, DBs, LLM weights |
| **Data HDD** | Seagate BarraCuda 4 TB SATA — shared data, document storage, backups |
| **PSU / Power** | MSI MAG PANO M100L PZ case · Tapo P100 smart plug · Eaton protection strip |

**BIOS/UEFI (required settings):**
```
SVM Mode (AMD Virtualization): Enabled
IOMMU:                         Enabled
Above 4G Decoding:             Enabled
Re-size BAR Support:           Enabled
AC BACK:                       Always On
Secure Boot:                   Disabled
```

---

## 2. Proxmox VE Host

**Version:** PVE 9.x  
**Kernel:** `6.14.11-5-pve` (pinned — required for NVIDIA DKMS compilation)  
**NVIDIA Driver:** `580.105.08` (proprietary, `nvidiafb` + `nouveau` blacklisted)  
**OS optimizations:** `Log2RAM` installed (redirects `/var/log` to RAM)

### 2.1 Storage Pools

| PVE Pool | Backend | Physical Device | Used For |
|---|---|---|---|
| `local` | Directory | KIOXIA SATA (100 GB) | ISO images, templates, PVE configs |
| `nvme-storage` | LVM-Thin | Samsung 990 NVMe | LXC root disks, DBs (Qdrant, Neo4j), LLM weights |
| `hdd-data` | Directory | Seagate 4 TB HDD | Backups, SFTPGo data root, shared documents |

Disk flags on all VM/LXC disks: `Discard` (TRIM), `SSD Emulation`, `IO Thread: enabled`

### 2.2 Network

| Parameter | Value |
|---|---|
| Bridge | `vmbr0` (no VLAN tagging) |
| Internal subnet | `10.10.10.0/24` |
| NAT | Managed by `vm-nat.service` |
| IPv6 | Disabled |
| Gateway | `10.10.10.1` |

### 2.3 LXC Containers

#### LXC 200 — `tensor-lxc` (Primary Compute Node)

```
Type:          Unprivileged LXC
OS:            Ubuntu 24.04
CPU:           14 cores (host type)
RAM:           28 GB
Swap:          512 MB  [was 8 GB initially, reduced]
Root Disk:     200 GB on nvme-storage
IP:            10.10.10.50/24
Features:      nesting=1, keyctl=1
```

**GPU passthrough** (bind-mount method, zero virtualization overhead):

```ini
# /etc/pve/lxc/200.conf — GPU section
lxc.cgroup2.devices.allow: c 195:* rwm
lxc.cgroup2.devices.allow: c 234:* rwm
lxc.cgroup2.devices.allow: c 235:* rwm
lxc.cgroup2.devices.allow: c 236:* rwm
lxc.cgroup2.devices.allow: c 237:* rwm
lxc.cgroup2.devices.allow: c 238:* rwm
lxc.cgroup2.devices.allow: c 239:* rwm
lxc.cgroup2.devices.allow: c 511:* rwm
lxc.cgroup2.devices.allow: c 226:* rwm
lxc.mount.entry: /dev/nvidia0          dev/nvidia0          none bind,optional,create=file
lxc.mount.entry: /dev/nvidiactl        dev/nvidiactl        none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm       dev/nvidia-uvm       none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm-tools dev/nvidia-uvm-tools none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-modeset   dev/nvidia-modeset   none bind,optional,create=file
lxc.mount.entry: /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.580.105.08 usr/lib/x86_64-linux-gnu/libnvidia-ml.so.580.105.08 none bind,optional,create=file
lxc.mount.entry: /usr/lib/x86_64-linux-gnu/libcuda.so.580.105.08      usr/lib/x86_64-linux-gnu/libcuda.so.580.105.08      none bind,optional,create=file
lxc.mount.entry: /usr/bin/nvidia-smi   usr/bin/nvidia-smi   none bind,optional,create=file
```

**Data mount point:**

```ini
mp0: /mnt/backup-hdd/sftpgo-data,mp=/mnt/shared-data
```

**NVIDIA Container Runtime** — critical config inside LXC 200:

```toml
# /etc/nvidia-container-runtime/config.toml
no-cgroups = true   # required for unprivileged LXC + Docker
```

---

#### LXC 103 — `sftpgo` (Data Ingest Node)

```
Type:          Unprivileged LXC
OS:            Debian/Ubuntu
CPU:           2 cores
RAM:           2 GB
Root Disk:     6–8 GB
IP:            10.10.10.60/24
```

**Mount:**
```ini
mp0: /mnt/backup-hdd/sftpgo-data,mp=/srv/sftpgo/data
```

**Permission note:** Unprivileged LXC maps UID 1000 (internal) → UID 101000 (host).  
Host path requires: `chown -R 101000:101000 /mnt/backup-hdd/sftpgo-data`

#### LXC 999 — Tailscale Subnet Router

Dedicated container acting as PVE subnet router.  
Exposes `10.10.10.0/24` to the Tailscale mesh.  
Separated from PVE host to avoid `iptables` conflicts.

---

## 3. Data Storage & Shared Paths

```
Physical host path:     /mnt/backup-hdd/sftpgo-data/
Mounted in LXC 200:     /mnt/shared-data/
Mounted in LXC 103:     /srv/sftpgo/data/
```

**Key subdirectory:**
```
/mnt/shared-data/ram-user/Jackdaw/
  ├── Master-Data/                   # Source Excel / PDF files (read by ETL)
  └── prefect-worker/
      └── scripts/
          └── requirements.txt       # Auto-installed by prefect-worker on container start
```

**Docker bind mounts** inside LXC 200 (used by `prefect-worker`, `ollama`, `qdrant`):
```yaml
- /mnt/shared-data:/mnt/shared-data
- /mnt/shared-data/ram-user/Jackdaw/Master-Data:/data/shared:ro
```

**Symlinks:** Docker does not traverse symlinks pointing outside a mounted volume.  
All paths must be specified as absolute paths (`/mnt/shared-data/...`).

**File ingest flow:**
```
Windows PC (rclone / Windows WebDAV client)
  → HTTPS via VPS Caddy (reverse proxy, no storage)
    → Tailscale tunnel → LXC 103 SFTPGo (port 8080 admin, port 8090 WebDAV)
      → /mnt/backup-hdd/sftpgo-data/ (4 TB HDD)
        → visible in LXC 200 as /mnt/shared-data/ (bind mount)
```

**rclone config** (Windows, portable mode):
```batch
rclone.exe --config ".\rclone.conf" sync "C:\WorkDocs" pve_webdav:/ --progress
```
Config location Linux: `~/.config/rclone/rclone.conf`

---

## 4. Networking: Tailscale + VPS + Caddy

### Architecture

```
Internet
  │
  ▼
Cloud VPS (public IP)
  ├── Caddy (ports 80/443, Let's Encrypt TLS)
  │     ├── Routes local VPS services (n8n, webui, langfuse, searxng)
  │     └── Routes PVE services via Tailscale IP 10.10.10.50 / 10.10.10.60
  │
  └── Tailscale node (100.x.y.z mesh)
        │
        ▼ WireGuard tunnel
       PVE LXC 999 (Subnet Router)
         └── Exposes 10.10.10.0/24 to Tailscale mesh
               ├── LXC 200: 10.10.10.50  (ai-compute)
               └── LXC 103: 10.10.10.60  (sftpgo)
```

### Caddy Routing Table

```caddy
# --- VPS-local services ---
n8n.adzv-pt.dev          → n8n:5678
webui.adzv-pt.dev        → open-webui:8080
langfuse.adzv-pt.dev     → langfuse-web:3000
searxng.adzv-pt.dev      → searxng:8080

# --- PVE services via Tailscale ---
flowise.adzv-pt.dev      → 10.10.10.50:3001
ollama.adzv-pt.dev       → 10.10.10.50:11434
neo4j.adzv-pt.dev        → 10.10.10.50:7474
pve.prefect.adzv-pt.dev  → 10.10.10.50:4200
pve.db.adzv-pt.dev       → 10.10.10.50:18978
pve.sftpgo.adzv-pt.dev   → 10.10.10.60:8080
  /dav/*                 → 10.10.10.60:8090  (WebDAV, path-stripped)
```

**SFTPGo WebDAV split-port config:**
```caddy
pve.sftpgo.adzv-pt.dev {
    handle_path /dav/* {
        reverse_proxy 10.10.10.60:8090
    }
    handle {
        reverse_proxy 10.10.10.60:8080
    }
}
```

**SFTPGo `sftpgo.json` — WebDAV section:**
```json
"webdavd": {
  "bindings": [{
    "port": 8090,
    "address": "",
    "enable_https": false,
    "prefix": "",
    "proxy_allowed": [],
    "client_ip_proxy_header": "",
    "disable_www_auth_header": false
  }]
}
```

---

## 5. Docker Stacks

### 5.1 PVE Stack — LXC 200 (`ai-compute`)

All services on internal Docker network. GPU runtime via `nvidia` driver.

| Container | Image | Ports | Role |
|---|---|---|---|
| `postgres_db` | `postgres:alpine` | `5432` | Primary DB: `engineering_core`, `prefect`, `flowise_db` |
| `redis` | `redis:alpine` | `6379` | Prefect message broker |
| `prefect-server` | `prefecthq/prefect:3-latest` | `4200` | Orchestration API + UI (`--no-services`) |
| `prefect-services` | `prefecthq/prefect:3-latest` | — | Background scheduler & services |
| `prefect-worker` | `prefecthq/prefect:3-latest` | — | Flow executor, pool: `local-pool` |
| `ollama` | `ollama/ollama:latest` | `11434` | LLM inference, RTX 3090 |
| `qdrant` | `qdrant/qdrant:latest` | `6333` | Vector DB |
| `neo4j` | `neo4j:latest` | `7474`, `7687` | Graph DB |
| `flowise` | `flowiseai/flowise:latest` | `3001` | AI agent builder |
| `dbgate_gui` | `dbgate/dbgate:latest` | `18978→3000` | DB admin UI |

**Service dependency graph:**
```
postgres ←── prefect-server ←── prefect-services
         ←── prefect-server ←── prefect-worker
         ←── flowise
redis    ←── prefect-server
```

**Volume mounts (bind):**
```
./postgres_data → /var/lib/postgresql/data
./ollama_storage → /root/.ollama
./qdrant_storage → /qdrant/storage
./neo4j_data → /data
```

**Key env vars:**
```
PREFECT_API_URL=https://pve.prefect.adzv-pt.dev/api
OLLAMA_GPU=nvidia
```

**prefect-worker entrypoint** (on container start):
```bash
pip install -r /mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts/requirements.txt
prefect worker start --pool local-pool
```

---

### 5.2 VPS Stack (Cloud Control Plane)

All services on external Docker network `web_proxy`.

| Container | Image | Role |
|---|---|---|
| `n8n` | `n8nio/n8n:latest` | Automation workflows |
| `open-webui` | `ghcr.io/open-webui/open-webui:main` | Chat frontend → Ollama via Tailscale |
| `langfuse-web` | `langfuse/langfuse:3` | LLM observability frontend |
| `langfuse-worker` | `langfuse/langfuse-worker:3` | Async observability processing |
| `postgres` | `postgres:latest` | n8n + Langfuse database |
| `clickhouse` | `clickhouse/clickhouse-server` | Langfuse trace storage |
| `redis` | `valkey/valkey:8-alpine` | Langfuse + n8n broker |
| `minio` | `minio/minio` | Langfuse blob storage |
| `caddy` | `caddy:2-alpine` | Reverse proxy, TLS termination |

**Key env vars:**
```
OLLAMA_BASE_URL=http://10.10.10.50:11434   # Open WebUI → PVE via Tailscale
WEBHOOK_URL=https://n8n.adzv-pt.dev
```

**Volume mounts (bind):**
```
./postgres_data    → /var/lib/postgresql/data
./n8n_data         → /home/node/.n8n
./n8n_backups      → /backup
./clickhouse_data  → /var/lib/clickhouse
./caddy_data       → /data
./caddy_config     → /config
```

> **Design rationale:** Langfuse's stateful dependencies (Clickhouse, Redis, MinIO) live on VPS to prevent SSD wear on the local NVMe. All LLM compute stays on PVE/RTX 3090.

---

## 6. AI / ML Stack

### Ollama

| Parameter | Value |
|---|---|
| Endpoint (internal) | `http://ollama:11434` (Docker) / `http://10.10.10.50:11434` (Tailscale) |
| Endpoint (external) | `https://ollama.adzv-pt.dev` |
| GPU binding | RTX 3090 via Docker `nvidia` runtime |
| Storage | `./ollama_storage:/root/.ollama` |

**Deployed models:**
```
DeepSeek-R1-Distill-Llama-70B  Q3_K_M / IQ4_XS  — fits 24 GB VRAM
DeepSeek-R1-32B                Q4_K_M
Qwen2.5-Coder-32B              —  ad-hoc SQL generation
nomic-embed-text               —  vector embeddings for Qdrant
```

### Qdrant

| Parameter | Value |
|---|---|
| Role | Semantic search for engineering property lookups and RAG |
| Endpoint | `http://qdrant:6333` (internal) / `6333` (Tailscale) |
| Storage | `./qdrant_storage:/qdrant/storage` |

### Neo4j

| Parameter | Value |
|---|---|
| Role | Knowledge graph: Tag→Parent, Tag→Document relationships |
| HTTP | `7474` |
| Bolt | `7687` |
| Auth | `neo4j` / `5013d89f19fd063bd0ff1e5442c4dd5c` |
| Storage | `./neo4j_data:/data` |
| External | `https://neo4j.adzv-pt.dev` |

### Flowise

| Parameter | Value |
|---|---|
| Role | Visual AI agent builder, connects to Ollama + Qdrant + Neo4j |
| Port | `3001` |
| DB | `flowise_db` on shared PostgreSQL |
| External | `https://flowise.adzv-pt.dev` |

---

## 7. Python / ETL Environment

**Runtime:** Python 3.12 inside `prefecthq/prefect:3-latest`

**Key libraries:**
```
pandas            — read_excel(dtype=str, na_filter=False)
sqlalchemy 2.x    — async, engine.begin() pattern
asyncpg           — async PostgreSQL driver
prefect 3.x       — orchestration
```

**DB connection string:**
```
postgresql+asyncpg://postgres_admin:<password>@postgres:5432/engineering_core
```

**Prefect API URL:**
```
https://pve.prefect.adzv-pt.dev/api
```

**Work pool:** `local-pool` (Process worker inside container)

**ETL code layout:**
```
/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts/
  edw/
    etl/
      flows/        # Prefect flow definitions
      tasks/        # Prefect task functions
        common.py   # Shared helpers: load_config, calculate_row_hash, clean_string
```

**Core data integrity rules:**
- UPSERT via `row_hash` (MD5/SHA) comparison — minimizes DB writes
- `lookup.get(value) if value else None` — strict FK resolution, never auto-creates reference rows
- Raw source values always preserved in `_raw` columns
- SCD tracking: every change to `project_core.tag` → logged to `project_core.tag_history` (New / Updated / Deleted)
- `NaT` / empty strings → explicitly converted to Python `None` before DB insert

---

## 8. Database Schema Overview

**PostgreSQL instance:** `postgres_db` container, port `5432`

| Database | Used By | Description |
|---|---|---|
| `engineering_core` | ETL / Jackdaw | Master engineering data warehouse |
| `prefect` | Prefect server | Orchestration state |
| `flowise_db` | Flowise | Agent configs and chat history |

**Schemas in `engineering_core`:**

| Schema | Contents |
|---|---|
| `reference_core` | Master reference data: companies, plants, areas, articles, purchase orders |
| `project_core` | Tags, equipment, documents, property values, tag history |
| `ontology_core` | Classes, properties, class-property mappings |
| `mapping` | Tag↔Document, Tag↔SECE, Document↔PO relationships |
| `audit_core` | Validation logs, quality reports |

**Key design patterns:**
- All PKs: `UUID` (`gen_random_uuid()`)
- CDC: `row_hash TEXT` on every mutable entity table
- All timestamps: `TIMESTAMP WITH TIME ZONE`
- Schema prefix required on all SQL (`project_core.tag`, not just `tag`)

---

## 9. Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                    Cloud VPS                             │
│  Caddy (TLS) → n8n · Open WebUI · Langfuse stack       │
│  Domain: adzv-pt.dev                                    │
└──────────────────┬──────────────────────────────────────┘
                   │ Tailscale (WireGuard)
┌──────────────────▼──────────────────────────────────────┐
│              Proxmox PVE (10.10.10.0/24)                │
│                                                          │
│  LXC 200 (10.10.10.50) — ai-compute                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Docker: postgres · redis · prefect · ollama    │   │
│  │          qdrant · neo4j · flowise · dbgate      │   │
│  │  GPU: RTX 3090 via cgroup2 bind-mount           │   │
│  │  Data: /mnt/shared-data (HDD bind mount)        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  LXC 103 (10.10.10.60) — sftpgo                        │
│  ┌────────────────────────────────────────────────┐    │
│  │  SFTPGo: WebDAV :8090 · Admin :8080           │    │
│  │  Data: /srv/sftpgo/data → 4TB HDD             │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  LXC 999 — Tailscale subnet router                      │
│  Host: NVIDIA driver 580 · kernel 6.14.11-5-pve        │
└─────────────────────────────────────────────────────────┘
```
