# CRS Module – Complete Summary

**Project**: Jackdaw EDW  
**Module**: CRS (Customer Request System) Management  
**Phase**: 1 – Data Ingestion & Schema  
**Delivery Date**: 2026-03-26  

---

## 📦 Deliverables Overview

You have received **5 complete files** implementing the CRS module from scratch:

| # | File | Type | Size | Purpose |
|---|------|------|------|---------|
| 1 | `migration_011_crs_module.sql` | SQL | ~380 lines | Creates 3 tables + seed data + indexes |
| 2 | `sync_crs_data.py` | Python (Prefect) | ~450 lines | Retroactive loader (Prefect 3.x flow) |
| 3 | `crs_excel_parser_db.py` | Python | ~380 lines | Standalone parser + DB writer (testing) |
| 4 | `CRS_MODULE_DEPLOYMENT_GUIDE.md` | Documentation | ~450 lines | Full deployment guide (5 steps + troubleshooting) |
| 5 | `CRS_QUICK_START.md` | Checklist | ~80 lines | Quick 5-step deployment (~15 min) |

---

## 🏗️ Architecture

### **Data Flow**

```
CRS Excel Files                 Parser                    PostgreSQL
─────────────────────────────────────────────────────────────────────

  DOC_COMMENT_*.xlsx ──┐
                       ├─→ crs_excel_parser.py (extract) ──→ Row Hash
                       ├─→ Merge (group + detail) ─────────→ Comment ID
  JDAW_*.xlsx ─────────┘

                                                         ┌─→ audit_core.crs_comment
                                                         ├─→ audit_core.crs_comment_history
  Upsert to DB ◀──────────────── Prepare ◀──────────────┤
  (ON CONFLICT)                 (SCD2)                   └─→ audit_core.sync_run_stats
```

### **Table Relationships**

```
audit_core.crs_comment
├─ PK: id (UUID)
├─ UNIQUE: comment_id (TEXT)
├─ ↓ audit_core.crs_comment_history
│  ├─ FK: comment_id → crs_comment.id
│  └─ Tracks: INSERT/UPDATE/DELETE changes
│
└─ → audit_core.crs_validation_query (FK: applicable_validation_query_id)
   ├─ Links comments to validation SQL queries
   ├─ By category: tag_missing, property_defect, etc.
   └─ Seed data: 4 example queries
```

---

## 🗂️ Database Schema (Phase 1)

### **Table 1: `audit_core.crs_comment` (Main Storage)**

**Purpose**: Store parsed CRS comments from Excel files + AI processing metadata

**Key Columns**:

| Group | Columns | Notes |
|-------|---------|-------|
| **Identity** | `id` (PK), `comment_id` (UNIQUE) | comment_id = `{doc_number}#{row_hash[:8]}` |
| **Source Metadata** | `doc_number`, `revision`, `return_code`, `transmittal_*` | From DOC_COMMENT_*.xlsx header |
| **Comment Content** | `group_comment`, `comment` | group = main topic, comment = detail |
| **Related Entities** | `tag_name`, `property_name` | Extracted from detail sheet if found |
| **Response** | `response_vendor`, `formal_response`, `response_approval_date` | Vendor reply + final approved response |
| **LLM Fields** (Phase 2) | `llm_category`, `llm_category_confidence`, `llm_response` | Auto-classification + generated reply |
| **Validation** (Phase 2) | `applicable_validation_query_id`, `validation_status`, `validation_result_json` | Link to SQL query + execution result |
| **Status** | `status` | RECEIVED\|IN_REVIEW\|RESPONDED\|APPROVED\|CLOSED |
| **Audit (SCD2)** | `row_hash`, `sync_status`, `sync_timestamp`, `object_status` | Change tracking |
| **Raw Data** | `_raw_*` columns | Original values for debugging |

**Indexes**: 7 — on status, category, tag, doc, source_file, sync_status, transmittal_date, row_hash

**Constraints**:
- PK on `id`
- UNIQUE on `comment_id`
- FK to `crs_validation_query.id` (soft FK, nullable)

---

### **Table 2: `audit_core.crs_validation_query` (Query Registry)**

**Purpose**: Register SQL validation queries linked to comment categories

**Key Columns**:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Unique query identifier |
| `query_code` | TEXT UNIQUE | Code like `CRS_TAG_EXISTS` |
| `query_name` | TEXT | Human-readable name |
| `category` | TEXT | Comment category (link field) — e.g., `tag_missing`, `defect_pattern` |
| `sql_query` | TEXT | SELECT query (may use `:param` placeholders) |
| `expected_result` | TEXT | Description of PASS condition |
| `has_parameters` | BOOLEAN | True if query is parametric |
| `parameter_names` | TEXT[] | Array of `:param` names |
| `is_active` | BOOLEAN | Enable/disable query |
| `created_at`, `updated_at` | TIMESTAMP | Auto-tracked |
| `object_status` | TEXT | Active\|Inactive |

**Seed Data** (4 example queries):

