---
description: Audit logging — mandatory obligations for every flow
---

# Audit Rules

Every flow that writes to `project_core.*` or `mapping.*` MUST:

## 1. sync_run_stats — INSERT on start
```python
import uuid
from datetime import datetime

run_id = str(uuid.uuid4())

with engine.begin() as conn:
    conn.execute(text("""
        INSERT INTO audit_core.sync_run_stats
            (run_id, target_table, start_time, source_file)
        VALUES (:rid, :tbl, :st, :sf)
    """), {
        "rid": run_id,
        "tbl": "project_core.tag",   # actual target
        "st":  datetime.now(),
        "sf":  str(source_file_path),
    })
```

## 2. sync_run_stats — UPDATE on completion (always, even on partial error)
```python
with engine.begin() as conn:
    conn.execute(text("""
        UPDATE audit_core.sync_run_stats SET
            end_time        = :et,
            count_created   = :cr,
            count_updated   = :up,
            count_unchanged = :uc,
            count_deleted   = :dl,
            count_errors    = :er
        WHERE run_id = :rid
    """), {
        "et": datetime.now(),
        "cr": stats["created"],   "up": stats["updated"],
        "uc": stats["unchanged"], "dl": stats["deleted"],
        "er": stats["errors"],    "rid": run_id,
    })
```

## 3. tag_status_history — INSERT before every tag change
```python
import json

with engine.begin() as conn:
    conn.execute(text("""
        INSERT INTO audit_core.tag_status_history
            (tag_id, tag_name, source_id, sync_status, run_id, row_hash, snapshot)
        VALUES (:tid, :tn, :sid, :ss, :rid, :h, :snap)
    """), {
        "tid":  tag_id,
        "tn":   tag_name,
        "sid":  source_file_name,
        "ss":   sync_status,        # 'New' | 'Updated' | 'Deleted'
        "rid":  run_id,
        "h":    current_hash,
        "snap": json.dumps(snapshot_dict),
    })
```

## Snapshot minimum keys
```python
_SNAPSHOT_KEYS = {
    "t_stat", "cls_raw", "art_raw", "dco_raw",
    "area_raw", "unit_raw", "disc_raw", "po_raw",
}
snapshot_dict = {k: params[k] for k in _SNAPSHOT_KEYS if k in params}
```

## Prohibited
- Flows modifying project data without writing to `sync_run_stats`
- Tag changes without a `tag_status_history` entry
- Omitting the end-record UPDATE on error paths — log errors in `count_errors`, still write it
