## 2️⃣ EDW Schemas Reference (edw_schemas.md)

```markdown
---
name: EDW Schemas
description: Quick reference for all database tables, relationships, and constraints
tags: [schema, postgres, database, edw]
trigger_keywords: ["tag", "history", "schema", "table", "foreign key"]
---

# EDW Database Schemas

## project_core (Main Data)

### tag
- **id** UUID PRIMARY KEY
- **tag_code** VARCHAR(255) UNIQUE (source system identifier)
- **tag_name** VARCHAR(500) (human-readable name)
- **tag_parent_id** UUID FK → tag.id (hierarchy, nullable for roots)
- **row_hash** VARCHAR(32) (MD5 for SCD2 detection)
- **updated_at** TIMESTAMP WITH TIME ZONE

**Purpose**: Master Tag Repository (MTR)  
**SCD2**: Yes (see tag_history)  
**Update Frequency**: Daily via etl/flows/main_sync.py

### tag_history
- **id** UUID PRIMARY KEY
- **tag_id** UUID FK → tag.id ON DELETE CASCADE
- **status** VARCHAR(20) CHECK (status IN ('NEW', 'UPDATED', 'DELETED'))
- **old_values** JSONB (previous state)
- **new_values** JSONB (new state)
- **changed_at** TIMESTAMP WITH TIME ZONE

**Purpose**: Audit trail for SCD Type 2  
**Rows**: ~10M (last 12 months)

### document
- **id** UUID PRIMARY KEY
- **doc_code** VARCHAR(255) UNIQUE
- **doc_name** VARCHAR(500)
- **company_id** UUID FK → ontology_core.company.id
- **row_hash** VARCHAR(32)
- **updated_at** TIMESTAMP WITH TIME ZONE

**Purpose**: Master Data Repository (MDR)  
**SCD2**: Yes (see document_history)

### document_history
- Same structure as tag_history
- **Rows**: ~5M

### property_value
- **id** UUID PRIMARY KEY
- **tag_id** UUID FK → tag.id
- **property_name** VARCHAR(255)
- **property_value** TEXT
- **unit_id** UUID FK → ontology_core.unit.id
- **version** INT (versioning, not SCD2)

### property_value_history
- Versions of property values over time

## ontology_core (References)

### classification
- **id** UUID PRIMARY KEY
- **code** VARCHAR(100) UNIQUE
- **name** VARCHAR(255)
- **description** TEXT

**Usage**: Tag classifications (e.g., PUMP, VALVE, MOTOR)

### unit
- **id** UUID PRIMARY KEY
- **code** VARCHAR(50) UNIQUE (e.g., PSI, L/min, mm)
- **name** VARCHAR(100)

### company
- **id** UUID PRIMARY KEY
- **code** VARCHAR(100) UNIQUE (e.g., AVEVA, SAP, Siemens)
- **name** VARCHAR(255)

## audit_core (Logging)

### log_entry
- **id** UUID PRIMARY KEY
- **operation** VARCHAR(100) (e.g., SYNC_TAGS, SYNC_DOC)
- **table_name** VARCHAR(100)
- **rows_affected** INT
- **success** BOOLEAN
- **error_message** TEXT
- **logged_at** TIMESTAMP WITH TIME ZONE

**Purpose**: Audit trail for compliance

## Key Relationships

```
tag ──┬─→ tag (self: parent-child hierarchy)
      └─→ tag_history (SCD Type 2 audit)

document ──┬─→ company (source system)
           ├─→ document_history (SCD Type 2)
           └─→ property_value

property_value ──→ unit (measurement)
                 └─→ property_value_history (version tracking)
```

## Foreign Key Rules

- **Never auto-create** company, classification, or unit
- **Safe lookup**: `lookup.get(code) or None`
- **Preserve original**: Store source code in `_raw_*` column on FK failure
- **Log warnings**: Always log missing FK to audit_core.log_entry

## Indexes Strategy

```sql
-- Performance: tag parent-child queries
CREATE INDEX idx_tag_parent_id ON project_core.tag(tag_parent_id)
WHERE tag_parent_id IS NOT NULL;

-- Performance: recent history queries (analytical workloads)
CREATE INDEX idx_tag_history_recent ON project_core.tag_history(changed_at)
WHERE changed_at > NOW() - INTERVAL '90 days';

-- Performance: tag code lookups (UPSERT matching)
CREATE INDEX idx_tag_code_hash ON project_core.tag(tag_code, row_hash);
```
```

---