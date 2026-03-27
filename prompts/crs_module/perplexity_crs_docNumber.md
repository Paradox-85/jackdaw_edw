<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# давай также выполним следующее, для некоторых detailed файлов у меня есть ошибки в кторых участвует DOCUMENT_NUMBER - но здесь это не номер CRS документа (который мы ранее исключали), а именно ссылка на документ, которая указывает что Tag присутсвует в документе. Для части detailed files это применимо, где это поле явно указано. вот пример состава полей где есть явная ссылка на документ:

Sr. No.
DOCUMENT_NUMBER
PLANT_CODE
TAG_NAME
Issue
-> нужно добавить поле в схему БД (расширить схему
-> нужно добавить поиск колонки DOCUMENT_NUMBER при обработке и включить ее в условие уникальности при проверке hash значения
-> если поля нет на конкретном листе, просто указываем Not Applicable - так как это не применимо (логика полностью аналогична той, что мы применяли при анализе PROPERTY NAME)

Три изменения: схема БД, скрипт парсинга, скрипт загрузки.

***

## 1. migration_014 — добавить колонку `document_number`

```sql
-- =============================================================================
-- migration_014_crs_add_document_number.sql
--
-- Purpose:
--   Add document_number column to audit_core.crs_comment.
--   This field represents a reference to a project document that contains
--   the tag (from detail sheet DOCUMENT_NUMBER column).
--   NOT the CRS file itself (that is crs_doc_number).
--   NULL / 'Not Applicable' when not present in the detail sheet.
--
-- Changes:
--   2026-03-27 — Initial implementation.
-- =============================================================================

BEGIN;

ALTER TABLE "audit_core"."crs_comment"
    ADD COLUMN IF NOT EXISTS "document_number" TEXT NULL;

-- Place it after property_name for logical grouping
COMMENT ON COLUMN "audit_core"."crs_comment"."document_number" IS
    'Reference to a project document containing the tag (from DOCUMENT_NUMBER '
    'column in detail sheet). Not Applicable when column absent in source file. '
    'NOT the CRS file number — that is crs_doc_number.';

CREATE INDEX IF NOT EXISTS "idx_crs_comment_document_number"
    ON "audit_core"."crs_comment"("document_number")
    WHERE "document_number" IS NOT NULL
      AND "document_number" != 'Not Applicable';

COMMIT;
```


***

## 2. Скрипт — три места

### `process_key()` — добавить поиск `doc_num_col` и извлечение значения

Логика полностью аналогична `prop_col` — нормализованное сравнение, `Not Applicable` если колонки нет:

```python
            # Определить колонки один раз на лист — до цикла по строкам
            tag_col, is_equip_col = _find_tag_col(list(df_sheet.columns))

            prop_col = next(
                (c for c in df_sheet.columns
                 if any(
                     kw.replace(" ", "_") in c.lower().replace(" ", "_")
                     for kw in PROPERTY_COL_KEYWORDS
                 )),
                None,
            )

            # НОВОЕ — поиск колонки DOCUMENT_NUMBER:
            doc_num_col = next(
                (c for c in df_sheet.columns
                 if any(
                     kw.replace(" ", "_") in c.lower().replace(" ", "_")
                     for kw in DOCUMENT_NUMBER_KEYWORDS
                 )),
                None,
            )

            for _, d_row in df_sheet.iterrows():
                raw_tag  = _scalar(d_row[tag_col]) if tag_col else None
                tag_name = (
                    _extract_tag_from_equipment(raw_tag)
                    if is_equip_col
                    else clean_string(raw_tag)
                )

                prop_name = _scalar(d_row[prop_col]) if prop_col else None
                if not prop_name or str(prop_name).strip() == "":
                    prop_name = "Not Applicable"

                # НОВОЕ:
                doc_number_ref = _scalar(d_row[doc_num_col]) if doc_num_col else None
                if not doc_number_ref or str(doc_number_ref).strip() == "":
                    doc_number_ref = "Not Applicable"

                row_comment = comment_val
                if row_comment is None and fallback_col and fallback_col in d_row.index:
                    row_comment = _scalar(d_row[fallback_col]) or None

                records.append({
                    "DOC_NUMBER":         metadata.get("DOC_NUMBER"),
                    "REVISION":           metadata.get("REVISION"),
                    "RETURN_CODE":        metadata.get("RETURN_CODE"),
                    "TRANSMITTAL_NUMBER": metadata.get("TRANSMITTAL_NUMBER"),
                    "TRANSMITTAL_DATE":   metadata.get("TRANSMITTAL_DATE"),
                    "TAG_NAME":           tag_name,
                    "PROPERTY_NAME":      prop_name,
                    "DOCUMENT_NUMBER_REF": doc_number_ref,   # ← новое
                    "GROUP_COMMENT":      comment_text,
                    "RESPONSE":           response_text,
                    "SOURCE_FILE":        metadata.get("SOURCE_FILE"),
                    "DETAIL_FILE":        detail_path.name,
                    "DETAIL_SHEET":       sheet_key,
                    "COMMENT":            row_comment,
                    "CRS_FILE_PATH":      metadata.get("CRS_FILE_PATH"),
                })
```

Блок `not found_detail` — тоже добавить поле:

```python
        if not found_detail:
            records.append({
                ...
                "DOCUMENT_NUMBER_REF": "Not Applicable",   # ← добавить
                ...
            })
```


### Добавить константу `DOCUMENT_NUMBER_KEYWORDS` рядом с `PROPERTY_COL_KEYWORDS`:

```python
PROPERTY_COL_KEYWORDS = (
    "equipment property name",
    "equipment_property_name",
    "tag property name",
    "tag_property_name",
    "property name",
    "property_name",
)

# НОВОЕ:
DOCUMENT_NUMBER_KEYWORDS = (
    "document number",
    "document_number",
    "doc number",
    "doc_number",
    "doc no",
    "doc_no",
)
```

> **Важно:** имя ключа в raw dict — `DOCUMENT_NUMBER_REF`, а не `DOCUMENT_NUMBER`, чтобы не конфликтовать с `DOC_NUMBER` (CRS-документ из header).

### `prepare_crs_records()` — добавить поле в hash и db_record

```python
        # После property_name:
        document_number_ref = clean_string(rec.get("DOCUMENT_NUMBER_REF")) or "Not Applicable"

        # В hash_source — добавить:
        hash_source = {
            "crs_doc_number":     crs_doc_number,
            "tag_name":           tag_name or "",
            "revision":           revision or "",
            "return_code":        return_code or "",
            "transmittal_num":    transmittal_num or "",
            "transmittal_date":   str(transmittal_date) if transmittal_date else "",
            "group_comment":      group_comment,
            "comment":            comment,
            "property_name":      property_name or "",
            "document_number_ref": document_number_ref,   # ← новое
            "response_vendor":    response_vendor or "",
            "source_file":        source_file,
            "detail_file":        detail_file or "",
            "detail_sheet":       detail_sheet or "",
            "crs_file_path":      crs_file_path,
        }

        # В comment_id UUID5 — добавить в ключ:
        doc_num_key = (
            document_number_ref
            if document_number_ref and document_number_ref.upper() != "NOT APPLICABLE"
            else ""
        )
        comment_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{crs_doc_number}|{group_comment}|{detail_sheet or ''}|{tag_name or ''}|{comment}|{prop_key}|{doc_num_key}",
        ))

        # В db_records.append() — добавить поле:
        db_records.append({
            ...
            "property_name":      property_name,
            "document_number":    document_number_ref,   # ← новое, маппинг к имени колонки БД
            ...
        })
```


### `upsert_crs_records()` — обновить SQL

```python
    upsert_sql = text("""
        INSERT INTO audit_core.crs_comment (
            comment_id, crs_doc_number, revision, return_code,
            transmittal_number, transmittal_date,
            group_comment, comment, tag_name, tag_id, property_name,
            document_number,                          -- ← новое
            response_vendor, source_file, detail_file, detail_sheet,
            crs_file_path, crs_file_timestamp,
            status, object_status, row_hash, sync_timestamp
        ) VALUES (
            :comment_id, :crs_doc_number, :revision, :return_code,
            :transmittal_number, :transmittal_date,
            :group_comment, :comment, :tag_name, :tag_id, :property_name,
            :document_number,                         -- ← новое
            :response_vendor, :source_file, :detail_file, :detail_sheet,
            :crs_file_path, :crs_file_timestamp,
            :status, :object_status, :row_hash, now()
        )
        ON CONFLICT (comment_id) DO UPDATE SET
            group_comment      = EXCLUDED.group_comment,
            comment            = EXCLUDED.comment,
            tag_name           = EXCLUDED.tag_name,
            tag_id             = EXCLUDED.tag_id,
            property_name      = EXCLUDED.property_name,
            document_number    = EXCLUDED.document_number,   -- ← новое
            response_vendor    = EXCLUDED.response_vendor,
            crs_file_timestamp = EXCLUDED.crs_file_timestamp,
            row_hash           = EXCLUDED.row_hash,
            sync_timestamp     = now()
        WHERE audit_core.crs_comment.row_hash != EXCLUDED.row_hash
        RETURNING id, xmax
    """)
```


***

## Порядок применения

```bash
# 1. Миграция БД
psql -U edw_user -d jackdaw_edw -f sql/schema/migration_014_crs_add_document_number.sql

# 2. Проверить колонку
psql -U edw_user -d jackdaw_edw -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'audit_core'
  AND table_name = 'crs_comment'
  AND column_name = 'document_number';"

# 3. TRUNCATE + повторный импорт (comment_id изменился — новое поле в UUID5)
TRUNCATE audit_core.crs_comment, audit_core.crs_comment_audit RESTART IDENTITY CASCADE;
python scripts/import_crs_data.py --debug
```

