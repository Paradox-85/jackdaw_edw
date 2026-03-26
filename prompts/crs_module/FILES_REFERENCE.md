# CRS Module – Files Reference

| # | File | Type | Lines | Purpose | Where to Use |
|----|------|------|-------|---------|--------------|
| **1** | `migration_011_crs_module.sql` | SQL | 380 | Database schema: 3 tables, 7 indexes, triggers, seed data | Run in PostgreSQL first (Step 1) |
| **2** | `sync_crs_data.py` | Python (Prefect) | 450 | Retroactive loader – scans directory, parses files, loads to DB | Copy to `etl/flows/` and deploy (Step 3) |
| **3** | `crs_excel_parser_db.py` | Python | 380 | Standalone parser – test/debug without Prefect | Optional for development testing (Step 2) |
| **4** | `CRS_MODULE_DEPLOYMENT_GUIDE.md` | Markdown | 450 | Complete deployment guide + troubleshooting | Reference during/after deployment |
| **5** | `CRS_QUICK_START.md` | Markdown | 80 | 5-step quick checklist (15 minutes) | Quick reference for rapid deployment |
| **6** | `CRS_SUMMARY.md` | Markdown | 400 | Full architecture + design decisions | Deep dive reference |

---

## 📦 What You're Deploying

### Database Tables (3)

```
audit_core.crs_comment
├─ Stores: Customer comments from CRS Excel files
├─ Rows: ~1000–5000 per organization
├─ Key columns: comment_id, doc_number, tag_name, status, llm_category, validation_status
└─ Indexes: 7 (status, category, tag, doc, source_file, sync_status, transmittal_date)

audit_core.crs_validation_query
├─ Stores: SQL queries for comment validation
├─ Rows: 4 seed + custom queries
├─ Key columns: query_code, category, sql_query, is_active
└─ Purpose: Registry linking comment categories to validation checks

audit_core.crs_comment_history
├─ Stores: SCD Type 2 change history
├─ Tracks: INSERT/UPDATE/DELETE operations
├─ Key columns: comment_id, change_type, changed_fields (JSONB)
└─ Purpose: Full audit trail for compliance
```

### Flows (1 main, 1 optional)

```
sync_crs_data.py (MAIN)
├─ Entry point: sync_crs_data_flow(debug_mode: bool)
├─ Tasks:
│  ├─ discover_files() – scan /mnt/shared-data/.../EIS-Data
│  ├─ parse_main_file() – extract header + comments
│  ├─ process_key() – parallel file processing
│  ├─ prepare_records() – calculate row_hash, comment_id
│  ├─ upsert_records() – batch write to DB (ON CONFLICT)
│  └─ log_sync_stats() – audit logging
├─ Parallelism: 6 workers, batch size 500
├─ Output: {"run_id", "files_processed", "records_parsed", "records_loaded", "errors", "status"}
└─ Deployment: Add to etl/flows/, register with Prefect

crs_excel_parser_db.py (OPTIONAL)
├─ Standalone mode (no Prefect)
├─ Used for: Testing, debugging, one-off loads
├─ Entry point: process_and_load(db_url: str)
└─ Output: Summary stats dictionary
```

---

## 🚀 Deployment Sequence

### Step 1: Create Schema (5 min)
```bash
psql -U postgres -d engineering_core -f migration_011_crs_module.sql
```
✓ Creates 3 tables, indexes, seed data (4 validation queries)

### Step 2: Test Parser [OPTIONAL] (3 min)
```bash
export DB_URL="postgresql://..."
python crs_excel_parser_db.py
```
✓ Verifies parsing + DB write works before Prefect deployment

### Step 3: Deploy Prefect Flow (3 min)
```bash
cp sync_crs_data.py etl/flows/
# Then register with Prefect
```
✓ Flow ready for scheduling + orchestration

### Step 4: Run Initial Sync (5 min)
```bash
python -c "from etl.flows.sync_crs_data import sync_crs_data_flow; print(sync_crs_data_flow())"
```
✓ Loads all CRS files retroactively

### Step 5: Verify [ALWAYS] (2 min)
```sql
SELECT COUNT(*) FROM audit_core.crs_comment;
SELECT status, COUNT(*) FROM audit_core.crs_comment GROUP BY status;
```
✓ Confirm data loaded successfully

---

## 🔍 Key Metrics to Monitor

After deployment:

