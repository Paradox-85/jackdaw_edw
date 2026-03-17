# Debug Failed ETL Sync

Use when a Prefect flow fails or produces unexpected results.

## Quick diagnosis
```bash
tail -f logs/prefect.log | grep -E "ERROR|WARNING"
prefect flow-run ls --limit 5
psql $DATABASE_URL -c "SELECT * FROM project_core.tag_history ORDER BY created_at DESC LIMIT 20;"
psql $DATABASE_URL -c "SELECT * FROM audit_core.log_entry WHERE success = false ORDER BY created_at DESC LIMIT 10;"
```

## DB state check (via pgedge MCP)
- Check cardinality: `SELECT COUNT(*) FROM project_core.tag_history WHERE status = 'Updated'`
- Check orphaned tags: `SELECT COUNT(*) FROM project_core.tag WHERE tag_parent_id IS NULL`

## Common causes
- CSV dtype mismatch → ensure `dtype=str, na_filter=False`
- FK miss → check `_raw` column for unresolved FKs
- Hash collision → verify `compute_row_hash` uses `sort_keys=True, default=str`
- Hierarchy resolved BEFORE sync → must run `task_sync_tags` first
