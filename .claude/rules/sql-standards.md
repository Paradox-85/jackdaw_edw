---
description: SQL standards for PostgreSQL (engineering_core)
---

# SQL Standards

## Core Rules
- **Always schema-prefix**: `project_core.tag` — never bare `tag`
- **All PKs/FKs**: `UUID` with `DEFAULT gen_random_uuid()`
- **Timestamps**: `TIMESTAMP DEFAULT now()` (not TIMESTAMPTZ unless explicitly needed)
- **Soft deletes**: set `object_status = 'Inactive'` — never `DELETE FROM project_core.*`
- **No SELECT ***: always list columns explicitly in production queries

## Schema Map (from schema.sql — never invent tables or columns)
```
project_core   → tag, document, property_value
ontology_core  → class, property, class_property, uom, uom_group, validation_rule
reference_core → area, process_unit, discipline, company, purchase_order,
                 po_package, site, plant, project, article, model_part, sece
mapping        → tag_document, tag_sece
audit_core     → sync_run_stats, tag_status_history
```

## Query Header (required on all non-trivial queries)
```sql
/*
Purpose: Extract active tags with resolved FK references for EIS export (seq 003).
Gate:    object_status = 'Active' — primary indexed filter.
Changes: 2026-03-12 — Initial implementation.
*/
```

## UPSERT Pattern
```sql
INSERT INTO project_core.tag (tag_name, row_hash, sync_status, sync_timestamp, ...)
VALUES (:tag_name, :hash, 'New', now(), ...)
ON CONFLICT (tag_name) DO UPDATE SET
    row_hash       = EXCLUDED.row_hash,
    sync_status    = 'Updated',
    sync_timestamp = EXCLUDED.sync_timestamp,
    tag_status     = EXCLUDED.tag_status
    -- list each updated field explicitly
WHERE project_core.tag.row_hash != EXCLUDED.row_hash;  -- guard: skip if hash unchanged
```

## sync_status Canonical Values
| Value | When |
|---|---|
| `'New'` | Record created for the first time |
| `'Updated'` | Hash changed vs previous load |
| `'No Changes'` | Hash matches — skipped DB write |
| `'Deleted'` | Present in DB, absent in source file |

## object_status Canonical Values
`'Active'` (default) · `'Inactive'` (soft delete when record removed from source — never physical delete)

> DB audit 2026-03-16: `project_core.tag` stores `'Inactive'` for removed rows, not `'Deleted'`.
> `sync_status = 'Deleted'` marks records absent from the latest source file — separate field.

## Tag Hierarchy Resolution (second pass)
```sql
-- Run AFTER main tag UPSERT completes
UPDATE project_core.tag
SET parent_tag_id = (
    SELECT id FROM project_core.tag WHERE tag_name = :parent_name
)
WHERE tag_name = :child_name
  AND :parent_name IS NOT NULL;
```

## Inline Comment Style
```sql
-- Use LEFT JOIN: tags may have no area assigned (nullable FK)
LEFT JOIN reference_core.area a ON t.area_id = a.id
```

## Prohibited
- Inventing column names not in `schema.sql`
- `DELETE FROM` any `project_core.*` table
- Bare table names without schema prefix
- String concatenation for SQL — always use bound parameters (`:param`)
