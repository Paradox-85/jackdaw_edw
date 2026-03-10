## 1️⃣ SCD Type 2 Expert (scd2.md)

```markdown
---
name: SCD Type 2 Expert
description: Generate SCD Type 2 logic for warehouse tables (tags, documents, properties)
tags: [etl, scd2, audit, sql, postgres]
trigger_keywords: ["scd2", "scd type 2", "change tracking", "history"]
---

# SCD Type 2 Patterns for EDW

**CRITICAL**: Always use hash comparison before UPSERT.

## SQL Pattern

```sql
/*
Purpose: Sync tags with SCD Type 2.
Params: @batch_date.
Output: Updated/inserted rows + history entries.
Changes: 2026-03-09 - Added hash validation.
*/

-- Why MERGE: Atomic operation, no race conditions
MERGE INTO project_core.tag AS target
USING (
    SELECT tag_code, tag_name, MD5(CONCAT(tag_code, '|', tag_name)) AS row_hash
    FROM staging.tag
    WHERE load_date = @batch_date
) AS source
ON target.tag_code = source.tag_code
    AND target.row_hash != source.row_hash  -- Only if changed
WHEN MATCHED THEN
BEGIN
    -- Log change BEFORE update
    INSERT INTO project_core.tag_history (tag_id, status, old_values, new_values, changed_at)
    VALUES (target.id, 'UPDATED', 
            JSON_OBJECT('tag_name', target.tag_name, 'row_hash', target.row_hash),
            JSON_OBJECT('tag_name', source.tag_name, 'row_hash', source.row_hash),
            GETDATE());
    
    -- Update main table
    UPDATE SET
        tag_name = source.tag_name,
        row_hash = source.row_hash,
        updated_at = GETDATE()
    WHERE target.id = target.id;
END
WHEN NOT MATCHED BY TARGET THEN
BEGIN
    -- Insert new tag
    INSERT INTO project_core.tag (tag_code, tag_name, row_hash, created_at)
    VALUES (source.tag_code, source.tag_name, source.row_hash, GETDATE());
    
    -- Log new record
    INSERT INTO project_core.tag_history (tag_id, status, new_values, changed_at)
    VALUES (SCOPE_IDENTITY(), 'NEW', 
            JSON_OBJECT('tag_code', source.tag_code, 'tag_name', source.tag_name),
            GETDATE());
END;
```

## Python Pattern

```python
import hashlib
from sqlalchemy import text, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

async def sync_tags_with_scd2(
    session: AsyncSession,
    csv_path: str,
    batch_size: int = 500
) -> dict[str, int]:
    """
    Sync tags with SCD Type 2 change tracking.
    
    Why: Detect changes via hash, minimize writes, maintain audit trail.
    """
    df = pd.read_csv(csv_path, dtype=str, na_filter=False)
    df = df.where(pd.notna(df), None)
    
    # Generate row hashes
    df['row_hash'] = df.apply(
        lambda row: hashlib.md5(
            f"{row['tag_code']}|{row['tag_name']}".encode()
        ).hexdigest(),
        axis=1
    )
    
    # Build lookup for existing tags
    existing_stmt = select(Tag.tag_code, Tag.id, Tag.row_hash)
    existing_rows = await session.execute(existing_stmt)
    existing_lookup = {code: (id, hash_val) for code, id, hash_val in existing_rows.fetchall()}
    
    result = {"inserted": 0, "updated": 0, "failed": 0}
    
    async with session.begin():
        for idx, row in df.iterrows():
            tag_code = row['tag_code']
            
            if tag_code in existing_lookup:
                existing_id, existing_hash = existing_lookup[tag_code]
                
                # Only update if hash differs
                if existing_hash != row['row_hash']:
                    # Log to history BEFORE update
                    history = TagHistory(
                        tag_id=existing_id,
                        status='UPDATED',
                        old_values={'tag_name': existing_hash},
                        new_values={'tag_name': row['tag_name']},
                        changed_at=datetime.now(timezone.utc)
                    )
                    session.add(history)
                    
                    # Update main table
                    stmt = update(Tag).where(Tag.id == existing_id).values(
                        tag_name=row['tag_name'],
                        row_hash=row['row_hash']
                    )
                    await session.execute(stmt)
                    result['updated'] += 1
            else:
                # New tag
                new_tag = Tag(
                    tag_code=tag_code,
                    tag_name=row['tag_name'],
                    row_hash=row['row_hash']
                )
                session.add(new_tag)
                result['inserted'] += 1
    
    return result
```

## Key Rules

1. **Always hash** before UPSERT (MD5 or SHA256)
2. **Log BEFORE update** to tag_history
3. **Status values**: NEW, UPDATED, DELETED
4. **Store old/new values** as JSONB
5. **Compare hash** to detect actual changes (avoid noise updates)

## Tables Needing SCD2
- project_core.tag + tag_history
- project_core.document + document_history
- project_core.property_value + property_value_history
```

---