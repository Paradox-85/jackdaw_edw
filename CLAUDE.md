# CLAUDE.md — EDW Gold Standard (Condensed)

**Version**: 2026-03-09 | **Size**: ~12k (was 85k) | **Focus**: Clarity + Compliance

---

## 🚨 LANGUAGE POLICY (CRITICAL)

**Responses to user**: RUSSIAN ONLY (Русский)  
- NO English unless user explicitly asks "на английском"
- Examples: User "Создай sync task" → You "Создал etl/tasks/sync_tags.py с SCD2 и hash"

**All code elements**: ENGLISH ONLY  
- Comments, docstrings, inline, SQL, YAML, Bash, JSON
- Example: `# Extract CSV with preserved types` ✅ | `# Извлечь CSV` ❌

---

## 📋 LINTING & CODE QUALITY (pyproject.toml)

```toml
[tool.black]
line-length = 88
target-version = 'py311'

[tool.ruff]
select = ["E", "F", "W", "UP", "I", "C90"]
ignore = ["E501"]
max-complexity = 10

[tool.mypy]
strict = true
disallow_untyped_defs = true

[tool.pydocstyle]
convention = "google"

[tool.sqlfluff]
dialect = "postgresql"
line-length = 88
```

**Setup**: `pip install pre-commit && pre-commit install`

---

## 💎 CODE GOLD STANDARD

### 1. Self-Documenting Code (Priority #1)
- Descriptive names: `sync_tags_with_scd2()` not `func1()`
- Functions <50 lines, single responsibility, type hints
- NO comments if code is obvious

```python
# ✅ GOOD: Clear intent, no comment needed
def validate_tag(tag: dict) -> bool:
    if not tag.get('tag_code'):
        return False
    return len(tag['tag_code']) <= 255
```

### 2. Comments: WHY, Not WHAT
- **Inline**: Rare, only for edges → `# Handle empty CSV from upstream failure`
- **Block**: Algorithms → `# SCD Type 2: hash before upsert (10x faster than full scan)`
- **NEVER**: `# Increment x`, commented code, TODO spam

**Special Formats**:
```python
# FIXED: NaT→None conversion bug (2026-03-09)
df = pd.read_csv(..., na_filter=False)

# Adapted from SQLAlchemy [MIT] github.com/sqlalchemy/...
async def get_attribute(obj: Base, attr: str) -> Any: ...

# TODO: Add async Ollama support [HIGH, Q2, 2-day estimate]
```

### 3. Docstrings (PEP 257 Google — MANDATORY)

```python
async def sync_tags_with_scd2(
    session: AsyncSession,
    csv_path: str,
    batch_size: int = 500
) -> dict[str, int]:
    """
    Synchronize tags from CSV to PostgreSQL with SCD Type 2.

    Args:
        session: SQLAlchemy AsyncSession for database ops.
        csv_path: Path to CSV (use symlink data/current/tags.csv).
        batch_size: Rows per batch for performance (default 500).

    Returns:
        dict with keys:
        - inserted: count of new tags
        - updated: count of modified tags
        - failed: count of errors
        - errors: list of error messages

    Raises:
        FileNotFoundError: If csv_path missing.
        IntegrityError: If FK violation.

    Example:
        >>> result = await sync_tags_with_scd2(session, 'data/current/tags.csv')
        {'inserted': 10, 'updated': 5, 'failed': 0, 'errors': []}
    """
```

---

## 🗄️ SQL STANDARDS (ANSI/PostgreSQL)

### Query Header + Inline Comments

```sql
/*
Purpose: Active tags hierarchy for dashboard queries.
Params: @equip_type (e.g. 'PUMP').
Output: tag_id, parent_name, change_count.
Errors: None (safe LEFT JOIN).
Changes: 2026-03-09 — Added 90-day filter for performance.
*/

-- Why LEFT JOIN: Preserve orphaned tags from upstream failures
WITH recent_tags AS (
    SELECT * FROM project_core.tag
    WHERE updated_at > NOW() - INTERVAL '90 days'
)
SELECT
    t.tag_code,
    p.tag_name AS parent_name,
    COUNT(DISTINCT h.id) AS change_count
FROM recent_tags t
LEFT JOIN project_core.tag p ON t.tag_parent_id = p.id
LEFT JOIN project_core.tag_history h ON t.id = h.tag_id
WHERE t.tag_code LIKE @equip_type
GROUP BY t.tag_code, p.tag_name;
```

