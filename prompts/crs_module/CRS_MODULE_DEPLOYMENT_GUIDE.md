# CRS Module Deployment Guide

**Last Updated**: 2026-03-26  
**Status**: Phase 1 Implementation (Data Ingestion Layer)  
**Owner**: Jackdaw EDW Project

---

## 📋 Overview

This guide walks through deploying the **CRS (Customer Request System) Module** — a new subsystem for Jackdaw EDW that:

1. **Ingests** CRS comments from Excel files (`DOC_COMMENT_*.xlsx`, `JDAW_*.xlsx`)
2. **Stores** comments in `audit_core.crs_comment` with full audit trail
3. **Manages** validation queries in `audit_core.crs_validation_query` (for AI/LLM processing)
4. **Tracks** changes via SCD Type 2 history in `audit_core.crs_comment_history`

**Phase 1 (This Deployment)**: Data ingestion + schema creation  
**Phase 2 (Future)**: LLM classification, automated validation, response generation

---

## 🗂️ Files Provided

| File | Purpose | Deployment Step |
|------|---------|---|
| `migration_011_crs_module.sql` | Creates 3 CRS tables + seed data | **Step 1** |
| `sync_crs_data.py` | Prefect 3.x flow (retroactive load) | **Step 3** |
| `crs_excel_parser_db.py` | Standalone parser (testing) | **Step 2** (optional) |
| This file | Deployment instructions | Reference |

---

## ✅ Prerequisites

- PostgreSQL 14+ (running in Docker Compose)
- Prefect 3.x (deployed on your node)
- Python 3.10+ with:
  ```bash
  pip install pandas openpyxl sqlalchemy psycopg2-binary
  ```
- CRS Excel files in: `/mnt/shared-data/ram-user/Jackdaw/EIS-Data/`

---

## 🚀 Deployment Steps

### **Step 1: Create Database Schema**

Run the migration SQL in your PostgreSQL database:

```bash
# Option A: Direct psql
psql -U postgres -d engineering_core -f migration_011_crs_module.sql

# Option B: Via DbGate or pgAdmin
# 1. Open SQL editor
# 2. Copy contents of migration_011_crs_module.sql
# 3. Execute
# 4. Verify (see Verification section below)
```

**Expected Output**:
```
CREATE TABLE
COMMENT ON TABLE
CREATE INDEX (× 7)
DROP TRIGGER
CREATE FUNCTION
CREATE TRIGGER
INSERT 0 4  ← Seed validation queries
```

**Verify**:
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'audit_core' AND table_name LIKE 'crs_%';

-- Should return:
-- crs_comment
-- crs_comment_history
-- crs_validation_query

-- Check seed queries
SELECT query_code, category, is_active 
FROM audit_core.crs_validation_query 
ORDER BY category;

-- Should return 4 seed queries (CRS_TAG_EXISTS, CRS_TAG_PROPERTY_EXISTS, etc.)
```

---

### **Step 2: Test Standalone Parser (Optional)**

If you want to test data parsing before deploying the full Prefect flow:

```bash
cd /home/claude

# Set database URL
export DB_URL="postgresql://postgres:password@localhost:5432/engineering_core"

# Run parser (standalone mode)
python crs_excel_parser_db.py

# Expected output:
# INFO | Found 12 main file(s), 8 detail key(s)
# INFO | ✓ JDAW-KVE-E-JA-6944-00001-234_A01 — 47 record(s)
# ...
# INFO | Total records parsed: 1245
# INFO | Upsert complete: 1245 inserted, 0 updated, 0 errors
```

**Check results in DB**:
```sql
SELECT COUNT(*) as total_comments FROM audit_core.crs_comment;
SELECT status, COUNT(*) FROM audit_core.crs_comment GROUP BY status;
SELECT doc_number, COUNT(*) FROM audit_core.crs_comment GROUP BY doc_number ORDER BY COUNT(*) DESC LIMIT 5;
```

---

### **Step 3: Deploy Prefect Flow**

#### **3a. Copy flow to project**

```bash
# Copy sync_crs_data.py to your Prefect flows directory
cp sync_crs_data.py /home/claude/jackdaw/edw/etl/flows/