1. **CRS_TAG_EXISTS** — Category: `tag_missing`
   - Validates tag exists in `project_core.tag`
   - Parametric: `:tag_name`

2. **CRS_TAG_PROPERTY_EXISTS** — Category: `property_missing`
   - Validates property value defined for tag
   - Parametric: `:tag_name`, `:property_code`

3. **CRS_DEFECT_IN_VALIDATION_RULES** — Category: `defect_pattern`
   - Checks for defect patterns in validation results
   - Non-parametric (aggregation query)

4. **CRS_DOCUMENT_ACTIVE** — Category: `document_inactive`
   - Validates document exists and active
   - Parametric: `:doc_number`

---

### **Table 3: `audit_core.crs_comment_history` (SCD Type 2)**

**Purpose**: Audit trail — track all INSERT/UPDATE/DELETE operations

**Columns**:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | History record ID |
| `comment_id` | UUID FK | Reference to `crs_comment.id` |
| `change_type` | TEXT | INSERT\|UPDATE\|DELETE |
| `changed_fields` | JSONB | `{field: {old: X, new: Y}}` |
| `changed_by` | TEXT | User or system making change |
| `change_reason` | TEXT | Why change was made |
| `changed_at` | TIMESTAMP | When change occurred |
| `run_id` | UUID | Prefect run_id for traceability |

**Indexes**: On comment_id, changed_at, change_type

---

## 🔧 Code Components

### **1. `sync_crs_data.py` (Prefect Flow)**

**Location**: `etl/flows/sync_crs_data.py` (after deployment)

**Key Features**:
- ✅ Parallel file processing (ThreadPoolExecutor, 6 workers)
- ✅ Retroactive scan of `/mnt/shared-data/ram-user/Jackdaw/EIS-Data/`
- ✅ Handles both DOC_COMMENT_* and JDAW_* file patterns
- ✅ Merged cell resolution (openpyxl)
- ✅ Row hash calculation (MD5) for SCD2
- ✅ Comment ID generation
- ✅ Batch upsert with ON CONFLICT
- ✅ Audit logging to sync_run_stats
- ✅ Error handling + logging

**Main Flow Function**:
```python
@flow(name="Sync CRS Comments (Retroactive)")
def sync_crs_data_flow(debug_mode: bool = False) -> dict
```

**Execution Time**: ~5–15 min (depending on file count)

**Output**:
```python
{
    "run_id": "a3f2b1c8...",
    "files_processed": 12,
    "records_parsed": 1245,
    "records_loaded": 1245,
    "errors": 0,
    "status": "SUCCESS"
}
```

---

### **2. `crs_excel_parser_db.py` (Standalone Parser)**

**Purpose**: Test/debug parser (optional, for development)

**Key Functions**:
- `discover_files()` — Find main + detail file pairs
- `parse_main_file()` — Extract header + comments from DOC_COMMENT_* file
- `_load_detail_file_impl()` — Load detail sheets from JDAW_* file
- `find_matching_sheet()` — Match comment topic to detail sheet
- `process_key()` — Extract records from one document
- `prepare_crs_records()` — Add row_hash + comment_id
- `upsert_crs_comments()` — Write to DB with ON CONFLICT

**Usage**:
```bash
export DB_URL="postgresql://user:pass@host:5432/db"
python crs_excel_parser_db.py
```

---

### **3. `migration_011_crs_module.sql` (DDL)**

**Contents**:

1. **CREATE TABLE** × 3
   - `crs_comment`
   - `crs_validation_query`
   - `crs_comment_history`

2. **CREATE INDEX** × 7
   - On frequently queried columns

3. **CREATE TRIGGER** × 1
   - Auto-update `updated_at` on `crs_validation_query`

4. **INSERT** × 4 seed queries into `crs_validation_query`

5. **Comments** + verification queries

---

## 🚀 Deployment Process

### **Quick Deployment (15 min)**

See `CRS_QUICK_START.md`:

1. Run migration SQL
2. Test parser (optional)
3. Copy flow to project
4. Deploy Prefect flow
5. Run initial sync

### **Detailed Deployment (with troubleshooting)**

See `CRS_MODULE_DEPLOYMENT_GUIDE.md`:
- Prerequisites
- Step-by-step instructions
- Verification queries
- Configuration options
- Troubleshooting section

---

## 📊 Data Model Examples

