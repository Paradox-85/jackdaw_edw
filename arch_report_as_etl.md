# Jackdaw EIS — Report-as-ETL
## Architecture Decision Record: Reverse ETL / EIS CSV Snapshot Export

---

## 1. Концепция

Экспорт EIS CSV-файлов реализован по той же архитектурной модели, что и импорт данных — как Prefect Flow с чётко разделёнными слоями Extract / Transform / Load. Единственное отличие от импорта — направление потока данных.

**Ключевой принцип:** логика отчёта живёт в коде (Git), а не в настройках BI-инструмента. Это означает воспроизводимость, версионность и возможность code review для каждого изменения в выгрузке.

| Dimension | ETL Import | Reverse ETL Export |
|---|---|---|
| Direction | Source → Database | Database → Files (CSV/XML) |
| Trigger | New/changed source file | Manual run или schedule via Prefect |
| Transform | Normalize, resolve FK, hash | Filter, join, reshape, clean encoding |
| Load | UPSERT with row_hash CDC | `write_csv()` / `write_xml()` / `write_xlsx()` |
| Gate | `object_status = 'Active'` on write | `object_status = 'Active'` in SELECT |
| Audit | `audit_core.sync_run_stats` | `audit_core.sync_run_stats` (та же таблица) |
| Orchestrator | `flows/main_sync.py` | `flows/export_eis_snapshot.py` |

---

## 2. Архитектура flow

### 2.1 Файловая структура

```
scripts/
├── flows/
│   ├── main_sync.py                  # ETL import orchestrator
│   └── export_eis_snapshot.py        # Reverse ETL export orchestrator  ← NEW
├── tasks/
│   ├── common.py                     # shared helpers
│   └── export_transforms.py          # transform + sanitize + write_csv  ← NEW
└── config/
    └── db_config.yaml                # добавлен ключ storage.export_dir
```

### 2.2 Точка входа (параметры flow)

```python
export_eis_snapshot(
    doc_revision : str       = "A35",   # встраивается в каждое имя файла
    output_dir   : str       = _OUT_DIR, # из config: storage.export_dir
    reports      : list[str] = None,     # None = все 17; subset для переиздания
)
```

Пример частичного переиздания:

```python
export_eis_snapshot(doc_revision="A36", reports=["tag_register", "doc_ref_tag"])
```

### 2.3 Слои обработки

| Layer | Location | Responsibility |
|---|---|---|
| SQL Query | `flows/export_eis_snapshot.py` | Extract + first-level filter. `WHERE object_status='Active'` / `mapping_status='Active'`. JOINs across project_core, reference_core, ontology_core. |
| Domain Transform | `tasks/export_transforms.py` | Business rules per report type. `transform_tag_register()`: Deleted exclusion, column renames, date format. Future: T1 TAG_STATUS filter, T3 UoM normalisation. |
| Sanitize Gate | `export_transforms.sanitize_dataframe()` | Вызывается unconditionally внутри `write_csv()`. Применяет `clean_engineering_text()` к КАЖДОЙ str-колонке. Ни один CSV не может обойти этот слой. |
| Write | `export_transforms.write_csv()` | UTF-8 BOM (`utf-8-sig`) для совместимости с Excel/EIS. Возвращает row count для audit log. |

### 2.4 Конвенция имён выходных файлов

```
JDAW-KVE-E-JA-6944-00001-{seq:03d}-{doc_revision}.CSV

Пример: JDAW-KVE-E-JA-6944-00001-003-A35.CSV
```

- `seq` — трёхзначный порядковый номер из `EXPORT_MANIFEST` (001–024)
- `doc_revision` — параметр flow, например `A35`

---

## 3. Контракт фильтрации

> **Правило:** фильтрация выполняется на уровне SQL-запроса, а не в Pandas после загрузки. PostgreSQL использует индексы на `object_status` и `mapping_status`, что исключает full scan таблиц.

| Rule | Scope | Condition | Rationale |
|---|---|---|---|
| Entity tables | `project_core`, `reference_core`, `ontology_core` | `WHERE object_status = 'Active'` | Indexed. Fast scan. |
| Mapping tables | `mapping.*` | `WHERE mapping_status = 'Active'` | Indexed. Replaces join-time sync_status check. |
| **NEVER use** | all tables | `sync_status` (в контексте экспорта) | ETL control field only. Not a visibility gate. |
| Business filter | `document` (все запросы) | `AND d.status != 'CAN'` | EIS rule: cancelled documents excluded. |

### Атомарная связь `object_status` ↔ `sync_status`

В задаче `sync_tag_data.py` "Final Cleanup" UPDATE выполняется в одной транзакции:

```sql
UPDATE project_core.tag
   SET sync_status   = 'Deleted',
       object_status = 'Inactive'    -- атомарно с sync_status
WHERE sync_timestamp < :run_start
  AND sync_status   != 'Deleted'
```

