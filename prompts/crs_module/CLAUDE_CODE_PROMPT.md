# Claude Code Integration Prompt – CRS Module v2

**Objective**: Review, validate, and optimize CRS module schema & flows against live PostgreSQL database  
**Status**: Phase 1 v2 Ready for Code Review  
**Tools Required**: Skills (PostgreSQL, Python), MCP (PostgreSQL connector)

---

## 📋 Files to Analyze

### Primary Deliverables

| File | Purpose | Priority | Size |
|------|---------|----------|------|
| `@prompts/crs_module/migration_012_crs_module_revised.sql` | Database schema (4 tables, constraints, indexes, seed data) | **HIGH** | 450 lines |
| `@prompts/crs_module/sync_crs_data_v2.py` | Prefect 3.x flow (retroactive loader with optimizations) | **HIGH** | 550 lines |
| `@prompts/crs_module/FEEDBACK_RESOLUTIONS.md` | Mapping of peer review comments → fixes applied | **MEDIUM** | 200 lines |
| `@prompts/crs_module/IMPLEMENTATION_CHECKLIST.md` | Step-by-step deployment manual with validation queries | **MEDIUM** | 350 lines |

### Reference Files (Existing Project)

| File | Purpose | Location |
|------|---------|----------|
| `@sql/schema/schema.sql` | Canonical EDW schema (source of truth) | `@docs/sql/schema/schema.sql` or GitHub repo |
| `@etl/flows/sync_tag_data.py` | Reference pattern for Prefect flows | Project repo |
| `@etl/tasks/common.py` | Shared utilities (`load_config`, `get_db_engine_url`) | Project repo |
| `@config/config.yaml` | Database connection config | Project repo |

---

## 🎯 Code Review Tasks

### Task 1: Schema Validation Against Live DB

**Objective**: Ensure migration_012 will execute correctly on current database  
**MCP Required**: PostgreSQL connector  

**Steps**:
1. **Connect to projectcore schema**
   - Load `schema.sql` from project
   - Identify actual table/column names (case sensitivity, underscores)
   - Cross-reference with migration_012 seed queries

2. **Validate column name mappings**
   ```
   Expected (from migration_012 seed queries):
   - projectcore.tag (columns: id, tagname, tagstatus, objectstatus)
   - projectcore.document (columns: docnumber, title, status, objectstatus)
   - projectcore.propertyvalue (columns: id, propertyvalue, tagid, propertyid)
   - ontologycore.property (columns: id, code)
   
   Actual (query live DB):
   - SELECT column_name FROM information_schema.columns 
     WHERE table_schema='projectcore' AND table_name='tag'
   
   ⚠️ CRITICAL: Flag if naming differs (e.g. tag_name vs tagname)
   ```

3. **Check table existence and FK references**
   - Verify `projectcore.tag(id)` and `projectcore.document(id)` exist
   - Confirm audit_core.validation_result table (used in seed query)
   - Flag any missing prerequisite tables

4. **Deliverable**
   - ✅ Schema compatibility report: "OK to apply migration_012" or "Issues found"
   - 🔴 If issues: Provide corrected seed queries with actual column names

---

### Task 2: Python Flow Code Review

**Objective**: Ensure sync_crs_data_v2.py is production-ready  
**MCP Required**: PostgreSQL connector (for test DB operations)  

**Code Quality Checks**:

1. **Type hints & error handling**
   - Verify all functions have type annotations
   - Check try-except blocks around DB/file operations
   - Verify logger.error() used for exceptions

2. **Connection pooling & resource management**
   - Verify QueuePool config (pool_size=5, max_overflow=10)
   - Check `engine.dispose()` called at flow end
   - Verify detail file cache cleared (`_detail_cache.clear()`)

3. **Hash exclusion fields (critical for SCD2)**
   ```python
   HASH_EXCLUDE_FIELDS should be:
   {
     'sync_timestamp', 'crs_file_timestamp', 'llm_response_timestamp',
     'validation_timestamp', 'response_approval_date', 'llm_response'
   }
   
   ⚠️ Flag if any timestamp field is missing or extra fields included
   ```