# Verify import works
cd /home/claude/jackdaw/edw
python -c "from etl.flows.sync_crs_data import sync_crs_data_flow; print('✓ Import OK')"
```

#### **3b. Deploy to Prefect Cloud/Server**

```bash
cd /home/claude/jackdaw/edw

# Option 1: Deploy as a new deployment
python -m prefect.cli deployment create etl/flows/sync_crs_data.py:sync_crs_data_flow \
  --name "sync-crs-data" \
  --tag "crs,production" \
  --description "Load customer CRS comments from Excel files"

# Option 2: Serve locally for testing
prefect deploy etl/flows/sync_crs_data.py:sync_crs_data_flow --name sync-crs-data

# Option 3: Create deployment programmatically (in your flow entry script)
# See example below
```

#### **3c: Programmatic Deployment (Recommended)**

Add this to `etl/flows/sync_crs_data.py` main block:

```python
if __name__ == "__main__":
    # For local testing:
    result = sync_crs_data_flow(debug_mode=True)
    print(f"\n✓ Test run: {result}")
    
    # For production deployment:
    # Uncomment below and run this file once to register deployment
    # sync_crs_data_flow.serve(
    #     name="sync-crs-data",
    #     cron="0 2 * * *",  # Daily at 2 AM
    #     tags=["production", "crs", "daily"],
    # )
```

---

### **Step 4: Run Initial Sync**

#### **Option A: Via Prefect UI**

1. Open Prefect Cloud/Server
2. Navigate to Flows → `sync_crs_data_flow`
3. Click **Run** → Set `debug_mode=False` → Click **Execute**

#### **Option B: Via CLI**

```bash
# Trigger the deployment
prefect deployment run "sync-crs-data/sync-crs-data"

# Watch logs
prefect flow-run logs <run_id>
```

#### **Option C: Direct Python (Testing)**

```bash
cd /home/claude/jackdaw/edw
python -c "from etl.flows.sync_crs_data import sync_crs_data_flow; print(sync_crs_data_flow(debug_mode=True))"
```

**Expected Output**:
```
Starting CRS sync flow | Run ID: a3f2b1c8 | Debug: False
Found 12 main file(s), 8 detail key(s)
Processing 12 document(s)...
  ✓ JDAW-KVE-E-JA-6944-00001-234_A01 — 47 record(s)
  ✓ JDAW-KVE-E-JA-6944-00001-235_A02 — 52 record(s)
  ...
Total records parsed: 1245
Prepared 1245 records for upsert
Upsert: 1245 inserted/updated, 0 errors
Logged sync stats for run a3f2b1c8
CRS sync complete: {'run_id': 'a3f2b1c8', 'files_processed': 12, 'records_parsed': 1245, 'records_loaded': 1245, 'errors': 0, 'status': 'SUCCESS'}
```

---

## 🔍 Verification

### **1. Table Structure Verification**

```sql
-- List all CRS columns
\d audit_core.crs_comment

-- Expected columns:
-- id, comment_id (UNIQUE), doc_number, revision, return_code,
-- transmittal_number, transmittal_date, tag_name, property_name,
-- group_comment, comment, response_vendor, source_file, detail_file,
-- detail_sheet, crs_file_path, crs_file_timestamp, llm_category,
-- llm_response, status, formal_response, row_hash, sync_status,
-- object_status, ... (+ raw data fields)
```

### **2. Data Load Verification**

```sql
-- Row count
SELECT COUNT(*) as total_comments FROM audit_core.crs_comment;

-- Status distribution
SELECT status, COUNT(*) FROM audit_core.crs_comment GROUP BY status;

-- Document distribution (top 10)
SELECT doc_number, COUNT(*) as comment_count 
FROM audit_core.crs_comment 
GROUP BY doc_number 
ORDER BY comment_count DESC 
LIMIT 10;