### **Example Record** (crs_comment)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "comment_id": "JDAW-KVE-E-IN-2347-00002#a7c2f1b9",
  "doc_number": "JDAW-KVE-E-IN-2347-00002",
  "revision": "A05",
  "transmittal_date": "2025-08-15",
  "group_comment": "Design Review — Pressure Vessel Concerns",
  "comment": "Pressure rating unclear — verify against ASME code",
  "tag_name": "PV-101",
  "property_name": "DESIGN_PRESSURE",
  "status": "RECEIVED",
  "llm_category": null,
  "llm_response": null,
  "validation_status": null,
  "row_hash": "a7c2f1b9c3e1f5a2...",
  "sync_status": "SYNCED",
  "object_status": "Active"
}
```

### **Example Validation Query** (crs_validation_query)

```json
{
  "query_code": "CRS_TAG_EXISTS",
  "query_name": "Check if tag exists in database",
  "category": "tag_missing",
  "sql_query": "SELECT id, tag_name, tag_status FROM project_core.tag WHERE tag_name = :tag_name AND object_status = 'Active'",
  "expected_result": "PASS: returns 1 row with tag details. FAIL: returns 0 rows.",
  "has_parameters": true,
  "parameter_names": ["tag_name"],
  "is_active": true
}
```

---

## 🔄 Integration Points

### **With Existing Jackdaw EDW**

| Component | Integration |
|-----------|-----------|
| **Database** | Uses existing `engineering_core` DB, `audit_core` schema |
| **Config** | Reads from `config/db_config.yaml` (existing) |
| **Prefect** | Follows same patterns as `sync_tag_data.py`, `sync_doc_data.py` |
| **Tasks** | Uses `tasks.common.load_config()`, `get_db_engine_url()` |
| **Audit** | Logs to `audit_core.sync_run_stats` (existing) |
| **UI** | Stub exists: `ui/pages/crs_assistant.py` (Phase 2 activation) |

### **Future Integration (Phase 2)**

| Phase | Component | Integration |
|-------|-----------|-----------|
| **Phase 2** | LLM Classification | Use Ollama (existing infra) for `llm_category` |
| **Phase 2** | Validation Execution | Prefect task to run SQL queries + store results |
| **Phase 2** | RAG Pipeline | Embed comments in Qdrant (existing), retrieve similar |
| **Phase 2** | UI | Activate `crs_assistant.py` page in EDW Control Center |

---

## 📋 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **SCD Type 2 (crs_comment_history)** | Enables temporal queries + audit trail for compliance |
| **Row Hash (MD5)** | Detect changes without schema changes; aligns with EDW pattern |
| **Comment ID as Business Key** | `{doc_number}#{row_hash[:8]}` ensures uniqueness + traceability |
| **ON CONFLICT Upsert** | Idempotent — safe to re-run; supports partial updates |
| **Separate Validation Query Table** | Decouples comment storage from validation logic; enables easy extension |
| **JSONB for Validation Result** | Flexible schema for query results; supports complex nested structures |
| **Batch Processing (500 rows)** | Balances memory usage + DB load |
| **Thread Pool (6 workers)** | Parallel file processing on multi-core; respects file lock contention |

---

## 🎯 Phase 1 Scope (What's Implemented)

✅ **Database Schema**
- 3 tables (crs_comment, crs_validation_query, crs_comment_history)
- Indexes + constraints
- Seed data (4 validation queries)

✅ **Data Ingestion**
- Excel parsing (DOC_COMMENT_* + JDAW_*.xlsx)
- Parallel processing
- Row hash + comment ID generation
- Batch upsert with change detection

✅ **Audit & Tracking**
- sync_run_stats logging
- SCD2 history table
- Change tracking (insert/update)

✅ **Prefect Integration**
- Flow deployment ready
- Retroactive loading support
- Error handling + logging

---

## 🚀 Phase 2 Scope (Next Sprint)

🔲 **LLM Classification** (TBD)
- [ ] Implement `llm_category` auto-classification
- [ ] Confidence scoring
- [ ] Store in `llm_response` + `llm_response_timestamp`

🔲 **Validation Execution** (TBD)
- [ ] Match comment category → validation query
- [ ] Execute SQL with parameters
- [ ] Store result in `validation_result_json` + `validation_status`

🔲 **Response Generation** (TBD)
- [ ] Draft response via LLM (based on validation result)
- [ ] Store in `formal_response`
- [ ] Human review workflow
- [ ] Approval tracking (`response_author`, `response_approval_date`)

🔲 **RAG Pipeline** (TBD)
- [ ] Embed comments in Qdrant
- [ ] Retrieve similar comments + responses
- [ ] Few-shot prompting for LLM

🔲 **UI Integration** (TBD)
- [ ] Activate `crs_assistant.py` page
- [ ] Review + edit responses in browser
- [ ] Export functionality

---

## 📞 Questions? Next Steps?

**To Deploy**:
1. See `CRS_QUICK_START.md` (5 steps, 15 min)
2. Or follow `CRS_MODULE_DEPLOYMENT_GUIDE.md` (detailed + troubleshooting)

**To Customize**:
- Modify `sync_crs_data.py` for different file paths or patterns
- Add more seed queries to `migration_011_crs_module.sql`
- Adjust batch size or worker count in constants

**To Extend (Phase 2)**:
- Implement LLM classification task
- Add validation query execution task
- Integrate with UI

---

**Status**: ✅ **Phase 1 Complete — Ready for Deployment**

All code follows Jackdaw EDW conventions:
- ✅ Async/await patterns where applicable
- ✅ Schema-prefixed SQL
- ✅ Proper FK resolution
- ✅ Error handling + logging
- ✅ Type hints (Python)
- ✅ Audit trail (SCD2)
- ✅ Configuration externalisation

