---
description: ETL pipeline logic — SCD2, row hashing, FK resolution, Prefect patterns
---

# ETL Logic

## SCD Type 2 Algorithm (mandatory for all tag sync)
```
1. Read source: dtype=str, na_filter=False
2. Load lookup caches into memory (class, area, unit, discipline, po, company, etc.)
3. Load existing tag cache: {tag_name: (id, row_hash, sync_status)}
4. For each source row:
   a. hash == cached hash  → sync_status='No Changes', skip all DB writes
   b. hash != cached hash  → UPDATE tag + INSERT audit_core.tag_status_history
   c. tag_name not in cache → INSERT tag with sync_status='New'
5. Rows in cache not seen in source → UPDATE sync_status='Deleted'
6. Second pass: sync_tag_hierarchy() resolves parent_tag_id
```

## Row Hash
```python
import hashlib
import pandas as pd

def calculate_row_hash(row: pd.Series) -> str:
    """Compute MD5 of concatenated row values for change detection."""
    combined = "|".join(str(v) for v in row.values)
    return hashlib.md5(combined.encode()).hexdigest()
```

## FK Resolution — strict pattern
```python
# Safe: returns None on miss, never raises, never auto-creates reference data
class_id = class_lookup.get(clean_string(row.get('TAG_CLASS_NAME')))

if not class_id:
    logger.warning(f"Class not found: '{row.get('TAG_CLASS_NAME')}' for tag {tag_name}")

# Always store raw value regardless of FK resolution outcome
params["cls_raw"] = clean_string(row.get('TAG_CLASS_NAME'))
params["cls_id"]  = class_id  # UUID or None
```

## Memory Cache Pattern (mandatory — never query inside row loop)
```python
# Load entire lookup BEFORE processing rows — avoids N+1 queries
with engine.connect() as conn:
    class_lookup: dict[str, uuid.UUID] = {
        row.code: row.id
        for row in conn.execute(text("SELECT code, id FROM ontology_core.class"))
    }
    tag_cache: dict[str, tuple[uuid.UUID, str, str]] = {
        row.tag_name: (row.id, row.row_hash, row.sync_status)
        for row in conn.execute(text(
            "SELECT id, tag_name, row_hash, sync_status FROM project_core.tag"
        ))
    }
```

## Mapping Tables (tag_document, tag_sece)
Process AFTER main tag UPSERT in same flow. Use identical hash + cache pattern:
```python
link_hash = calculate_row_hash(pd.Series([str(tag_id), str(doc_id)]))
cached = tag_doc_cache.get((tag_id, doc_id))
if not cached:
    # INSERT new mapping with sync_status='New'
elif cached[1] in ('New', 'Updated', 'Deleted'):
    # UPDATE sync_status to 'No Changes'
# If cached[1] == 'No Changes': skip entirely
```

## Multi-value Source Fields (space-separated)
MDR `TAG_DOC` and `SAFETY_CRITICAL_ITEM_GROUP` contain space-separated codes:
```python
doc_raw = clean_string(row.get('TAG_DOC'))
if doc_raw and tag_uuid:
    for code in [c.strip() for c in doc_raw.split(' ') if c.strip()]:
        doc_id = doc_lookup.get(code)
        if not doc_id:
            logger.warning(f"Document '{code}' not found for tag {tag_name}")
            continue
        # process mapping
```

## Prefect Task/Flow Structure
```python
@task(name="Sync Tags SCD2", retries=2, retry_delay_seconds=30)
def sync_tags(config: dict) -> dict[str, int]:
    """Sync tags from EIS source with SCD Type 2 change detection."""
    logger = get_run_logger()
    stats = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0, "errors": 0}
    # ... implementation
    logger.info(f"Tag sync complete: {stats}")
    return stats

@flow(name="Tag Register Sync", log_prints=True)
def tag_register_flow() -> None:
    """Master flow: ontology seed → tag sync → hierarchy → export."""
    sync_tags()           # phase 1: main UPSERT with SCD2
    sync_tag_hierarchy()  # phase 2: parent_tag_id second pass
```

## Worker Entrypoint (from docker-compose.yml)
Worker installs deps from requirements.txt at startup:
```
/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts/requirements.txt
```
Pool name: `local-pool` (compose) / `default-agent-pool` (entrypoint override).