### Stored Procedure (TRY-CATCH + Transactions)

```sql
CREATE OR ALTER PROCEDURE sp_sync_tags_scd2(
    @batch_date DATE,
    @dry_run BIT = 0
) AS
/*
Purpose: Full ETL sync with SCD Type 2 + audit logging.
Params: @batch_date (YYYY-MM-DD), @dry_run (1=test, 0=commit).
Output: @rows_affected INT OUTPUT.
Errors: TRY-CATCH rollback + audit_core.log_entry.
*/
BEGIN
    DECLARE @rows_affected INT = 0;
    
    BEGIN TRANSACTION sync_start;
    SAVE TRANSACTION sp_checkpoint;
    
    BEGIN TRY
        -- Validate: Prevent empty batch processing
        IF NOT EXISTS (
            SELECT 1 FROM staging.tag WHERE load_date = @batch_date
        )
            RAISERROR('Empty batch for date %s', 16, 1, @batch_date);

        -- Why MERGE: Atomic operation, no race conditions
        MERGE INTO project_core.tag AS target
        USING staging.tag AS source
        ON target.tag_code = source.tag_code
            AND target.row_hash != source.row_hash
        WHEN MATCHED THEN
        BEGIN
            INSERT INTO project_core.tag_history (tag_id, status, old_values, new_values)
            VALUES (target.id, 'UPDATED', NULL, NULL);
            
            UPDATE SET
                tag_name = source.tag_name,
                row_hash = source.row_hash,
                updated_at = GETDATE()
            WHERE target.id = target.id;
            SET @rows_affected += 1;
        END
        WHEN NOT MATCHED BY TARGET THEN
        BEGIN
            INSERT INTO project_core.tag (tag_code, tag_name, row_hash)
            VALUES (source.tag_code, source.tag_name, source.row_hash);
            SET @rows_affected += 1;
        END;

        IF @dry_run = 0
        BEGIN
            INSERT INTO audit_core.log_entry (operation, table_name, rows_affected, success)
            VALUES ('SYNC_TAGS_SCD2', 'project_core.tag', @rows_affected, 1);
            COMMIT TRANSACTION sync_start;
        END
        ELSE
        BEGIN
            ROLLBACK TRANSACTION sp_checkpoint;
        END;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION sp_checkpoint;
        INSERT INTO audit_core.log_entry (operation, table_name, success, error_message)
        VALUES ('SYNC_TAGS_SCD2', 'project_core.tag', 0, ERROR_MESSAGE());
        THROW;
    END CATCH;
END;
```

### Tables & Indexes (Full Context)

```sql
-- Why SCD Type 2: Historical accuracy, temporal queries, audit compliance
-- Business Rules: tag_code UNIQUE, row_hash for change detection
-- Update Frequency: Daily via Prefect flow at 02:00 UTC
CREATE TABLE project_core.tag (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Unique code from source system (AVEVA, SAP, etc)
    tag_code VARCHAR(255) NOT NULL UNIQUE,
    -- MD5 hash for UPSERT change detection
    row_hash VARCHAR(32),
    -- Parent tag for hierarchy (resolved AFTER main sync)
    tag_parent_id UUID REFERENCES project_core.tag(id) ON DELETE SET NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track changes: NEW, UPDATED, DELETED
CREATE TABLE project_core.tag_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id UUID NOT NULL REFERENCES project_core.tag(id) ON DELETE CASCADE,
    status VARCHAR(20) CHECK (status IN ('NEW', 'UPDATED', 'DELETED')),
    old_values JSONB,
    new_values JSONB,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Why partial index: 80% tags have parents, <1% queries look >90 days back
CREATE INDEX idx_tag_parent_id ON project_core.tag(tag_parent_id)
WHERE tag_parent_id IS NOT NULL;

CREATE INDEX idx_tag_history_recent ON project_core.tag_history(changed_at)
WHERE changed_at > NOW() - INTERVAL '90 days';
```

---

## 🐍 Python + SQL Integration

