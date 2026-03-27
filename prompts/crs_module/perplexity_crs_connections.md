<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Инструкции для Claude Code

### Контекст

В `import_crs_data.py` обрабатываются CRS detail-файлы. Появился новый тип листа с колонками `FROM_TAG` / `TO_TAG` (трубопроводные/кабельные связи между тегами). Нужно расширить схему БД и скрипт импорта.

***

### Шаг 1 — Создать миграцию БД

**`@sql/schema/migration_015_crs_add_from_to_tag.sql`** — создать новый файл:

```sql
-- =============================================================================
-- migration_015_crs_add_from_to_tag.sql
--
-- Purpose:
--   Add from_tag / to_tag columns to audit_core.crs_comment.
--   These fields represent directional tag relationships found in specific
--   CRS detail sheets (e.g. pipeline / cable routing comments).
--   Both columns are NULL when the detail sheet does not contain FROM_TAG/TO_TAG.
--   In these cases tag_name remains the primary tag identifier.
--
-- Applies after: migration_014_crs_add_document_number.sql
-- =============================================================================

BEGIN;

ALTER TABLE "audit_core"."crs_comment"
    ADD COLUMN IF NOT EXISTS "from_tag" TEXT NULL,
    ADD COLUMN IF NOT EXISTS "to_tag"   TEXT NULL;

COMMENT ON COLUMN "audit_core"."crs_comment"."from_tag" IS
    'Source tag in a directional tag pair (FROM_TAG column in detail sheet). '
    'NULL when not applicable to this record type.';

COMMENT ON COLUMN "audit_core"."crs_comment"."to_tag" IS
    'Destination tag in a directional tag pair (TO_TAG column in detail sheet). '
    'NULL when not applicable to this record type.';

CREATE INDEX IF NOT EXISTS "idx_crs_comment_from_tag"
    ON "audit_core"."crs_comment"("from_tag")
    WHERE "from_tag" IS NOT NULL;

CREATE INDEX IF NOT EXISTS "idx_crs_comment_to_tag"
    ON "audit_core"."crs_comment"("to_tag")
    WHERE "to_tag" IS NOT NULL;

COMMIT;
```


***

### Шаг 2 — Обновить скрипт импорта

**`@scripts/import_crs_data.py`** — внести следующие изменения:

#### 2.1 Добавить константы `FROM_TAG_KEYWORDS` / `TO_TAG_KEYWORDS` после `DOCUMENT_NUMBER_KEYWORDS`

```python
FROM_TAG_KEYWORDS: tuple[str, ...] = (
    "from tag",
    "from_tag",
    "from tag name",
    "from_tag_name",
)

TO_TAG_KEYWORDS: tuple[str, ...] = (
    "to tag",
    "to_tag",
    "to tag name",
    "to_tag_name",
)
```


#### 2.2 В `process_key()` — добавить поиск колонок `from_tag_col` / `to_tag_col` в блоке определения колонок (после `doc_num_col`)

```python
            # FROM_TAG / TO_TAG — present only in directional detail sheets
            from_tag_col = next(
                (c for c in df_sheet.columns
                 if any(
                     kw.replace(" ", "_") in c.lower().replace(" ", "_")
                     for kw in FROM_TAG_KEYWORDS
                 )),
                None,
            )
            to_tag_col = next(
                (c for c in df_sheet.columns
                 if any(
                     kw.replace(" ", "_") in c.lower().replace(" ", "_")
                     for kw in TO_TAG_KEYWORDS
                 )),
                None,
            )
```


#### 2.3 В `process_key()` — извлечь значения в цикле по строкам (после `doc_number_ref`)

```python
                from_tag = clean_string(_scalar(d_row[from_tag_col])) if from_tag_col else None
                to_tag   = clean_string(_scalar(d_row[to_tag_col]))   if to_tag_col   else None
```


#### 2.4 В `process_key()` — добавить поля в `records.append({...})`

```python
                    "FROM_TAG":            from_tag,
                    "TO_TAG":              to_tag,
```


#### 2.5 В `process_key()` — добавить поля в блок `not found_detail`

```python
                "FROM_TAG":            None,
                "TO_TAG":              None,
```


#### 2.6 В `process_key()` — добавить `from_tag` и `to_tag` в `_cid` для дедупликации

```python
                _cid = (
                    f"{metadata.get('DOC_NUMBER', '')}|{comment_text}|{sheet_key}"
                    f"|{tag_name or ''}|{row_comment or ''}|{prop_key_chk}|{doc_num_chk}"
                    f"|{from_tag or ''}|{to_tag or ''}"
                )
```


#### 2.7 В `prepare_crs_records()` — добавить извлечение полей (после `document_number_ref`)

```python
        from_tag            = clean_string(rec.get("FROM_TAG"))
        to_tag              = clean_string(rec.get("TO_TAG"))
```


#### 2.8 В `prepare_crs_records()` — добавить в `hash_source`

```python
            "from_tag":           from_tag or "",
            "to_tag":             to_tag or "",
```


#### 2.9 В `prepare_crs_records()` — добавить в `comment_id` UUID5 строку

```python
        comment_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{crs_doc_number}|{group_comment}|{detail_sheet or ''}"
            f"|{tag_name or ''}|{comment}|{prop_key}|{doc_num_key}"
            f"|{from_tag or ''}|{to_tag or ''}",
        ))
```


#### 2.10 В `prepare_crs_records()` — добавить поля в `db_records.append({...})`

```python
            "from_tag":           from_tag,
            "to_tag":             to_tag,
```


#### 2.11 В `upsert_crs_records()` — обновить SQL INSERT (список колонок и VALUES)

В секции колонок после `document_number` добавить:

```sql
            from_tag, to_tag,
```

В секции VALUES после `:document_number` добавить:

```sql
            :from_tag, :to_tag,
```

В секции `ON CONFLICT DO UPDATE SET` после `document_number = EXCLUDED.document_number` добавить:

```sql
            from_tag           = EXCLUDED.from_tag,
            to_tag             = EXCLUDED.to_tag,
```


***

### Шаг 3 — Применить миграцию

```bash
psql -U edw_user -d jackdaw_edw \
  -f sql/schema/migration_015_crs_add_from_to_tag.sql

# Проверить:
psql -U edw_user -d jackdaw_edw -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'audit_core'
  AND table_name = 'crs_comment'
  AND column_name IN ('from_tag', 'to_tag');"
```


### Шаг 4 — Повторный импорт

Поскольку `comment_id` (UUID5) изменился — добавлены `from_tag`/`to_tag` в ключ:

```bash
# TRUNCATE существующих данных перед повторным импортом
psql -U edw_user -d jackdaw_edw -c "
TRUNCATE audit_core.crs_comment, audit_core.crs_comment_audit
RESTART IDENTITY CASCADE;"

python scripts/import_crs_data.py --debug
# После проверки — полный прогон:
python scripts/import_crs_data.py
```