-- Tag detection rate
SELECT 
  COUNT(*) as total,
  COUNT(tag_name) as with_tag,
  ROUND(100.0 * COUNT(tag_name) / COUNT(*), 1) as tag_detection_pct
FROM audit_core.crs_comment;

-- Sample records
SELECT 
  comment_id, doc_number, group_comment, tag_name, status, sync_status
FROM audit_core.crs_comment 
LIMIT 5;
```

### **3. Validation Query Verification**

```sql
-- List seed validation queries
SELECT 
  query_code, query_name, category, is_active 
FROM audit_core.crs_validation_query 
ORDER BY category;

-- Test a parametric query (example)
-- First find a tag_name in loaded comments
SELECT DISTINCT tag_name 
FROM audit_core.crs_comment 
WHERE tag_name IS NOT NULL 
LIMIT 1;

-- Then run the validation query with that tag
-- (This will be done automatically by LLM module in Phase 2)
```

### **4. Change History Verification (SCD2)**

```sql
-- Check if history table is empty (expected for first load)
SELECT COUNT(*) FROM audit_core.crs_comment_history;

-- After updates, should show history
SELECT change_type, COUNT(*) FROM audit_core.crs_comment_history GROUP BY change_type;
```

### **5. Audit Logging Verification**

```sql
-- Check sync_run_stats entry
SELECT * FROM audit_core.sync_run_stats 
WHERE target_table = 'crs_comment' 
ORDER BY start_time DESC 
LIMIT 1;

-- Expected columns: run_id, target_table, count_created, count_errors, source_file
```

---

## 🛠️ Configuration

### **Database Connection**

The Prefect flow uses `tasks.common.load_config()` to read config from:

```
/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts/config/db_config.yaml
```

Ensure this file has:
```yaml
postgres:
  user: postgres
  password: <your_password>
  host: <postgres_host>
  port: 5432
  database: engineering_core

storage:
  crs_data_dir: /mnt/shared-data/ram-user/Jackdaw/EIS-Data
```

### **CRS File Path**

By default, the flow scans: `/mnt/shared-data/ram-user/Jackdaw/EIS-Data`

To change:
1. Edit `sync_crs_data.py` line: `CRS_DATA_DIR = Path("/path/to/crs/files")`
2. Redeploy the flow

### **Batch Size**

Upsert batch size (default: 500) can be adjusted via:
```python
# In sync_crs_data.py
BATCH_SIZE = 1000  # Larger = faster, but more memory
```

---

## 📊 Data Model Reference

### **audit_core.crs_comment**

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `comment_id` | TEXT UNIQUE | Business key: `{doc_number}#{row_hash[:8]}` |
| `doc_number` | TEXT NOT NULL | Document identifier (e.g., `JDAW-KVE-E-IN-2347-00002`) |
| `revision` | TEXT | Document revision (e.g., `A05`) |
| `transmittal_date` | DATE | Customer submission date |
| `group_comment` | TEXT | High-level comment topic |
| `comment` | TEXT | Detail-level comment text |
| `tag_name` | TEXT | Related tag (if identified) |
| `property_name` | TEXT | Related property (if identified) |
| `response_vendor` | TEXT | Vendor's initial response |
| **LLM Fields** | | |
| `llm_category` | TEXT | Auto-classified category (Phase 2) |
| `llm_category_confidence` | REAL | 0.0–1.0 confidence score |
| `llm_response` | TEXT | Initial LLM-generated response (Phase 2) |
| `llm_response_timestamp` | TIMESTAMP | When LLM response was generated |
| **Validation Fields** | | |
| `applicable_validation_query_id` | UUID FK | Link to `crs_validation_query` |
| `validation_status` | TEXT | PENDING\|PASSED\|FAILED\|INCONCLUSIVE |
| `validation_result_json` | JSONB | Query execution result snapshot |
| `validation_timestamp` | TIMESTAMP | When validation last ran |
| **Resolution Fields** | | |
| `status` | TEXT | RECEIVED\|IN_REVIEW\|RESPONDED\|APPROVED\|CLOSED |
| `formal_response` | TEXT | Final approved response |
| `response_author` | TEXT | Who created formal response |
| `response_approval_date` | DATE | Approval signature date |
| **Audit Fields** | | |
| `row_hash` | TEXT | MD5 hash for SCD2 detection |
| `sync_status` | TEXT | SYNCED\|MODIFIED\|ERROR |
| `sync_timestamp` | TIMESTAMP | Last sync time |
| `object_status` | TEXT | Active\|Inactive |

