# AGENTS.md

## Project Overview

**Engineering Data Warehouse (EDW) for Jackdaw**

- **Stack:** Prefect 3.0 | PostgreSQL (async) | Neo4j | Qdrant | Ollama
- **Language:** Python 3.10+ with async/await, SQLAlchemy 2.x
- **Hardware:** AMD Ryzen 7 7700, NVIDIA RTX 3090 (GPU for Ollama)
- **Data Path:** Symlinks in `./data/` point to `/mnt/shared-data/`
- **Purpose:** Centralized tag synchronization with SCD Type 2 tracking, semantic search, and graph relationships

---

## Setup Commands

### Prerequisites
```bash
# Install Python dependencies
pip install -r requirements.txt --break-system-packages

# Prefect setup
pip install prefect[postgres]

# Docker services (PostgreSQL, Neo4j, Qdrant, Ollama)
docker-compose up -d
```

### Environment Configuration
```bash
# Create environment file
cp .env.example .env

# Set up symbolic links to shared data
ln -s /mnt/shared-data/raw ./data/raw
ln -s /mnt/shared-data/processed ./data/processed
ln -s /mnt/shared-data/archive ./data/archive
```

### Database Initialization
```bash
# PostgreSQL schema setup
psql -U edw_user -d edw_db < sql/schema.sql

# Apply migrations (if using Alembic)
alembic upgrade head

# Verify schema
psql -U edw_user -d edw_db -c "\dt project_core.*"
```

### Prefect Server
```bash
# Start local Prefect server
prefect server start

# Deploy main ETL flow
prefect deploy --entrypoint etl/flows/tag_sync.py:main_pipeline --name "tag-sync-master"

# Access UI
open http://localhost:4200
```

### Local AI Services
```bash
# Ollama (LLM for data enrichment on RTX 3090)
ollama serve
# In another terminal: ollama pull llama2

# Neo4j (Graph database for tag relationships)
# Running via Docker, access at http://localhost:7687

# Qdrant (Vector database for semantic search)
# Running via Docker, access at http://localhost:6333
```

---

## Testing Instructions

### Unit Tests
```bash
# Run all ETL tests
pytest etl/ -v

# Run specific module
pytest etl/tasks/tag_sync.py::test_compute_row_hash -v

# With coverage report
pytest etl/ --cov=etl --cov-report=html

# Watch mode (rerun on file changes)
pytest-watch etl/
```

### Integration Tests
```bash
# PostgreSQL integration
pytest tests/integration/test_postgres.py -v

# Neo4j integration
pytest tests/integration/test_neo4j.py -v

# Qdrant/semantic search
pytest tests/integration/test_qdrant.py -v

# All integrations
pytest tests/integration/ -v
```

### Code Quality
```bash
# Format with Black
black etl/ sql/ config/

# Lint with Ruff
ruff check --fix etl/

# Type check with mypy
mypy etl/ --strict

# All checks via pre-commit
pre-commit run --all-files
```

### Database Testing
```bash
# Check PostgreSQL async connection
pytest tests/integration/test_postgres_async.py -v

# Verify SCD history tracking
pytest tests/test_scd_tracking.py -v

# FK resolution edge cases
pytest tests/test_fk_resolution.py -v
```

---

## Code Style

### Python
- **Type hints (mandatory):** All functions must have type hints
  ```python
  from typing import Optional, List
  from sqlalchemy.ext.asyncio import AsyncSession
  
  async def sync_tags(session: AsyncSession, tags: List[dict]) -> int:
      """Synchronize tags with hash comparison for SCD tracking."""
      pass
  ```
- **Async/await:** Use `async with engine.begin()` for transactional integrity
- **Formatter:** Black (line length: 100)
- **Linter:** Ruff (strict mode, no warnings)
- **Strings:** Single quotes, no f-strings for SQL (use parameterized queries)

