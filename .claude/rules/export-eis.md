---
description: EIS Reverse ETL export rules — Tag Register CSV (seq 003)
---

# EIS Export (Reverse ETL)

## Output File Naming
```
JDAW-KVE-E-JA-6944-00001-003-{doc_revision}.CSV
```
- `doc_revision` must match `^[A-Z]\d{2}$` (e.g. `A35`) — validate with regex BEFORE any DB work
- Extension is uppercase `.CSV` per EIS specification

## Encoding
**UTF-8 BOM** (`utf-8-sig`) — mandatory for Excel/EIS system compatibility.

## Filter Gate (two layers — both required)
```python
# Layer 1: SQL WHERE t.object_status = 'Active'  (indexed, primary)
# Layer 2: Python guard against upstream leaks
df = df[df["object_status"] == "Active"].copy()
```

## Sanitization (unconditional — no bypass allowed)
```python
def write_csv(df: pd.DataFrame, path: Path) -> int:
    """Write DataFrame to UTF-8 BOM CSV. Sanitizer cannot be skipped."""
    clean_df = sanitize_dataframe(df)   # strips encoding artefacts (Â², mojibake)
    clean_df.to_csv(path, index=False, encoding="utf-8-sig")
    return len(clean_df)
```

## Transforms (apply in order)
```python
df = df.rename(columns={"sync_status": "ACTION_STATUS"})
df["ACTION_DATE"] = pd.to_datetime(df["sync_timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")
df["PARENT_TAG_NAME"] = df["PARENT_TAG_NAME"].replace("unset", "")
df = df.drop(columns=["object_status", "sync_timestamp"], errors="ignore")
df = df[[c for c in EIS_COLUMNS if c in df.columns]]
```

## Column Order (strict per EIS spec JDAW-PT-D-JA-7739-00003)
```python
EIS_COLUMNS = [
    "PLANT_CODE", "TAG_NAME", "PARENT_TAG_NAME", "AREA_CODE",
    "PROCESS_UNIT_CODE", "TAG_CLASS_NAME", "TAG_STATUS",
    "REQUISITION_CODE", "DESIGNED_BY_COMPANY_NAME", "COMPANY_NAME",
    "PO_CODE", "PRODUCTION_CRITICAL_ITEM", "SAFETY_CRITICAL_ITEM",
    "SAFETY_CRITICAL_ITEM_GROUP", "SAFETY_CRITICAL_ITEM_REASON_AWARDED",
    "TAG_DESCRIPTION", "ACTION_STATUS", "ACTION_DATE",
]
```

## Audit
Export flow writes to `audit_core.sync_run_stats`:
- `target_table = 'project_core.tag'`
- `count_unchanged` = row count exported
