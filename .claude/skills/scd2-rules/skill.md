---
name: scd2-rules
description: SCD Type 2 hash logic, tag_history rules, audit patterns for EDW Jackdaw
---
# SCD Type 2 — EDW Rules

**Hash:** `hashlib.md5("|".join(str(v) for v in row.values).encode()).hexdigest()`
**Tables:** `project_core.tag` → `audit_core.tag_status_history` → `audit_core.sync_run_stats`
**Status values:** `New | Updated | No Changes | Deleted`

## Rules
- Write to DB ONLY if `new_hash != existing_hash`
- Always insert to `tag_status_history` with `old_value` JSONB and `new_value` JSONB
- Always update `audit_core.sync_run_stats` (operation, table_name, rows_affected, success)
- Hierarchy resolution MUST run AFTER main tag sync (same Prefect flow, separate task)
- FK miss: NULL + warning + preserve original in `_raw` column

> ⚠️ Hash formula must match `rules/etl-logic.md` exactly.
> Never use `json.dumps` for hashing — field order differs between implementations.

## Pre-commit check
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM audit_core.tag_status_history WHERE sync_status NOT IN ('New','Updated','No Changes','Deleted');"
# Should return 0
```