4. **ON CONFLICT upsert logic**
   - Verify SQL: `ON CONFLICT (comment_id) DO UPDATE SET ...`
   - Check row_hash comparison: `WHERE audit_core.crs_comment.row_hash != EXCLUDED.row_hash`
   - Ensure idempotent behavior (safe for re-runs)

5. **Orphan sheet tracking**
   - Verify `orphan_sheets` list collected during `process_key()`
   - Check logged in `log_sync_stats()` for visibility
   - Ensure function returns `tuple[list[dict], list[str]]`

6. **Deliverable**
   - ✅ Code review sign-off: "Production-ready" or "Needs fixes"
   - 🔴 If issues: Specific line numbers + required changes

---

### Task 3: Schema vs. Flow Integration Test

**Objective**: Simulate migration + small data load on TEST database  
**MCP Required**: PostgreSQL connector with test DB access  

**Steps**:

1. **Create test environment**
   ```
   - If available: spin up separate test DB instance
   - Otherwise: test against staging schema in development DB
   - Create audit_core schema if missing
   ```

2. **Apply migration to test DB**
   - Execute `migration_012_crs_module_revised.sql`
   - Verify all 4 tables created (crs_comment, crs_comment_validation, 
     crs_comment_audit, crs_validation_query)
   - Check all indexes present (should be 15+ indexes)

3. **Run seed data queries**
   ```sql
   -- Insert 1 test comment
   INSERT INTO audit_core.crs_comment 
   (doc_number, comment_id, group_comment, comment, status, objectstatus)
   VALUES ('TEST-001', 'test#abc123', 'Test group', 'Test detail', 'RECEIVED', 'Active');
   
   -- Verify
   SELECT * FROM audit_core.crs_comment WHERE doc_number='TEST-001';
   
   -- Test M2M
   INSERT INTO audit_core.crs_comment_validation (comment_id, validation_query_id, validation_status)
   SELECT id, (SELECT id FROM audit_core.crs_validation_query LIMIT 1), 'PENDING'
   FROM audit_core.crs_comment WHERE doc_number='TEST-001';
   
   -- Verify link
   SELECT cv.validation_status, vq.query_code 
   FROM audit_core.crs_comment_validation cv
   JOIN audit_core.crs_validation_query vq ON vq.id = cv.validation_query_id;
   ```

4. **Test constraint enforcement**
   ```
   -- This should FAIL (invalid status)
   INSERT INTO audit_core.crs_comment 
   (doc_number, comment_id, group_comment, comment, status, objectstatus)
   VALUES ('TEST-002', 'test#def456', 'Test', 'Test', 'INVALID', 'Active');
   -- Expected: ERROR: new row violates check constraint "crs_comment_status_check"
   
   -- This should FAIL (invalid objectstatus)
   INSERT INTO audit_core.crs_comment 
   (doc_number, comment_id, group_comment, comment, status, objectstatus)
   VALUES ('TEST-003', 'test#ghi789', 'Test', 'Test', 'RECEIVED', 'UNKNOWN');
   -- Expected: ERROR: new row violates check constraint "crs_comment_objectstatus_check"
   ```

5. **Deliverable**
   - ✅ Integration test report: "All checks passed" or list of failures
   - 📊 Test DB structure verification (tables, indexes, constraints)
   - 🔴 If failures: Root cause analysis + recommended fixes

---

### Task 4: Performance & Scalability Review

**Objective**: Validate optimizations claimed in v2  

**Metrics to verify**:

1. **Index effectiveness**
   - Verify partial index on `llm_category_confidence < 0.7` is created
   - Check all 15 indexes exist per migration script
   - Query stats: Does `EXPLAIN ANALYZE` show index usage?

2. **Connection pooling**
   ```python
   Verify in sync_crs_data_v2.py:
   - QueuePool(pool_size=5, max_overflow=10, pool_recycle=3600)
   - Connection check before parallel processing: _check_db_connection()
   - Proper cleanup: engine.dispose()
   ```

3. **Memory optimization**
   - Row hash exclusions prevent false "modified" flags
   - Detail cache cleanup (`_detail_cache.clear()`) prevents memory leak
   - Batch size (500) is reasonable for network round-trips

