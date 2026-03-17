# Add New Tag Source

Use this command when adding a new data source to the EDW pipeline.

## Steps
1. Check `schema.sql` for `project_core.tag` structure.
2. **Use subagent (schema-validator)** to validate current DB state via pgedge.
3. Create Prefect task in `etl/tasks/tag_sync.py`:
   - Extract: `pd.read_csv(dtype=str, na_filter=False)`
   - Transform: `compute_row_hash()` for SCD2
   - Load: batch upsert with FK resolution
4. Add task to master flow with retry and error handling.
5. Test with sample data; verify `audit_core.log_entry` populated.
6. Update `schema.sql` if any DB changes (same commit).

## Prompt template
"Add new source [SOURCE_NAME] with fields [FIELDS]. Schema: project_core.tag."
