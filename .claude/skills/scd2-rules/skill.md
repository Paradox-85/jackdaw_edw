---
name: scd2-rules
description: SCD Type 2 hash logic, tag_history rules, audit patterns for EDW Jackdaw
---
# SCD Type 2 — EDW Rules

**Hash:** `md5(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()`
**Tables:** `project_core.tag` → `project_core.tag_history` → `audit_core.log_entry`
**Status values:** `New | Updated | Deleted`

## Rules
- Write to DB ONLY if `new_hash != existing_hash`
- Always insert to `tag_history` with `old_value` JSONB and `new_value` JSONB
- Always insert to `audit_core.log_entry` (operation, table_name, rows_affected, success)
- Hierarchy resolution MUST run AFTER main tag sync (same Prefect flow, separate task)
- FK miss: NULL + warning + preserve original in `_raw` column

## Pre-commit check
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM project_core.tag_history WHERE status NOT IN ('New','Updated','Deleted');"
# Should return 0
```