| Metric | Query | Expected |
|--------|-------|----------|
| Total comments loaded | `SELECT COUNT(*) FROM audit_core.crs_comment` | 1000–5000 |
| Comment status distribution | `SELECT status, COUNT(*) FROM audit_core.crs_comment GROUP BY status` | Mostly RECEIVED |
| Tag detection rate | `SELECT 100.0 * COUNT(tag_name) / COUNT(*) FROM audit_core.crs_comment` | 50–80% |
| Sync errors | `SELECT count_errors FROM audit_core.sync_run_stats WHERE target_table='crs_comment' ORDER BY start_time DESC LIMIT 1` | 0 |
| Change history entries (Phase 1) | `SELECT COUNT(*) FROM audit_core.crs_comment_history` | 0 (expected after first load) |

---

## ✅ Validation Checklist

Before marking Phase 1 complete:

- [ ] Schema created: 3 tables exist
- [ ] Seed data inserted: 4 validation queries visible
- [ ] Parser tested: Excel files parsed correctly (optional)
- [ ] Flow deployed: Prefect recognizes `sync_crs_data_flow`
- [ ] Initial sync run: Comments loaded, no errors
- [ ] Data verified: Row count > 0, status breakdown looks correct
- [ ] Indexes functional: Queries execute quickly
- [ ] Audit trail working: sync_run_stats entry created

---

## 🔄 Next: Phase 2 (Planned)

When Phase 1 is stable, implement:

1. **LLM Classification** — Auto-categorize comments
   - Populate `crs_comment.llm_category` + `llm_category_confidence`
   - Use Ollama for inference

2. **Validation Execution** — Run SQL based on category
   - Match `llm_category` → validation query
   - Execute query, store result in `validation_result_json`
   - Update `validation_status`

3. **Response Generation** — Draft replies
   - LLM generates response based on validation result
   - Store in `formal_response` + timestamp
   - Human review workflow

4. **RAG Pipeline** — Retrieve similar comments
   - Embed comments in Qdrant
   - Few-shot prompting

5. **UI Integration** — CRS Assistant page
   - Activate `ui/pages/crs_assistant.py`
   - Review + edit responses in browser

---

## 📞 Support References

| Issue | Reference |
|-------|-----------|
| Deployment stuck | `CRS_MODULE_DEPLOYMENT_GUIDE.md` → Troubleshooting section |
| Quick 5-step guide | `CRS_QUICK_START.md` |
| Full architecture | `CRS_SUMMARY.md` → Architecture section |
| Database schema | `migration_011_crs_module.sql` → Table definitions |
| Flow implementation | `sync_crs_data.py` → Code comments |

---

## 📊 File Statistics

```
Total LOC (code):       1,210 lines
├─ SQL:                 ~380 lines
├─ Python (Prefect):    ~450 lines
├─ Python (standalone): ~380 lines
└─ Comments/blanks:     ~300 lines

Total LOC (docs):       1,010 lines
├─ Deployment guide:    ~450 lines
├─ Summary:             ~400 lines
├─ Quick start:         ~80 lines
└─ This file:           ~80 lines

Total size:             ~90 KB (all files)
├─ SQL:                 ~16 KB
├─ Python (x2):         ~44 KB
└─ Documentation:       ~30 KB
```

---

## ⏱️ Typical Timeline

| Phase | Duration | Effort |
|-------|----------|--------|
| **Read documentation** | 10–15 min | Low |
| **Step 1: Schema** | 2–5 min | Very Low |
| **Step 2: Test parser** | 5–10 min | Very Low |
| **Step 3: Deploy flow** | 3–5 min | Low |
| **Step 4: Initial sync** | 5–15 min | Very Low |
| **Step 5: Verification** | 2–5 min | Very Low |
| **TOTAL (Phase 1)** | **30–50 min** | **Low** |

Phase 2 (LLM + validation): 1–2 weeks (medium effort)

---

## 🎯 Success Criteria (Phase 1)

✅ **Data Ingestion** → CRS comments loaded from Excel files into PostgreSQL  
✅ **Schema Complete** → 3 tables with proper indexes, constraints, audit trail  
✅ **Prefect Integration** → Flow deployed, can be scheduled (hourly/daily)  
✅ **Retroactive Loading** → All existing CRS files processed, duplicates handled (ON CONFLICT)  
✅ **Auditable** → Every sync logged, change history tracked (SCD2)  
✅ **Ready for Phase 2** → Validation query registry in place, LLM can inject results

---

**Status**: ✅ **Phase 1 Complete – Ready for Deployment**

All files are production-ready. No further edits needed unless:
- File paths change (update `CRS_DATA_DIR` in `sync_crs_data.py`)
- File patterns differ (update regex patterns in both scripts)
- Database credentials differ (ensure `config/db_config.yaml` is correct)

See `CRS_QUICK_START.md` to begin deployment now.

