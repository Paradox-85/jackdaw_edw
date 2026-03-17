---
name: edw-sql-schema
description: EDW database schema reference — tables, FKs, indexes for Jackdaw project
---
# EDW Schema Reference

**Canonical source:** `sql/schema.sql` — always check before any DB change.
**Live validation:** pgedge MCP at `https://ai-db.adzv-pt.dev/mcp/v1`

## Schemas
`project_core` | `ontology_core` | `mapping` | `audit_core`

## Key tables

| Table | Key columns |
|-------|-------------|
| `project_core.tag` | UUID PK, `tag_code` UNIQUE, `row_hash` VARCHAR(32), `tag_parent_id` UUID FK(self) |
| `project_core.tag_history` | `tag_id` FK, `old_value` JSONB, `new_value` JSONB, `status` (New/Updated/Deleted) |
| `project_core.tag_parent` | `child_id` FK, `parent_id` FK — resolved after main sync |
| `project_core.tag_semantic` | `embedding VECTOR(384)` (Ollama), `description_enriched` TEXT |
| `audit_core.log_entry` | `operation`, `table_name`, `rows_affected`, `success`, `error_message` |

## Indexes
- Partial: `CREATE INDEX ON project_core.tag(tag_parent_id) WHERE tag_parent_id IS NOT NULL`
- Recency: `CREATE INDEX ON project_core.tag_history(created_at) WHERE created_at > NOW() - INTERVAL '90 days'`

## Quick validation
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'project_core';
SELECT COUNT(*) FROM project_core.tag WHERE row_hash IS NULL; -- should be 0
```
