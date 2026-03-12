# Architecture Reference

> Load when needed: `@docs/architecture.md`

## Hardware
- CPU: AMD Ryzen 7 7700
- GPU: NVIDIA RTX 3090 (24 GB VRAM) — Ollama GPU inference
- Host: Proxmox LXC (Ubuntu 24) + Docker Compose

## Docker Services (from docker-compose.yml)

| Container | Image | Ports | Role |
|---|---|---|---|
| `postgres_db` | postgres:16-bookworm | 5432 | Primary DB (`engineering_core` + `prefect` + `flowise_db`) |
| `redis` | redis:alpine | — | Prefect message broker + cache |
| `prefect-server` | prefecthq/prefect:3-latest | 4200 | Orchestration API + UI |
| `prefect-services` | prefecthq/prefect:3-latest | — | Background Prefect services (depends on `prefect-server`) |
| `prefect-worker` | prefecthq/prefect:3-latest | — | Flow executor, pool: `local-pool` |
| `ollama` | ollama/ollama:latest | 11434 | Local LLM (GPU), models in `./ollama_storage` |
| `flowise` | flowiseai/flowise:latest | 3001 | AI agent builder (DB: `flowise_db`) |
| `qdrant` | qdrant/qdrant:latest | 6333 | Vector search, storage: `./qdrant_storage` |
| `neo4j` | neo4j:latest | 7474 (HTTP), 7687 (Bolt) | Graph DB, data: `./neo4j_data` |
| `dbgate_gui` | dbgate/dbgate:latest | 18978 | DB admin UI, pre-configured for `engineering_core` |

## Key Configuration Facts
- **Prefect API URL**: `https://pve.prefect.adzv-pt.dev/api`
- **DB user**: `postgres_admin` / DB: `engineering_core`
- **Prefect worker** installs deps at startup from:
  `/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts/requirements.txt`
- **Ollama + Qdrant** mount shared data read-only:
  `/mnt/backup-hdd/sftpgo-data/ram-user/Jackdaw/Master-Data:/data/shared:ro`
- **DbGate** auth: `admin` user, connections restricted to `eng_db` only

## Service Dependencies
```
postgres ←─ prefect-server ←─ prefect-services
         ←─ prefect-server ←─ prefect-worker
         ←─ flowise
redis    ←─ prefect-server
```

## Data Access Paths
- Source EIS files: `/mnt/shared-data/ram-user/Jackdaw/`
- Project symlinks: `./data/current/` and `./data/_history/`
- Config: `config/db_config.yaml`

## Data Flow
```
EIS Excel/CSV files (./data/current/)
        ↓
seed_ontology flow
        ↓  populates ontology_core + reference_core (CFIHOS classes, UoM, picklists)
sync_tag_data flow
        ↓  SCD2 UPSERT → project_core.tag + mapping.tag_document + mapping.tag_sece
        ↓  every change → audit_core.tag_status_history (JSONB snapshot)
sync_tag_hierarchy flow
        ↓  second pass → resolves tag.parent_tag_id
export_tag_register flow
        ↓  Reverse ETL → EIS CSV (UTF-8 BOM, seq 003)

Parallel enrichment:
  Neo4j  ← Tag→Parent, Tag→Doc graph edges
  Qdrant ← property_value embeddings via Ollama
  Flowise ← AI agents querying EDW
```

## AI Layer
| Component | Purpose |
|---|---|
| **Ollama** (RTX 3090) | Anomaly detection, description enrichment, NLP on engineering text |
| **Qdrant** | Semantic property search (find similar instruments by spec) |
| **Neo4j** | Impact-chain: "if this valve fails, which docs/systems are affected?" |
| **Flowise** | Business-user natural language interface to EDW data |