### Key Patterns
- **CSV**: `dtype=str, na_filter=False` + convert NaT to None
- **Hash**: SHA256/MD5 before UPSERT (minimize writes)
- **FK**: `lookup.get(code) or None` (safe fallback to NULL)
- **Batch**: 500+ rows per transaction (performance)
- **Async**: SQLAlchemy AsyncSession, await everything
- **Audit**: ALWAYS log to `audit_core.log_entry`

### SQL in Python (Inline Example)

```python
# Why MERGE: Atomic operation, no race conditions between check + insert
query = """
MERGE INTO project_core.tag AS target
USING (VALUES (%s, %s, %s)) AS source(tag_code, tag_name, row_hash)
ON target.tag_code = source.tag_code AND target.row_hash != source.row_hash
WHEN MATCHED THEN UPDATE SET tag_name = source.tag_name
WHEN NOT MATCHED THEN INSERT (tag_code, tag_name, row_hash)
    VALUES (source.tag_code, source.tag_name, source.row_hash);
"""
```

---

## 📝 YAML/Docker Comments

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15
    # Why volumes: Persist data across container restarts, separate read/write for ETL
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      # Perf tuning for Ryzen 7 7700 + RTX 3090
      POSTGRES_SHARED_PRELOAD_LIBRARIES: pg_stat_statements
```

---

## 🔍 Perplexity MCP (Research Agent)

For facts/news/updates:
- Use: `perplexity_search "Proxmox GPU passthrough latest"`
- Summarize in Russian + cite sources [1]
- Process: Query → Research → Verify → Russian response

---

## 🏗️ EDW-SPECIFIC RULES

**SCD Type 2**
- Hash before UPSERT (detect changes)
- Log ALL changes to `tag_history` (audit trail)
- Status: NEW, UPDATED, DELETED

**Foreign Keys**
- Safe lookup: `lookup.get(code) or None`
- Log warnings if FK missing
- Preserve original in `_raw_*` columns on failure

**CSV Loading**
- Use symlinks: `.data/current/`, `.data/_history/`
- `dtype=str, na_filter=False` (preserve "NA" strings)
- Convert NaT/empty to None BEFORE DB insert

**Audit Logging**
- ALWAYS insert to `audit_core.log_entry`
- Fields: operation, table_name, rows_affected, success, error_message

**Project Structure**
```
edw/
├── docker/               # PostgreSQL, Neo4j, Qdrant, Ollama
├── sql/schema/           # Tables, views, migrations
├── etl/flows/            # Prefect orchestration
├── etl/tasks/            # Atomic tasks (sync_tag, sync_doc, sync_prop)
├── config/settings.yaml  # Paths, mappings, database config
└── data/                 # Symlinks to /mnt/shared-data/
```

---

## 🧪 TESTING (Minimal Example)

```python
@pytest.mark.asyncio
async def test_sync_tags_scd2_change_detection():
    """Given: existing tag. When: hash changes. Then: UPDATE + history entry."""
    # Setup
    existing = Tag(tag_code='TAG001', row_hash='abc123')
    session.add(existing)
    
    # Execute
    result = await sync_tags_with_scd2(session, [
        {'tag_code': 'TAG001', 'row_hash': 'def456'}
    ])
    
    # Assert
    assert result['updated'] == 1
    history = session.query(TagHistory).filter_by(tag_id=existing.id).first()
    assert history.status == 'UPDATED'
```

---

## ✅ FINAL CHECKLIST (Before Code Generation)

- [ ] **Names**: Descriptive, <50 lines, type hints
- [ ] **Docstring**: FULL (summary, Args, Returns, Raises, Example)
- [ ] **Comments**: WHY not WHAT, special formats (FIXED/TODO/Adapted)
- [ ] **Linting**: black/ruff/mypy/pydocstyle/sqlfluff compliant
- [ ] **SQL**: Header (purpose/params/output), inline (why), transactions, error handling
- [ ] **EDW**: SCD2 hash, audit logging, safe FK lookup, symlinks
- [ ] **Response**: RUSSIAN to user, ENGLISH in code

---

## 📚 Sources & Standards

- **PEP 257/8**: Python docstrings, formatting
- **Google Style Guide**: Code comments, docstrings
- **Reddit r/dataengineering**: SCD2, ETL best practices
- **RealPython**: Comments, code quality
- **sqlfluff**: SQL formatting/linting

**Apply to ALL code. Regenerate on violations.**

---

*Last updated: 2026-03-09 | Reduced from 85k → 12k | Claude Code compliant*