Благодаря этому `WHERE object_status = 'Active'` является полным эквивалентом "не удалён" и всегда актуален.

---

## 4. Паттерны SQL-запросов

### 4.1 Простая выгрузка сущности (areas, process_units)

```sql
SELECT a.code  AS AREA_CODE,
       a.name  AS AREA_NAME,
       p.code  AS PLANT_CODE
FROM   reference_core.area  a
LEFT JOIN reference_core.plant p ON p.id = a.plant_id
WHERE  a.object_status = 'Active'
ORDER BY a.code
```

### 4.2 Выгрузка с маппингом (doc_ref_tag)

```sql
SELECT t.tag_name, d.doc_number, d.title, d.status
FROM   mapping.tag_document   td
JOIN   project_core.tag        t  ON t.id  = td.tag_id
JOIN   project_core.document   d  ON d.id  = td.document_id
WHERE  td.mapping_status = 'Active'   -- mapping gate
  AND  t.object_status   = 'Active'   -- entity gate
  AND  d.object_status   = 'Active'   -- entity gate
  AND  d.status         != 'CAN'      -- business rule
```

### 4.3 Реестр тегов (tag_register) — многоуровневый JOIN

```sql
SELECT pl.code, t.tag_name, COALESCE(pt.tag_name, '') AS PARENT_TAG_NAME,
       a.code, u.code, c.name, t.tag_status, ...
FROM   project_core.tag t
LEFT JOIN reference_core.plant        pl ON pl.id = t.plant_id
LEFT JOIN project_core.tag            pt ON pt.id = t.parent_tag_id  -- self-join для иерархии
LEFT JOIN reference_core.area         a  ON a.id  = t.area_id
LEFT JOIN ontology_core.class         c  ON c.id  = t.class_id
-- ... остальные LEFT JOIN
WHERE  t.object_status = 'Active'
```

> `LEFT JOIN` для всех справочных таблиц — тег не должен пропасть из выгрузки из-за NULL FK.

---

## 5. Трансформации по типам отчётов

| Seq | Key | Transform fn | Rules applied |
|---|---|---|---|
| 003 | `tag_register` | `transform_tag_register()` | Deleted exclusion (2nd level), `sync_status`→`ACTION_STATUS`, `sync_timestamp`→`ACTION_CHANGED` (date only), `PARENT_TAG_NAME` unset→`""` |
| 010 | `tag_property_values` | `_identity()` + T3 pending | T3: N/A→NA, YES→Yes, unit strip (volt/kW/degC…), comma→dot для numeric UoM |
| 011 | `equipment_property_values` | `_identity()` + T3 pending | Те же правила T3 что и 010 |
| 016 | `doc_ref_tag` | `_identity()` + T1 pending | T1: TAG_STATUS NOT IN (VOID, Future, empty), DOCUMENT_STATUS != CAN, MDR=True |
| all | все отчёты | `write_csv()` → `sanitize_dataframe()` | `clean_engineering_text()` на ALL string columns. UTF-8 BOM. Mandatory, cannot be bypassed. |

### Реализованные трансформации — tag_register (003)

- **Primary gate:** `WHERE object_status = 'Active'` в SQL
- **Second level defence:** `df[df['sync_status'] != 'Deleted']` в `transform_tag_register()`
- `sync_status` → `ACTION_STATUS`
- `sync_timestamp` → `ACTION_CHANGED`, формат `YYYY-MM-DD` (только дата)
- `PARENT_TAG_NAME`: литерал `'unset'` → пустая строка
- Колонка `id` (внутренний UUID) удаляется из выгрузки

### Universal text sanitizer — применяется ко ВСЕМ отчётам

- `sanitize_dataframe(df)` перебирает все колонки через `pd.api.types.is_string_dtype()`
- Совместимо с pandas 2.x `StringDtype` и классическим `object` dtype
- Float / int / datetime-колонки не затрагиваются
- `clean_engineering_text()` — 12-шаговый pipeline: Â-пары, 3-байтные UTF-8 sequences, Win-1252 leaked bytes, NBSP, схлопывание пробелов
- **Гарантия:** `write_csv()` вызывает `sanitize_dataframe()` unconditionally — ни один CSV не может обойти санитайзер

#### Encoding corruption inventory (source: 1927 TAG_DESCRIPTION rows)

| Count | Pattern | Rule |
|---|---|---|
| 1198 | `Â` (U+00C2) | First byte of 2-byte UTF-8 pair, always paired |
| 1183 | `²` (U+00B2) | `Â²` → `2` |
| 708 | double space | collapse to single |
| 40 | `â` (U+00E2) | First byte of 3-byte UTF-8 seq |
| 23 | NBSP (`\xA0`) | `Â\xA0` UTF-8 pair → space |
| 23 | `\x93` / `\x9D` | Windows-1252 smart quotes → `"` |