### SQL
- **Schema prefixes (mandatory):** `FROM project_core.tag` (never bare table names)
- **UUID for IDs:** `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- **Timestamps:** Always `TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP`
- **Comments:** Explain non-obvious logic
  ```sql
  -- SCD Type 2: Track all changes to tag properties
  INSERT INTO project_core.tag_history (id, tag_id, old_value, new_value, status, created_at)
  VALUES (gen_random_uuid(), $1, $2, $3, 'Updated', CURRENT_TIMESTAMP);
  ```

### Cypher (Neo4j)
- **Indexes:** Create on frequently queried properties
  ```cypher
  CREATE INDEX ON :Tag(id)
  MATCH (parent:Tag {id: $parent_id})-[:PARENT_OF*1..5]->(child:Tag)
  RETURN child
  ```

### Markdown
- **One sentence per line** for diff readability
- **Code blocks with language:** ` ```python ... ``` `
- **Links:** Use `[text](url)` format

---

## SCD Type 2 & Data Integrity

### Hash-based UPSERT
```bash
# Before insert/update, compute MD5 hash of record
# Only write if hash differs from existing row
# Prevents unnecessary DB writes and history spam

Command: `python etl/utils/hash.py --data records.json`
```

### Foreign Key Resolution
```bash
# Never auto-create reference data
# Use .get() lookup with None fallback
# Preserve original value in _raw column on FK failure

Rule: `company_id = lookup_companies.get(name) if name else None`
```

### History Tracking
```bash
# Every change to project_core.tag triggers project_core.tag_history insert
# Status values: 'New' | 'Updated' | 'Deleted'
# Timestamps in UTC with time zone info

Log: `SELECT * FROM project_core.tag_history ORDER BY created_at DESC LIMIT 10;`
```

---

## Debugging

### Prefect Logs
```bash
# Real-time error monitoring
tail -f logs/prefect.log | grep ERROR

# View task output
prefect task-run ls

# Flow history
prefect flow-run ls --flow-name tag-sync

# Detailed run info
prefect flow-run inspect <run-id>
```

### PostgreSQL
```bash
# Check active connections
psql -U edw_user -d edw_db -c "SELECT * FROM pg_stat_activity;"

# Find locks
psql -U edw_user -d edw_db -c "SELECT * FROM pg_locks;"

# Slow queries (enable log_min_duration_statement = 1000 in postgresql.conf)
tail -f logs/postgresql.log | grep SLOW
```

### Neo4j
```bash
# Open Neo4j Browser
open http://localhost:7687

# Check node count
MATCH (n) RETURN count(n)

# Get stats
CALL apoc.meta.stats()

# Find slow queries
CALL db.listQueries()
```

### Qdrant
```bash
# Check collection status via API
curl http://localhost:6333/collections

# Monitor memory usage
docker exec qdrant qdrant-cli collection info properties
```

### Ollama
```bash
# Check loaded models
ollama list

# Test inference
ollama run llama2 "What is data engineering?"

# GPU status
nvidia-smi
```

---

## Commit & Pull Request Guidelines

### Commit Message Format
```
[module] Brief description (50 chars max)

Detailed explanation:
- What changed
- Why it changed
- Any breaking changes

Example:
[etl/tags] Fix SCD Type 2 timestamp UTC tracking

- Fixed: tag_history.created_at was using local time
- Impact: Affects only new records going forward
- Tests: Added test_scd_timezone_consistency
```

### Module Naming
```
[etl/tasks]     ETL task implementations
[etl/flows]     Prefect flow orchestration
[sql/schema]    PostgreSQL schema changes
[infra/docker]  Docker and container setup
[docs/api]      Documentation and API specs
```

### Pre-commit Checklist
- [ ] `black etl/ sql/ config/` (formatting)
- [ ] `ruff check --fix etl/` (linting)
- [ ] `mypy etl/ --strict` (type checking)
- [ ] `pytest etl/ -v` (all tests pass)
- [ ] `pre-commit run --all-files` (all hooks pass)
- [ ] No secrets in code (check .env entries)
- [ ] SCD changes tested with new test cases

### PR Title Format
```
[etl/tags] Implement tag-to-parent hierarchy sync
[sql] Add index on tag.parent_id for query performance
[infra] Update Docker Compose for local Ollama setup
[docs] Add AGENTS.md and CLAUDE.md guidelines
```

### PR Checklist
- Tests pass: `pytest etl/ -v`
- Code formatted: `black etl/`
- Linted: `ruff check etl/`
- Types checked: `mypy etl/ --strict`
- Migration (if needed): Tested with schema.sql
- Performance: Explain if query changes
- Breaking changes: Document in PR description

---

## Security Considerations

### Protected Files (Claude Code read-only)
- `.env*` files (secrets, API keys)
- `secrets/` directory (any secret material)
- `*.pem` files (SSH/TLS keys)
- `ssh/` directory (SSH configuration)
- `logs/prod/` directory (production logs)

### Before Pushing to Git
```bash
# Check for hardcoded secrets
git log -p | grep -i -E "(password|api_key|secret|token)"

