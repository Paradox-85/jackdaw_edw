# CRS Module Quick Start (15 minutes)

## ⚡ 5-Step Deployment Checklist

### **Step 1️⃣: Create Database Schema** (2 min)

```bash
psql -U postgres -d engineering_core -f migration_011_crs_module.sql
```

**Verify**:
```bash
psql -U postgres -d engineering_core -c "SELECT COUNT(*) FROM audit_core.crs_validation_query;"
# Should return: 4
```

---

### **Step 2️⃣: Test Parser (Optional)** (3 min)

```bash
export DB_URL="postgresql://postgres:password@localhost:5432/engineering_core"
python /home/claude/crs_excel_parser_db.py
```

---

### **Step 3️⃣: Copy Flow to Project** (1 min)

```bash
cp /home/claude/sync_crs_data.py /home/claude/jackdaw/edw/etl/flows/
```

---

### **Step 4️⃣: Deploy Prefect Flow** (3 min)

```bash
cd /home/claude/jackdaw/edw

# Test locally first
python -c "from etl.flows.sync_crs_data import sync_crs_data_flow; print(sync_crs_data_flow(debug_mode=True))"

# Deploy to Prefect (when ready)
# prefect deploy etl/flows/sync_crs_data.py:sync_crs_data_flow --name sync-crs-data
```

---

### **Step 5️⃣: Run Initial Sync** (5 min)

**Option A — Python**:
```bash
cd /home/claude/jackdaw/edw
python -c "from etl.flows.sync_crs_data import sync_crs_data_flow; print(sync_crs_data_flow())"
```

**Option B — Prefect UI** (if deployed):
1. Open Prefect dashboard
2. Find `sync_crs_data_flow`
3. Click **Run**
4. Wait for completion

---

## ✅ Verify Success

```sql
-- Check table created
SELECT COUNT(*) as total_comments FROM audit_core.crs_comment;

-- Check seed queries
SELECT COUNT(*) FROM audit_core.crs_validation_query;
-- Should return: 4

-- Check sample data
SELECT comment_id, doc_number, group_comment, status 
FROM audit_core.crs_comment LIMIT 3;
```

---

## 📋 Key Config Paths

- **CRS Files Location**: `/mnt/shared-data/ram-user/Jackdaw/EIS-Data/`
- **Flow Location**: `etl/flows/sync_crs_data.py`
- **DB Config**: `config/db_config.yaml`

---

## 🎯 What's Next?

**Phase 2** (next sprint):
- [ ] Add LLM classification (`llm_category`)
- [ ] Run validation queries based on category
- [ ] Generate formal responses

See `CRS_MODULE_DEPLOYMENT_GUIDE.md` for full details.

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| "File not found" | Check: `ls /mnt/shared-data/ram-user/Jackdaw/EIS-Data/*.xlsx` |
| "Table already exists" | Migration uses `IF NOT EXISTS` — safe to re-run |
| "Connection refused" | Verify DB running: `psql -c "SELECT version();"` |
| "No records loaded" | Check file structure matches expected patterns |

---

**Status**: ✅ Phase 1 Complete — Ready for Phase 2 (LLM integration)