---

## 6. Манифест отчётов (17 файлов)

Seq gaps: 007, 008, 012–015, 021 отсутствуют. Файл **008 (Purchase Orders) исключён из scope явно**.

| Seq | Key | Source xlsx | Mapping tables |
|---|---|---|---|
| 001 | `areas` | 203-Area | — |
| 002 | `process_units` | 204-ProcessUnit | — |
| 003 | `tag_register` | 205-Tag-register | — |
| 004 | `equipment_register` | 206-Equipment-register | — |
| 005 | `model_parts` | 209-Model-Part-register | — |
| 006 | `tag_connections` | 212-Tag Physical Connection | `mapping.tag_connection` ⚠ |
| 009 | `tag_class_properties` | 307-Tag-class-properties | `ontology_core.class_property` |
| 010 | `tag_property_values` | 303-Tag-property-value | — |
| 011 | `equipment_property_values` | 301-Equipment-property-value | — |
| 016 | `doc_ref_tag` | 412-Document_References_to_Tag | `mapping.tag_document` |
| 017 | `doc_ref_area` | 411-Document_References_to_Area | `mapping.document_area` ⚠ |
| 018 | `doc_ref_process_unit` | 410-Document_References_to_ProcessUnit | `mapping.document_process_unit` ⚠ |
| 019 | `doc_ref_equipment` | 413-Document_References_to_Equipment | `mapping.tag_document` (concept filter) |
| 020 | `doc_ref_model_part` | 414-Document_References_to_ModelPart | `mapping.document_model_part` ⚠ |
| 022 | `doc_ref_purchase_order` | 420-Document_References_to_PurchaseOrder | `mapping.document_po` |
| 023 | `doc_ref_plant` | 409-Document_References_to_PlantCode | — |
| 024 | `doc_ref_site` | 408-Document_References_to_Site | — |

> ⚠ — таблица маппинга требует проверки существования в схеме перед запуском экспорта.

---

## 7. Открытые вопросы

| Item | Priority | Files | Notes |
|---|---|---|---|
| Mapping tables 017–020 | **HIGH** | 017–020 | Подтвердить существование `mapping.document_area`, `document_process_unit`, `document_model_part`. Если нет — ALTER TABLE + ETL task. |
| `tag_connections` (006) | **HIGH** | 006 | Подтвердить `mapping.tag_connection`. Если нет — schema + ETL task из поля TAG_CONNECTION в MTR. |
| T1 row filter | MEDIUM | 003, 016 | `TAG_STATUS NOT IN ('VOID', 'Future', '')`, `DOCUMENT_STATUS != 'CAN'`, doc prefix whitelist (`JDAW*`, `JA*`…), `MDR = True` |
| T3 value normalisation | MEDIUM | 010, 011 | `N/A`→`NA`, `YES`→`Yes`, `NO`→`No`, `999999`→`NA`, unit strip (volt→V, degC→°C, kW, kg, Hz…), comma→dot для numeric UoM |
| `doc_revision` validation | LOW | flow param | Добавить `re.match(r'[A-Z]\d{2}', doc_revision)` в точку входа flow |
| `ACTION_STATUS` scope | LOW | 003 | Уточнить: выгружать все статусы (New/Updated/No Changes) или только изменённые в текущем цикле? |
| `PLANT_CODE` scope | LOW | 003, 004 | Уточнить: только `JDA` или также `SWA` и другие? Добавить параметр `plant_code` в flow. |

---

## 8. Стандарты кодирования (export модуль)

### Python

- Фильтры — только в SQL (`WHERE object_status` / `mapping_status`). Не в Pandas.
- `pd.read_sql` — `dtype=str` не нужен (SQL возвращает типизированные данные).
- `pd.api.types.is_string_dtype()` — вместо `dtype == object` для pandas 2.x совместимости.
- `engine.connect()` без `begin()` — транзакции не нужны для SELECT-only задач экспорта.

### SQL

- Всегда префикс схемы: `project_core.tag`, не просто `tag`.
- `LEFT JOIN` для опциональных связей — тег не должен пропасть из выгрузки из-за NULL FK.
- `COALESCE(pt.tag_name, '')` — для `PARENT_TAG_NAME`: NULL → пустая строка в выгрузке.
- `ORDER BY` обязателен во всех отчётах — стабильный порядок строк для diff-сравнения между ревизиями.

### Расширение на новые форматы

Для XML и Excel добавить `write_xml()` и `write_xlsx()` по аналогии с `write_csv()` — с аналогичным вызовом `sanitize_dataframe()` перед записью. Логика SQL-запросов и трансформаций остаётся идентичной.