4. **Deliverable**
   - ✅ Performance sign-off: "Optimizations correct" or "Recommendations"
   - 📊 Index usage analysis (if queryable in test DB)
   - 🔧 Any tuning suggestions (batch size, pool settings, etc.)

---

## 🔗 MCP PostgreSQL Connector

**Required Configuration**:

Connect to live EDW database for cross-validation:
```
URL: postgresql://[user]:[pass]@[host]:[port]/engineering_core
Schemas to access: projectcore, ontologycore, audit_core (after migration)
Required tables (for validation):
  - projectcore.tag
  - projectcore.document
  - projectcore.propertyvalue
  - ontologycore.property
  - audit_core.validation_result (if exists)
```

**Permission requirements**: SELECT on all above tables (read-only for validation)

---

## 📚 Skills to Apply

### 1. PostgreSQL Skill
- **Purpose**: Validate schema names, run integration tests
- **Key files**: 
  - `@docs/sql/schema/schema.sql` (canonical schema reference)
  - `migration_012_crs_module_revised.sql` (migration to review)
- **Queries to run**:
  ```sql
  -- Verify table existence
  SELECT table_schema, table_name FROM information_schema.tables 
  WHERE table_schema IN ('projectcore', 'ontologycore', 'audit_core')
  ORDER BY table_schema, table_name;
  
  -- Check column names (CRITICAL for seed queries)
  SELECT column_name FROM information_schema.columns 
  WHERE table_schema='projectcore' AND table_name='tag';
  
  -- Verify FKs work
  SELECT constraint_name, table_name, column_name 
  FROM information_schema.key_column_usage 
  WHERE constraint_schema='audit_core' AND table_name LIKE 'crs_%';
  ```

### 2. Python Skill
- **Purpose**: Code review of `sync_crs_data_v2.py`
- **Key checklist**:
  - Type hints on all functions ✅
  - Proper try-except around DB/file I/O ✅
  - Resource cleanup (cache, engine.dispose()) ✅
  - Idempotent upsert logic (ON CONFLICT) ✅
  - Hash exclusion fields correct ✅
  - Logger usage appropriate ✅

### 3. Prefect 3.x Skill
- **Purpose**: Verify flow structure matches project patterns
- **Compare against**: `etl/flows/sync_tag_data.py`
- **Key elements**:
  - `@flow` decorator with proper metadata ✅
  - `@task` decorators with cache_policy=NO_CACHE ✅
  - `get_run_logger()` usage ✅
  - Batch processing pattern ✅
  - Error reporting structure ✅

---

## 🎬 Execution Order

1. **Task 1** (Schema Validation) — 15 min — MCP + PostgreSQL skill
2. **Task 2** (Code Review) — 20 min — Python skill
3. **Task 3** (Integration Test) — 30 min — MCP + PostgreSQL skill
4. **Task 4** (Performance Review) — 10 min — PostgreSQL skill

**Total**: ~75 min

---

## ✅ Acceptance Criteria

**All tasks must complete with status "✅" or "REVIEW COMPLETE"**:

- [ ] Task 1: Schema validation passes (no naming conflicts)
- [ ] Task 2: Code review sign-off (production-ready)
- [ ] Task 3: Integration test passes (constraints, M2M, audit trail work)
- [ ] Task 4: Performance review passes (optimizations effective)

**If any task returns 🔴 issues**: Provide specific line numbers + recommended fixes

**Final deliverable**: Single "CRS Module v2 Code Review Report" with:
1. ✅ Go/no-go for production deployment
2. 🔴 Any blocking issues + fixes required
3. ⚠️ Warnings or recommendations for Phase 2

---

## 📞 Contact / Escalation

- **Critical blocking issue**: Escalate immediately — affects deployment timeline
- **Recommendation for improvement**: Document in Phase 2 backlog
- **Question on architecture**: Reference `FEEDBACK_RESOLUTIONS.md` for design decisions

---

**Ready for Claude Code review. Please begin with Task 1 (Schema Validation).**