### **audit_core.crs_validation_query**

Registry of SQL queries for comment validation. Linked by `llm_category`.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `query_code` | TEXT UNIQUE | Code (e.g., `CRS_TAG_EXISTS`) |
| `query_name` | TEXT | Human name (e.g., "Check if tag exists") |
| `category` | TEXT | Comment category (e.g., `tag_missing`) |
| `sql_query` | TEXT | SELECT query (may contain `:param` placeholders) |
| `expected_result` | TEXT | Description of PASS condition |
| `has_parameters` | BOOLEAN | True if query uses `:param` syntax |
| `parameter_names` | TEXT[] | Array of parameter names |
| `is_active` | BOOLEAN | Query enabled/disabled |
| `created_at`, `updated_at` | TIMESTAMP | Audit timestamps |
| `object_status` | TEXT | Active\|Inactive |

**Seed Queries** (inserted automatically):
1. `CRS_TAG_EXISTS` — Validates tag exists
2. `CRS_TAG_PROPERTY_EXISTS` — Validates property value defined
3. `CRS_DEFECT_IN_VALIDATION_RULES` — Checks defect patterns
4. `CRS_DOCUMENT_ACTIVE` — Validates document status

---

## 🐛 Troubleshooting

### **Issue**: "File not found" — `/mnt/shared-data/...`

**Solution**: Verify path and file permissions:
```bash
ls -la /mnt/shared-data/ram-user/Jackdaw/EIS-Data/*.xlsx | head -5
# Should list *.xlsx files
```

### **Issue**: "No matching detail sheet found" for most records

**Solution**: This is normal if Excel files don't follow the expected structure. Check:
- Column naming (should contain keywords: "comment", "tag name", "property name")
- Sheet names (should contain parts of the `GROUP_COMMENT` value)

### **Issue**: Database connection timeout

**Solution**: Check DB credentials in `config/db_config.yaml` and verify network:
```bash
psql postgresql://postgres:password@localhost:5432/engineering_core -c "SELECT version();"
```

### **Issue**: "ON CONFLICT syntax error"

**Solution**: Ensure PostgreSQL 10+ (for `ON CONFLICT` support):
```sql
SELECT version();
```

---

## 🔗 Next Steps (Phase 2)

After Phase 1 is complete:

1. **LLM Classification**: Implement `llm_category` auto-classification
   - Use Ollama + prompt engineering to categorize comments
   - Update `audit_core.crs_comment.llm_category` + `llm_response`

2. **Validation Execution**: Automatically run SQL queries based on category
   - Prefect task to match comment category → validation query
   - Execute query and store result in `validation_result_json`
   - Update `validation_status`

3. **Response Generation**: Generate formal responses based on validation
   - Use LLM to draft response + human review
   - Store in `formal_response` + `response_approval_date`

4. **RAG Pipeline**: Implement RAG for answer retrieval
   - Embed comments in Qdrant
   - Retrieve similar comments + responses
   - Use for few-shot prompting in LLM

5. **UI Integration**: Add CRS Assistant page to EDW Control Center
   - (Stub already exists: `ui/pages/crs_assistant.py`)

---

## 📞 Support

For issues or questions:
1. Check logs: `prefect flow-run logs <run_id>`
2. Verify data: SQL queries in Verification section
3. Contact: Jackdaw EDW project team

---

## 📝 Change Log

| Date | Change |
|------|--------|
| 2026-03-26 | Phase 1: Initial schema + Prefect flow deployment |
| 2026-04-XX | Phase 2: LLM classification + validation (planned) |
| 2026-05-XX | Phase 3: RAG pipeline + response generation (planned) |