# Verify .gitignore covers sensitive files
cat .gitignore | grep -E "(\.env|secrets|\.pem|ssh|logs/prod)"

# Scan staged files
git diff --cached | grep -i -E "(password|api_key)"
```

### Environment Variables
```bash
# ✅ CORRECT: Use env vars
DB_USER=${POSTGRES_USER}
DB_PASSWORD=${POSTGRES_PASSWORD}

# ❌ WRONG: Hardcoded in code
connection_string = "postgresql://user:hardcoded_password@localhost/edw_db"
```

---

## Performance Tips

### PostgreSQL
- **Indexes:** Add on all foreign keys and high-cardinality columns
  ```sql
  CREATE INDEX idx_tag_parent_id ON project_core.tag(parent_id);
  CREATE INDEX idx_tag_status ON project_core.tag(status);
  ```
- **Batch inserts:** Use multi-row INSERT for large datasets (1000+ rows)
- **Connection pooling:** Use pgbouncer for 10+ concurrent Prefect flows

### Neo4j
- **Index strategy:** Create indexes on `id` and relationship types
  ```cypher
  CREATE INDEX ON :Tag(id)
  CREATE INDEX ON :Tag(status)
  ```
- **Bulk operations:** Use APOC for 10k+ node inserts
  ```cypher
  CALL apoc.periodic.iterate(
    "UNWIND $data AS row RETURN row",
    "CREATE (t:Tag {id: row.id, name: row.name})",
    {batchSize: 1000, params: {data: rows}}
  )
  ```

### Qdrant
- **Batch embeddings:** Upload 100-1000 vectors per request
- **Memory:** Keep collection size < 10GB for RTX 3090

### Ollama (Local LLM)
- **Preload models:** Pull before ETL runs
  ```bash
  ollama pull llama2 && ollama pull neural-chat
  ```
- **GPU memory:** Monitor with `nvidia-smi`
- **Batch inference:** Queue multiple enrichment tasks

---

## Known Issues & Workarounds

### PostgreSQL Connection Timeout
- **Symptom:** `asyncpg.exceptions.TooManyConnectionsError`
- **Cause:** Too many concurrent Prefect task flows
- **Fix:** Enable pgbouncer or reduce `pool_size` in SQLAlchemy config

### Ollama Out of Memory
- **Symptom:** CUDA memory exhausted, model crashes
- **Cause:** Model too large for RTX 3090
- **Fix:** Use smaller model: `ollama pull neural-chat` instead of `llama2-70b`

### Neo4j Slow Traversals
- **Symptom:** Parent-child queries take 10+ seconds on 1M+ nodes
- **Cause:** Missing indexes on relationship properties
- **Fix:** Create indexes: `CREATE INDEX ON :Tag(id)`

### Qdrant Vector Search Slow
- **Symptom:** Search on 1M+ vectors takes >1 second
- **Cause:** Collection not indexed
- **Fix:** Use `indexing_threshold` in Qdrant config

---

## Useful Resources

- **Prefect 3.0:** https://docs.prefect.io
- **SQLAlchemy 2.x Async:** https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Neo4j Cypher Manual:** https://neo4j.com/docs/cypher-manual/current/
- **PostgreSQL Docs:** https://www.postgresql.org/docs/current/
- **Qdrant Documentation:** https://qdrant.tech/documentation/
- **Ollama Models:** https://ollama.ai
- **Project CLAUDE.md:** See ../CLAUDE.md for AI agent guidelines
- **agents.md Format:** https://agents.md/ (this file's format spec)

---

## Questions?

For AI-specific guidance, see `CLAUDE.md` (Claude Code-specific rules).  
For general questions, check the README.md or GitHub issues.
