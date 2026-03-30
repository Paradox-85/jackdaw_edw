# CRS Comment Categories v2.0 — Каталог типовых замечаний с SQL-запросами

> **Источники:** `master_comments_list.xlsx` (1207 записей), `schema.sql` (project knowledge, ветка main)  
> **Версия:** 2.0 — исправлены технические ошибки v1.0, добавлены категории C41–C50  
> **Цель:** Каждой категории — типовой SQL-запрос для проверки исполнимости требования в Jackdaw EDW

---

## Сводная таблица категорий

| query_code | Категория | EIS-файл | Объект БД | mapping_presence | Приоритет |
|---|---|---|---|---|---|
| CRS-C01 | Пустые обязательные поля (общее) | 001/003/004 | `project_core.tag` | Mandatory | 🔴 Critical |
| CRS-C02 | Отсутствует TAG_DESCRIPTION | 003 | `tag.description` | Mandatory | 🔴 Critical |
| CRS-C03 | TAG_DESCRIPTION > 255 символов | 003 | `tag.description` | Mandatory | 🟡 Warning |
| CRS-C04 | TAG_CLASS не в ISM (RDL) | 003 | `ontology_core.class` | Mandatory | 🔴 Critical |
| CRS-C05 | TNC — Tag Naming Convention | 003/004 | `tag.tag_name` | Mandatory | 🔴 Critical |
| CRS-C06 | AREA_CODE пустой | 003 | `tag.area_id` | Recommended | 🟡 Warning |
| CRS-C07 | AREA_CODE невалидный / "NA" | 001/003 | `reference_core.area` | Mandatory | 🔴 Critical |
| CRS-C08 | PROCESS_UNIT_CODE отсутствует | 003 | `tag.process_unit_id` | Mandatory | 🔴 Critical |
| CRS-C09 | PROCESS_UNIT_CODE не в регистре | 003/018 | `reference_core.process_unit` | Mandatory | 🔴 Critical |
| CRS-C10 | PARENT_TAG отсутствует | 003 | `tag.parent_tag_id` | Recommended | 🟡 Warning |
| CRS-C11 | PARENT_TAG не в MTR | 003 | `tag` (self-join) | Mandatory | 🔴 Critical |
| CRS-C12 | PARENT_TAG — pipe-to-pipe | 003 | `tag` + `ontology_core.class` | Recommended | 🟡 Warning |
| CRS-C13 | SAFETY_CRITICAL_ITEM пустой | 003 | `tag.safety_critical_item` | Mandatory | 🔴 Critical |
| CRS-C14 | SAFETY_CRITICAL_REASON пустой у SECE | 003 | `tag.safety_critical_item_reason_awarded` | Mandatory | 🔴 Critical |
| CRS-C15 | PRODUCTION_CRITICAL_ITEM пустой | 003 | `tag.production_critical_item` | Mandatory | 🔴 Critical |
| CRS-C16 | Дубликаты тегов | 003 | `tag.tag_name` | Mandatory | 🔴 Critical |
| CRS-C17 | Tag Property — тег не в MTR | 010 | `property_value.tag_id` | Mandatory | 🔴 Critical |
| CRS-C18 | PROPERTY_VALUE = "NA" при непустом UOM | 010/011 | `property_value` | Mandatory | 🟡 Warning |
| CRS-C19 | PROPERTY_VALUE = "0" | 010/011 | `property_value` | Optional | 🟡 Warning |
| CRS-C20 | Property class mapping не совпадает | 010 | `property_value` + `class_property` | Mandatory | 🔴 Critical |
| CRS-C21 | Тег без properties в Property CSV | 010 | `tag` vs `property_value` | Recommended | 🟡 Warning |
| CRS-C22 | Обязательные ISM properties не поданы | 010/011 | `class_property.mapping_presence` | Mandatory | 🔴 Critical |
| CRS-C23 | EQUIPMENT_CLASS не в RDL | 004 | `ontology_core.class` | Mandatory | 🔴 Critical |
| CRS-C24 | EQUIPMENT_DESCRIPTION пустая | 004 | `tag.description` | Mandatory | 🔴 Critical |
| CRS-C25 | MANUFACTURER_SERIAL_NUMBER пустой | 004 | `tag.serial_no` | Mandatory | 🔴 Critical |
| CRS-C26 | MODEL_PART_NAME пустой | 004 | `tag.model_id` | Mandatory | 🟡 Warning |
| CRS-C27 | MFG_COMPANY не заполнен | 004 | `tag.manufacturer_id` | Recommended | 🟡 Warning |
| CRS-C28 | Equipment — TAG_NAME не в MTR | 004 | `tag.equip_no` | Mandatory | 🔴 Critical |
| CRS-C29 | PLANT_CODE невалидный | 003/004 | `reference_core.plant` | Mandatory | 🔴 Critical |
| CRS-C30 | Документ не в DocMaster / NYI | 014/016 | `project_core.document` | Mandatory | 🔴 Critical |
| CRS-C31 | Тег без документной ссылки | 016 | `mapping.tag_document` | Recommended | 🟡 Warning |
| CRS-C32 | Doc в Tag-Doc, нет в DocMaster | 016 | `document` vs `tag_document` | Mandatory | 🔴 Critical |
| CRS-C33 | Тег в Tag-Doc, нет в MTR | 016 | `tag` vs `tag_document` | Mandatory | 🔴 Critical |
| CRS-C34 | Doc-Area: AREA_CODE отсутствует | 017 | `tag_document` → `tag.area_id` | Recommended | 🟡 Warning |
| CRS-C35 | Doc-PU: PROCESS_UNIT_CODE отсутствует | 018 | `tag_document` → `tag.process_unit_id` | Recommended | 🟡 Warning |
| CRS-C36 | PO_CODE не в PO Register | 008/022 | `reference_core.purchase_order` | Mandatory | 🔴 Critical |
| CRS-C37 | PO_DATE отсутствует | 008 | `purchase_order.po_date` | Mandatory | 🔴 Critical |
| CRS-C38 | COMPANY_NAME отсутствует / невалиден | 007/022 | `reference_core.company` | Recommended | 🟡 Warning |
| CRS-C39 | Дубликаты в Physical Connection | 006 | `tag.from_tag_raw` / `to_tag_raw` | Mandatory | 🔴 Critical |
| CRS-C40 | Equipment нет в Doc-Equipment | 019 | `tag.equip_no` vs `tag_document` | Recommended | 🟡 Warning |
| CRS-C41 | EX_CLASS / IP_GRADE пустые | 003 | `tag.ex_class`, `tag.ip_grade` | Mandatory | 🔴 Critical |
| CRS-C42 | MC_PACKAGE_CODE не заполнен | 003 | `tag.mc_package_code` | Recommended | 🟡 Warning |
| CRS-C43 | ALIAS конфликтует с другим тегом | 003 | `tag.alias` | Recommended | 🟡 Warning |
| CRS-C44 | TECH_ID пустой у instrument-тегов | 003 | `tag.tech_id` | Recommended | 🟡 Warning |
| CRS-C45 | FROM_TAG / TO_TAG не в MTR | 006 | `tag.from_tag_raw` / `to_tag_raw` | Mandatory | 🔴 Critical |
| CRS-C46 | TAG_STATUS вне допустимого словаря | 003 | `tag.tag_status` | Mandatory | 🔴 Critical |
| CRS-C47 | SECE-тег без маппинга в tag_sece | 003 | `mapping.tag_sece` | Mandatory | 🔴 Critical |
| CRS-C48 | property_code_raw не в ontology | 010/011 | `property_value.property_id` | Mandatory | 🔴 Critical |
| CRS-C49 | Дубликат doc_number в Document | 014 | `project_core.document` | Mandatory | 🔴 Critical |
| CRS-C50 | Circular parent reference | 003 | `tag.parent_tag_id` (CTE) | Mandatory | 🔴 Critical |

---

## Детальное описание категорий и SQL-запросы

---

### CRS-C01 — Пустые обязательные поля (общее)

**Типовой текст:** *"Data missing, further update required. Cells should not be left blank"*

```sql
SELECT
    t.tag_name,
    t.plant_raw,
    CASE WHEN t.class_id IS NULL                                  THEN 'TAG_CLASS missing'       END AS issue_class,
    CASE WHEN t.description IS NULL OR t.description = ''         THEN 'DESCRIPTION missing'     END AS issue_desc,
    CASE WHEN t.process_unit_id IS NULL                           THEN 'PROCESS_UNIT missing'    END AS issue_pu,
    CASE WHEN t.safety_critical_item IS NULL
          OR TRIM(t.safety_critical_item) = ''                    THEN 'SAFETY_CRITICAL missing' END AS issue_sc
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (
      t.class_id IS NULL
      OR t.description IS NULL OR t.description = ''
      OR t.process_unit_id IS NULL
      OR t.safety_critical_item IS NULL OR TRIM(t.safety_critical_item) = ''
  )
ORDER BY t.tag_name;
```

---

### CRS-C02 — Отсутствует TAG_DESCRIPTION

**Типовой текст:** *"Tag Description is missing for listed N tags"*

```sql
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)   AS tag_class,
    COALESCE(pl.code, t.plant_raw)      AS plant_code
FROM project_core.tag t
LEFT JOIN ontology_core.class  c  ON c.id  = t.class_id
LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
WHERE t.object_status = 'Active'
  AND (t.description IS NULL OR TRIM(t.description) = '')
ORDER BY t.tag_name;
-- COUNT: SELECT COUNT(*) FROM project_core.tag WHERE object_status='Active' AND (description IS NULL OR TRIM(description)='');
```

---

### CRS-C03 — TAG_DESCRIPTION > 255 символов

**Типовой текст:** *"Tag Description is exceeding 255 characters. Kindly limit within 255 characters"*

```sql
SELECT
    t.tag_name,
    LENGTH(t.description)            AS desc_length,
    LEFT(t.description, 80) || '...' AS desc_preview
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.description IS NOT NULL
  AND LENGTH(t.description) > 255
ORDER BY desc_length DESC;
```

---

### CRS-C04 — TAG_CLASS не в ISM (RDL)

**Типовой текст:** *"Tag Classes are not per Shell ISM / Tag Class Not available in Tag Class ISM (Jackdaw Data Reference)"*

```sql
-- class_id IS NULL → raw значение не нашлось в ontology_core.class
SELECT
    t.tag_name,
    t.tag_class_raw   AS submitted_class,
    'NOT RESOLVED IN RDL' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.class_id IS NULL
  AND t.tag_class_raw IS NOT NULL AND t.tag_class_raw != ''
ORDER BY t.tag_class_raw, t.tag_name;

-- Обзор: уникальные нераспознанные классы с подсчётом тегов
SELECT t.tag_class_raw, COUNT(*) AS affected_tags
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.class_id IS NULL
  AND t.tag_class_raw IS NOT NULL AND t.tag_class_raw != ''
GROUP BY t.tag_class_raw
ORDER BY affected_tags DESC;
```

---

### CRS-C05 — TNC (Tag Naming Convention) нарушена

**Типовой текст:** *"Tag Naming does not confirm with Jackdaw Tagging Specification JDAW-PT-D-OA-7880-00001"*  
**⚠ Исправление v2.0:** Добавлен `LEFT JOIN ontology_core.class` в третий запрос.

```sql
-- 1. Тег не начинается с "JDA-"
SELECT tag_name, tag_class_raw, plant_raw
FROM project_core.tag
WHERE object_status = 'Active'
  AND tag_name NOT LIKE 'JDA-%'
ORDER BY tag_name;

-- 2. Запятая вместо точки в имени тега
SELECT tag_name, tag_class_raw
FROM project_core.tag
WHERE object_status = 'Active'
  AND tag_name ~ ',';

-- 3. Pipe-теги, оканчивающиеся на "-" (без инсуляционного кода)
--    ИСПРАВЛЕНО: добавлен LEFT JOIN ontology_core.class
SELECT t.tag_name, c.name AS tag_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id  -- ИСПРАВЛЕНО v2.0
WHERE t.object_status = 'Active'
  AND c.name ILIKE '%pipe%'
  AND t.tag_name LIKE '%-'
ORDER BY t.tag_name;
```

---

### CRS-C06 — AREA_CODE пустой

**Типовой текст:** *"For N Tags, Area Code is blank. Though not mandatory but it is good to have the data"*

```sql
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)     AS tag_class,
    COALESCE(pu.code, t.process_unit_raw) AS process_unit
FROM project_core.tag t
LEFT JOIN ontology_core.class         c  ON c.id  = t.class_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE t.object_status = 'Active'
  AND t.area_id IS NULL
ORDER BY t.tag_name;
-- COUNT: SELECT COUNT(*) FROM project_core.tag WHERE object_status='Active' AND area_id IS NULL;
```

---

### CRS-C07 — AREA_CODE невалидный / literal "NA" / дублирован в ячейке

**Типовой текст:** *"AREA_CODE is duplicated within the same cell" / "Area code is as 'NA'"*

```sql
-- area_code_raw подан, но FK не разрешился
SELECT
    t.tag_name,
    t.area_code_raw       AS submitted_area_code,
    'NOT IN AREA REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.area_code_raw IS NOT NULL AND t.area_code_raw != ''
  AND t.area_id IS NULL
ORDER BY t.area_code_raw;

-- Literal "NA" в area_code_raw
SELECT tag_name, area_code_raw
FROM project_core.tag
WHERE object_status = 'Active'
  AND UPPER(TRIM(area_code_raw)) = 'NA';
```

---

### CRS-C08 — PROCESS_UNIT_CODE отсутствует

**Типовой текст:** *"For N Tags listed, Process Unit Code is missing"*

```sql
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw) AS tag_class,
    COALESCE(pl.code, t.plant_raw)    AS plant_code
FROM project_core.tag t
LEFT JOIN ontology_core.class  c  ON c.id  = t.class_id
LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
WHERE t.object_status = 'Active'
  AND t.process_unit_id IS NULL
ORDER BY t.tag_name;
-- COUNT: SELECT COUNT(*) FROM project_core.tag WHERE object_status='Active' AND process_unit_id IS NULL;
```

---

### CRS-C09 — PROCESS_UNIT_CODE не в регистре / literal "NA"

**Типовой текст:** *"Process Unit Code is not matching/not available in Process Unit CSV"*

```sql
-- Raw подан, FK не разрешился
SELECT
    t.tag_name,
    t.process_unit_raw        AS submitted_pu_code,
    'NOT IN PROCESS_UNIT REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.process_unit_raw IS NOT NULL AND t.process_unit_raw != ''
  AND t.process_unit_id IS NULL
ORDER BY t.process_unit_raw;

-- Literal "NA"
SELECT tag_name, process_unit_raw
FROM project_core.tag
WHERE object_status = 'Active'
  AND UPPER(TRIM(process_unit_raw)) = 'NA';
```

---

### CRS-C10 — PARENT_TAG отсутствует у физических тегов

**Типовой текст:** *"Listed N tags with class like Valve, transmitter, pipe etc should preferably have parent tag"*

```sql
SELECT
    t.tag_name,
    c.name AS tag_class
FROM project_core.tag t
JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.parent_tag_id IS NULL
  AND t.parent_tag_raw IS NULL
  AND c.name ILIKE ANY (ARRAY['%valve%','%transmitter%','%pipe%','%pump%','%motor%','%sensor%'])
ORDER BY c.name, t.tag_name;
```

---

### CRS-C11 — PARENT_TAG не существует в MTR

**Типовой текст:** *"Parent tag itself is not part of Tag anywhere in tag register"*

```sql
-- parent_tag_raw заполнен, FK не разрешился
SELECT
    t.tag_name,
    t.parent_tag_raw     AS declared_parent,
    'PARENT NOT IN MTR'  AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.parent_tag_raw IS NOT NULL AND t.parent_tag_raw != ''
  AND t.parent_tag_id IS NULL
ORDER BY t.parent_tag_raw;

-- Топ нераспознанных parent-ссылок
SELECT parent_tag_raw, COUNT(*) AS affected_tags
FROM project_core.tag
WHERE object_status = 'Active'
  AND parent_tag_raw IS NOT NULL AND parent_tag_raw != ''
  AND parent_tag_id IS NULL
GROUP BY parent_tag_raw
ORDER BY affected_tags DESC;
```

---

### CRS-C12 — PARENT_TAG — pipe-to-pipe ссылка

**Типовой текст:** *"For listed N Pipe tags, parent tag is also pipe tag. Acceptable only for small bore pipe/nozzle"*

```sql
SELECT
    child.tag_name  AS child_tag,
    parent.tag_name AS parent_tag,
    cc.name         AS child_class,
    pc.name         AS parent_class
FROM project_core.tag child
JOIN project_core.tag  parent ON parent.id = child.parent_tag_id
JOIN ontology_core.class cc    ON cc.id    = child.class_id
JOIN ontology_core.class pc    ON pc.id    = parent.class_id
WHERE child.object_status  = 'Active'
  AND parent.object_status = 'Active'
  AND cc.name ILIKE '%pipe%'
  AND pc.name ILIKE '%pipe%'
ORDER BY child.tag_name;
```

---

### CRS-C13 — SAFETY_CRITICAL_ITEM пустое / невалидное значение

**Типовой текст:** *"Many tags missing yes or no for safety critical item" / "The Safety Critical Item field is currently blank"*

```sql
SELECT
    t.tag_name,
    t.safety_critical_item,
    COALESCE(c.name, t.tag_class_raw) AS tag_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND (
      t.safety_critical_item IS NULL
      OR TRIM(t.safety_critical_item) = ''
      OR UPPER(TRIM(t.safety_critical_item)) NOT IN ('YES','NO','Y','N')
  )
ORDER BY t.tag_name;
-- COUNT: SELECT COUNT(*) FROM project_core.tag WHERE object_status='Active' AND (safety_critical_item IS NULL OR TRIM(safety_critical_item)='');
```

---

### CRS-C14 — SAFETY_CRITICAL_ITEM_REASON_AWARDED пустой у SECE-тегов

**Типовой текст:** *"For listed N safety critical items, SAFETY_CRITICAL_ITEM_REASON_AWARDED is not provided"*

```sql
-- Через tag.safety_critical_item = YES
SELECT
    t.tag_name,
    t.safety_critical_item,
    t.safety_critical_item_reason_awarded
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND (t.safety_critical_item_reason_awarded IS NULL OR TRIM(t.safety_critical_item_reason_awarded) = '')
ORDER BY t.tag_name;

-- Через mapping.tag_sece
SELECT
    t.tag_name,
    t.safety_critical_item_reason_awarded
FROM project_core.tag t
JOIN mapping.tag_sece ts ON ts.tag_id = t.id
WHERE t.object_status  = 'Active'
  AND ts.mapping_status = 'Active'
  AND (t.safety_critical_item_reason_awarded IS NULL OR TRIM(t.safety_critical_item_reason_awarded) = '')
ORDER BY t.tag_name;
```

---

### CRS-C15 — PRODUCTION_CRITICAL_ITEM пустое значение

**Типовой текст:** *"The Production Critical Item field is currently blank"*

```sql
SELECT
    t.tag_name,
    t.production_critical_item,
    COALESCE(c.name, t.tag_class_raw) AS tag_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND (t.production_critical_item IS NULL OR TRIM(t.production_critical_item) = '')
ORDER BY t.tag_name;
```

---

### CRS-C16 — Дубликаты тегов

**Типовой текст:** *"Duplicate Check: Please remove the duplicate values" / "N duplicate records noted"*

```sql
-- Дубли tag_name среди активных тегов (теоретически защищено UNIQUE source_id, но аудит важен)
SELECT tag_name, COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_name
HAVING COUNT(*) > 1
ORDER BY cnt DESC;

-- Дубли source_id
SELECT source_id, COUNT(*) AS cnt
FROM project_core.tag
GROUP BY source_id
HAVING COUNT(*) > 1;
```

---

### CRS-C17 — Tag Property: тег не существует в MTR

**Типовой текст:** *"Listed N records are part of Tag property register but corresponding Tags are not available in MTR"*

```sql
SELECT
    pv.tag_name_raw,
    t.object_status,
    COUNT(pv.id) AS property_rows
FROM project_core.property_value pv
LEFT JOIN project_core.tag t ON t.id = pv.tag_id
WHERE pv.object_status = 'Active'
  AND (
      t.id IS NULL                  -- тег вообще не существует (orphan FK)
      OR t.object_status != 'Active' -- тег неактивен
  )
GROUP BY pv.tag_name_raw, t.object_status
ORDER BY property_rows DESC;
```

---

### CRS-C18 — PROPERTY_VALUE = "NA" при непустом UOM

**Типовой текст:** *"If the property value is NA, the corresponding UOM should not contain any value"*  
**⚠ Исправление v2.0:** `pv.value` → `pv.property_value`; `pv.unit_raw` → `pv.property_uom_raw`

```sql
SELECT
    t.tag_name,
    pv.property_code_raw   AS property_code,
    pv.property_value,      -- ИСПРАВЛЕНО v2.0 (было: pv.value)
    pv.property_uom_raw    AS uom  -- ИСПРАВЛЕНО v2.0 (было: pv.unit_raw)
FROM project_core.property_value pv
JOIN project_core.tag t ON t.id = pv.tag_id
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(pv.property_value,''))) IN ('NA','N/A')
  AND pv.property_uom_raw IS NOT NULL
  AND TRIM(pv.property_uom_raw) != ''
ORDER BY t.tag_name, pv.property_code_raw;
```

---

### CRS-C19 — PROPERTY_VALUE = "0" (нулевое значение)

**Типовой текст:** *"Listed N records have property value as '0'. It is flagged for review"*  
**⚠ Исправление v2.0:** `pv.value` → `pv.property_value`; `pv.unit_raw` → `pv.property_uom_raw`

```sql
SELECT
    t.tag_name,
    pv.property_code_raw AS property_code,
    pv.property_value,    -- ИСПРАВЛЕНО v2.0
    pv.property_uom_raw  AS uom  -- ИСПРАВЛЕНО v2.0
FROM project_core.property_value pv
JOIN project_core.tag t ON t.id = pv.tag_id
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND TRIM(COALESCE(pv.property_value,'')) = '0'
ORDER BY t.tag_name, pv.property_code_raw;
```

---

### CRS-C20 — Property class mapping не совпадает (TagProperty_NA)

**Типовой текст:** *"For N records, the Tag class mapping against Tag in Tag Property CSV is different/NA"*

```sql
-- Свойства, чей property_code не входит в допустимый набор для класса тега
SELECT
    t.tag_name,
    c.name                         AS tag_class,
    pv.property_code_raw           AS property_code,
    'PROPERTY NOT IN CLASS SCOPE'  AS issue
FROM project_core.property_value pv
JOIN project_core.tag t    ON t.id  = pv.tag_id
JOIN ontology_core.class c ON c.id  = t.class_id
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND NOT EXISTS (
      SELECT 1
      FROM ontology_core.class_property cp
      JOIN ontology_core.property p ON p.id = cp.property_id
      WHERE cp.class_id = t.class_id
        AND p.code = pv.property_code_raw
        AND cp.mapping_status = 'Active'
  )
ORDER BY t.tag_name, pv.property_code_raw;
```

---

### CRS-C21 — Тег без единой property в Tag Property CSV

**Типовой текст:** *"For N Tags which are part of Tag CSV, do not have any property against them in Tag Property CSV"*

```sql
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)     AS tag_class,
    COALESCE(pu.code, t.process_unit_raw) AS process_unit
FROM project_core.tag t
LEFT JOIN ontology_core.class         c  ON c.id  = t.class_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE t.object_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM project_core.property_value pv
      WHERE pv.tag_id = t.id AND pv.object_status = 'Active'
  )
ORDER BY t.tag_name;
-- COUNT: SELECT COUNT(*) FROM project_core.tag t WHERE object_status='Active' AND NOT EXISTS (SELECT 1 FROM project_core.property_value pv WHERE pv.tag_id=t.id AND pv.object_status='Active');
```

---

### CRS-C22 — Обязательные ISM properties не поданы

**Типовой текст:** *"Tag_Property_Scope_Table: Listed Properties are not provided in CIS Submission which are required as per ISM"*  
**⚠ Исправление v2.0:** `cp.is_required = TRUE` → `cp.mapping_presence = 'Mandatory'` (поле `is_required` отсутствует в schema.sql; реальное поле — `mapping_presence TEXT`)

```sql
-- Для каждого активного тега: Mandatory properties из RDL, которых нет в property_value
SELECT
    t.tag_name,
    c.name                       AS tag_class,
    p.code                       AS required_property,
    'MISSING MANDATORY PROPERTY' AS issue
FROM project_core.tag t
JOIN ontology_core.class          c  ON c.id  = t.class_id
JOIN ontology_core.class_property cp ON cp.class_id = c.id
JOIN ontology_core.property       p  ON p.id  = cp.property_id
WHERE t.object_status  = 'Active'
  AND cp.mapping_presence = 'Mandatory'  -- ИСПРАВЛЕНО v2.0 (было: cp.is_required = TRUE)
  AND cp.mapping_status   = 'Active'
  AND NOT EXISTS (
      SELECT 1
      FROM project_core.property_value pv
      WHERE pv.tag_id = t.id
        AND pv.property_code_raw = p.code
        AND pv.object_status = 'Active'
  )
ORDER BY t.tag_name, p.code;

-- Счётчик по классам
SELECT c.name AS tag_class, p.code AS missing_property, COUNT(t.id) AS affected_tags
FROM project_core.tag t
JOIN ontology_core.class          c  ON c.id  = t.class_id
JOIN ontology_core.class_property cp ON cp.class_id = c.id AND cp.mapping_presence = 'Mandatory' AND cp.mapping_status = 'Active'
JOIN ontology_core.property       p  ON p.id  = cp.property_id
WHERE t.object_status = 'Active'
  AND NOT EXISTS (SELECT 1 FROM project_core.property_value pv WHERE pv.tag_id=t.id AND pv.property_code_raw=p.code AND pv.object_status='Active')
GROUP BY c.name, p.code
ORDER BY affected_tags DESC;
```

---

### CRS-C23 — EQUIPMENT_CLASS не в RDL

**Типовой текст:** *"For N Equipment Numbers, Equipment Class is not matching with Jackdaw ISM (RDL)"*

```sql
SELECT
    t.equip_no          AS equipment_number,
    t.tag_name,
    t.tag_class_raw     AS submitted_class,
    'CLASS NOT IN RDL'  AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.class_id IS NULL
  AND t.tag_class_raw IS NOT NULL AND t.tag_class_raw != ''
ORDER BY t.tag_class_raw;
```

---

### CRS-C24 — EQUIPMENT_DESCRIPTION пустая

**Типовой текст:** *"For N Equipments, EQUIPMENT_DESCRIPTION is not available"*

```sql
SELECT
    t.equip_no AS equipment_number,
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND (t.description IS NULL OR TRIM(t.description) = '')
ORDER BY t.tag_name;
```

---

### CRS-C25 — MANUFACTURER_SERIAL_NUMBER пустой / "NA"

**Типовой текст:** *"For N Equipments, Manufacturer Serial Number is blank, which is mandatory property as per EIS"*

```sql
SELECT
    t.equip_no   AS equipment_number,
    t.tag_name,
    t.serial_no,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND (
      t.serial_no IS NULL
      OR TRIM(t.serial_no) = ''
      OR UPPER(TRIM(t.serial_no)) = 'NA'
  )
ORDER BY t.tag_name;
-- COUNT: SELECT COUNT(*) FROM project_core.tag WHERE object_status='Active' AND equip_no IS NOT NULL AND (serial_no IS NULL OR TRIM(serial_no)='');
```

---

### CRS-C26 — MODEL_PART_NAME пустой

**Типовой текст:** *"For N Equipments, Model Part Name is missing, which is mandatory property as per EIS (Except soft tags)"*

```sql
SELECT
    t.equip_no          AS equipment_number,
    t.tag_name,
    t.model_part_raw    AS submitted_model_part,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.model_id IS NULL
  AND (t.model_part_raw IS NULL OR TRIM(t.model_part_raw) = '')
ORDER BY t.tag_name;
```

---

### CRS-C27 — MANUFACTURER_COMPANY (MFG) не заполнен

**Типовой текст:** *"Manufacturing company is not populated for listed N equipments"*

```sql
SELECT
    t.equip_no                        AS equipment_number,
    t.tag_name,
    t.manufacturer_company_raw,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.manufacturer_id IS NULL
  AND (t.manufacturer_company_raw IS NULL OR TRIM(t.manufacturer_company_raw) = '')
ORDER BY t.tag_name;
```

---

### CRS-C28 — Equipment: соответствующий тег не в MTR

**Типовой текст:** *"For N Equipment Numbers, the corresponding listed Tags are not part of Tag CSV (MTR)"*  
**⚠ Исправление v2.0:** Убрана недокументированная проверка `Equip_{tag_name}`. Используется `source_id` как канонический идентификатор.

```sql
-- Оборудование, у которого equip_no задан, но tag_name отсутствует в активных тегах
-- (защищает от ситуации когда equip_no ссылается на внешний реестр, не загруженный в MTR)
SELECT
    t.equip_no      AS equipment_number,
    t.tag_name,
    t.source_id,
    t.object_status AS tag_object_status
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND NOT EXISTS (
      -- Проверяем: существует ли активный тег с таким же tag_name (self-check через source_id)
      SELECT 1 FROM project_core.tag ref
      WHERE ref.tag_name = t.tag_name
        AND ref.object_status = 'Active'
        AND ref.equip_no IS NULL  -- парный «чистый» тег без equip_no
  )
ORDER BY t.equip_no;

-- Дополнительно: оборудование без equip_no (не числится в equipment register)
SELECT tag_name, tag_class_raw
FROM project_core.tag
WHERE object_status = 'Active'
  AND equip_no IS NULL
  AND tag_class_raw ILIKE ANY (ARRAY['%pump%','%compressor%','%heat exchanger%','%vessel%','%crane%'])
ORDER BY tag_class_raw, tag_name;
```

---

### CRS-C29 — PLANT_CODE невалидный (SWA, VEN и др.)

**Типовой текст:** *"PlantCode is SWA — not part of Area register" / "Plant Code Missing in Deliverable"*

```sql
-- plant_raw заполнен, FK не разрешился
SELECT
    t.tag_name,
    t.plant_raw             AS submitted_plant_code,
    'PLANT NOT IN REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.plant_raw IS NOT NULL AND t.plant_raw != ''
  AND t.plant_id IS NULL
ORDER BY t.plant_raw;

-- Группировка по невалидным кодам
SELECT plant_raw, COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
  AND plant_id IS NULL
  AND plant_raw IS NOT NULL AND plant_raw != ''
GROUP BY plant_raw
ORDER BY cnt DESC;
```

---

### CRS-C30 — Документ не в DocMaster / статус NYI или CAN

**Типовой текст:** *"Listed N document numbers are not available in Assai OR still in NYI (Not Yet Issued) status"*

```sql
SELECT
    doc.doc_number,
    doc.title,
    doc.status,
    doc.rev,
    doc.object_status
FROM project_core.document doc
WHERE doc.object_status = 'Active'
  AND (
      doc.status IS NULL
      OR UPPER(TRIM(doc.status)) IN ('NYI','CAN')
  )
ORDER BY doc.doc_number;
-- COUNT NYI: SELECT COUNT(*) FROM project_core.document WHERE object_status='Active' AND UPPER(COALESCE(status,''))='NYI';
```

---

### CRS-C31 — Тег без документной ссылки (Doc-Tag)

**Типовой текст:** *"For N Tags which are part of Tag CSV do not have document references"*

```sql
SELECT
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw)     AS tag_class,
    COALESCE(pu.code, t.process_unit_raw) AS process_unit
FROM project_core.tag t
LEFT JOIN ontology_core.class         c  ON c.id  = t.class_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE t.object_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM mapping.tag_document td
      WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  )
ORDER BY t.tag_name;
```

---

### CRS-C32 — Документ есть в Doc-Tag, но не в DocMaster

**Типовой текст:** *"These documents are available in Document to Tag reference but not in Document Master CSV"*

```sql
SELECT
    td.doc_number_raw               AS referenced_doc,
    COUNT(DISTINCT td.tag_id)       AS tag_count,
    'NOT IN DOCUMENT MASTER'        AS issue
FROM mapping.tag_document td
WHERE td.mapping_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM project_core.document doc
      WHERE doc.doc_number = td.doc_number_raw
        AND doc.object_status = 'Active'
  )
GROUP BY td.doc_number_raw
ORDER BY tag_count DESC;
```

---

### CRS-C33 — Тег в Doc-Tag не существует в MTR

**Типовой текст:** *"Tag NA in MTR: Listed N line items having N unique tags are not part of Tag Register"*

```sql
SELECT
    td.tag_name_raw           AS referenced_tag,
    COUNT(DISTINCT td.document_id) AS doc_count,
    'NOT IN MTR (Active)'     AS issue
FROM mapping.tag_document td
WHERE td.mapping_status = 'Active'
  AND NOT EXISTS (
      SELECT 1 FROM project_core.tag t
      WHERE t.tag_name = td.tag_name_raw
        AND t.object_status = 'Active'
  )
GROUP BY td.tag_name_raw
ORDER BY doc_count DESC;
```

---

### CRS-C34 — Doc-Area: AREA_CODE отсутствует

**Типовой текст:** *"Listed N document numbers as part of Doc Reference to Area do not have 'Area_Code'"*  
**Примечание:** `mapping.tag_document` не хранит area напрямую — связь только через `project_core.tag.area_id`

```sql
-- Документы с тегами, у которых area_id IS NULL (seq 017 экспорт будет иметь пустой AREA_CODE)
SELECT
    d.doc_number,
    COUNT(DISTINCT t.id) AS tags_without_area
FROM mapping.tag_document td
JOIN project_core.document d ON d.id = td.document_id
JOIN project_core.tag      t ON t.id = td.tag_id
WHERE td.mapping_status = 'Active'
  AND d.object_status   = 'Active'
  AND t.object_status   = 'Active'
  AND t.area_id IS NULL
GROUP BY d.doc_number
ORDER BY tags_without_area DESC;
```

---

### CRS-C35 — Doc-PU: PROCESS_UNIT_CODE отсутствует

**Типовой текст:** *"For N records, Process Unit code is missing in Document reference to Process Unit register"*  
**Примечание:** Связь только через `project_core.tag.process_unit_id`

```sql
SELECT
    d.doc_number,
    COUNT(DISTINCT t.id) AS tags_without_pu
FROM mapping.tag_document td
JOIN project_core.document d ON d.id = td.document_id
JOIN project_core.tag      t ON t.id = td.tag_id
WHERE td.mapping_status = 'Active'
  AND d.object_status   = 'Active'
  AND t.object_status   = 'Active'
  AND t.process_unit_id IS NULL
GROUP BY d.doc_number
ORDER BY tags_without_pu DESC;
```

---

### CRS-C36 — PO_CODE не в PO Register

**Типовой текст:** *"For listed N Tags, PO number is either not available/not matching with the PO CSV"*

```sql
-- Теги с po_code_raw, FK не разрешился
SELECT
    t.tag_name,
    t.po_code_raw        AS submitted_po_code,
    'PO NOT IN REGISTER' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.po_code_raw IS NOT NULL AND t.po_code_raw != ''
  AND t.po_id IS NULL
ORDER BY t.po_code_raw;

-- Топ нераспознанных PO-кодов
SELECT po_code_raw, COUNT(*) AS affected_tags
FROM project_core.tag
WHERE object_status = 'Active' AND po_id IS NULL AND po_code_raw IS NOT NULL AND po_code_raw != ''
GROUP BY po_code_raw ORDER BY affected_tags DESC;
```

---

### CRS-C37 — PO_DATE отсутствует

**Типовой текст:** *"Listed N PO Codes do not have PO date which is mandatory field for PO register"*

```sql
SELECT
    po.code     AS po_code,
    po.po_date,
    COUNT(t.id) AS tags_linked
FROM reference_core.purchase_order po
LEFT JOIN project_core.tag t ON t.po_id = po.id AND t.object_status = 'Active'
WHERE po.object_status = 'Active'
  AND po.po_date IS NULL
GROUP BY po.code, po.po_date
ORDER BY tags_linked DESC;
```

---

### CRS-C38 — COMPANY_NAME отсутствует / невалиден / двойной пробел

**Типовой текст:** *"Company name not available for listed N PO code" / "Company name has double space"*

```sql
-- PO без issuer company
SELECT po.code AS po_code, 'ISSUER COMPANY MISSING' AS issue
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active' AND po.issuer_id IS NULL
ORDER BY po.code;

-- Оборудование без manufacturer company
SELECT t.tag_name, t.manufacturer_company_raw, 'NO MANUFACTURER COMPANY' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.manufacturer_id IS NULL
  AND (t.manufacturer_company_raw IS NULL OR TRIM(t.manufacturer_company_raw) = '')
ORDER BY t.tag_name;

-- Company с двойными пробелами
SELECT id, name AS company_name, 'DOUBLE SPACE IN NAME' AS issue
FROM reference_core.company
WHERE object_status = 'Active' AND name LIKE '%  %'
ORDER BY name;
```

---

### CRS-C39 — Дубликаты в Tag Physical Connection

**Типовой текст:** *"Duplicate Check: Kindly remove the duplicate values" (файл 006)*

```sql
-- Дублирующиеся пары from_tag → to_tag среди активных тегов
SELECT
    from_tag_raw,
    to_tag_raw,
    COUNT(*) AS duplicate_count
FROM project_core.tag
WHERE object_status = 'Active'
  AND from_tag_raw IS NOT NULL
  AND to_tag_raw IS NOT NULL
GROUP BY from_tag_raw, to_tag_raw
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

---

### CRS-C40 — Equipment без Doc-Equipment маппинга

**Типовой текст:** *"Listed N Equipments do not have any document reference"*

```sql
SELECT
    t.equip_no    AS equipment_number,
    t.tag_name,
    COALESCE(c.name, t.tag_class_raw) AS equipment_class,
    'NO DOC-EQUIPMENT MAPPING' AS issue
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM mapping.tag_document td
      WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  )
ORDER BY t.tag_name;
```

---

## Новые категории C41–C50

---

### CRS-C41 — EX_CLASS / IP_GRADE пустые у E&I тегов

**Паттерн:** *"Ex classification is missing for zone 1/2 equipment"* — типово для offshore E&I  
**Поля схемы:** `project_core.tag.ex_class`, `project_core.tag.ip_grade`

```sql
-- Инструментальные теги без EX классификации
SELECT
    t.tag_name,
    t.tag_class_raw,
    t.area_code_raw,
    t.ex_class,
    t.ip_grade
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.ex_class IS NULL
  AND t.ip_grade IS NULL
  AND t.tag_class_raw ~* '(transmitter|sensor|junction.box|control.station|detector|analyser)'
ORDER BY t.tag_class_raw, t.tag_name;

-- Сводка по классам без EX данных
SELECT
    t.tag_class_raw,
    COUNT(*) AS tags_without_ex
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.ex_class IS NULL
  AND t.tag_class_raw IS NOT NULL
GROUP BY t.tag_class_raw
ORDER BY tags_without_ex DESC
LIMIT 20;
```

---

### CRS-C42 — MC_PACKAGE_CODE не заполнен (commissioning)

**Паттерн:** *"MC Package Code is missing for listed tags — required for completions"*  
**Поле схемы:** `project_core.tag.mc_package_code`

```sql
SELECT
    t.tag_name,
    t.tag_class_raw,
    t.process_unit_raw,
    t.mc_package_code
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (t.mc_package_code IS NULL OR TRIM(t.mc_package_code) = '')
  AND t.tag_class_raw ~* '(valve|instrument|electrical|mechanical)'
ORDER BY t.tag_class_raw, t.tag_name;

-- COUNT:
-- SELECT COUNT(*) FROM project_core.tag WHERE object_status='Active' AND (mc_package_code IS NULL OR TRIM(mc_package_code)='');
```

---

### CRS-C43 — ALIAS конфликтует с другим тегом

**Паттерн:** Alias должен быть уникален и не совпадать с tag_name другого тега  
**Поле схемы:** `project_core.tag.alias`

```sql
-- Alias дублируется между разными тегами
SELECT
    alias,
    ARRAY_AGG(tag_name ORDER BY tag_name) AS conflicting_tags,
    COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
  AND alias IS NOT NULL AND TRIM(alias) != ''
GROUP BY alias
HAVING COUNT(*) > 1
ORDER BY cnt DESC;

-- Alias совпадает с tag_name другого активного тега
SELECT
    t1.tag_name,
    t1.alias,
    t2.tag_name AS conflicts_with_tag
FROM project_core.tag t1
JOIN project_core.tag t2
    ON t2.tag_name = t1.alias AND t2.id != t1.id
WHERE t1.object_status = 'Active'
  AND t2.object_status = 'Active';
```

---

### CRS-C44 — TECH_ID пустой у instrument-тегов

**Паттерн:** *"TECH_ID is missing / does not follow expected format"*  
**Поле схемы:** `project_core.tag.tech_id`

```sql
SELECT
    t.tag_name,
    t.tech_id,
    t.tag_class_raw
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (t.tech_id IS NULL OR TRIM(t.tech_id) = '')
  AND t.tag_class_raw ~* '(instrument|loop|signal|transmitter)'
ORDER BY t.tag_class_raw, t.tag_name;

-- COUNT:
-- SELECT COUNT(*) FROM project_core.tag WHERE object_status='Active' AND (tech_id IS NULL OR TRIM(tech_id)='') AND tag_class_raw ~* '(instrument|loop|signal|transmitter)';
```

---

### CRS-C45 — FROM_TAG / TO_TAG не существуют в MTR

**Паттерн:** *"Listed tags have from/to tag connections referencing tags not in MTR"*  
**Поля схемы:** `project_core.tag.from_tag_raw`, `from_tag_id`, `to_tag_raw`, `to_tag_id`  
**Примечание:** Выделено из C39 — C39 = дублирующиеся пары, C45 = неразрешённые FK.

```sql
-- C45a: from_tag_raw заполнен, FK не разрешился
SELECT
    t.tag_name,
    t.from_tag_raw    AS declared_from,
    'FROM_TAG NOT IN MTR' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.from_tag_raw IS NOT NULL AND TRIM(t.from_tag_raw) != ''
  AND t.from_tag_id IS NULL
ORDER BY t.from_tag_raw;

-- C45b: to_tag_raw заполнен, FK не разрешился
SELECT
    t.tag_name,
    t.to_tag_raw      AS declared_to,
    'TO_TAG NOT IN MTR' AS issue
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.to_tag_raw IS NOT NULL AND TRIM(t.to_tag_raw) != ''
  AND t.to_tag_id IS NULL
ORDER BY t.to_tag_raw;

-- Сводно: уникальные нераспознанные references
SELECT
    COALESCE(t.from_tag_raw, t.to_tag_raw) AS unresolved_ref,
    CASE WHEN t.from_tag_raw IS NOT NULL THEN 'FROM' ELSE 'TO' END AS direction,
    COUNT(*) AS affected_tags
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND (
      (t.from_tag_raw IS NOT NULL AND t.from_tag_id IS NULL)
      OR (t.to_tag_raw IS NOT NULL AND t.to_tag_id IS NULL)
  )
GROUP BY unresolved_ref, direction
ORDER BY affected_tags DESC;
```

---

### CRS-C46 — TAG_STATUS вне допустимого словаря

**Паттерн:** ISO 15926 / CFIHOS — статус объекта должен быть из допустимого словаря  
**Поле схемы:** `project_core.tag.tag_status`

```sql
-- Обзор всех значений tag_status у активных тегов
SELECT
    COALESCE(tag_status, '(NULL)') AS tag_status,
    COUNT(*) AS cnt
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_status
ORDER BY cnt DESC;

-- Теги с tag_status вне ожидаемого набора
SELECT tag_name, tag_status, tag_class_raw
FROM project_core.tag
WHERE object_status = 'Active'
  AND UPPER(COALESCE(tag_status,'')) NOT IN (
      'DESIGN', 'FOR_CONSTRUCTION', 'INSTALLED',
      'COMMISSIONED', 'FOR_INFORMATION',
      'CANCELLED', 'DELETED', 'VOID', ''
  )
ORDER BY tag_status, tag_name;
```

---

### CRS-C47 — Safety critical = YES, но нет записи в mapping.tag_sece

**Паттерн:** *"Safety critical items not linked to performance standard"* — Shell SECE requirement  
**Поля схемы:** `project_core.tag.safety_critical_item`, `mapping.tag_sece`

```sql
SELECT
    t.tag_name,
    t.safety_critical_item,
    t.safety_critical_item_reason_awarded
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND NOT EXISTS (
      SELECT 1 FROM mapping.tag_sece ts
      WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active'
  )
ORDER BY t.tag_name;

-- COUNT:
-- SELECT COUNT(*) FROM project_core.tag t WHERE object_status='Active' AND UPPER(TRIM(COALESCE(safety_critical_item,''))) IN ('YES','Y') AND NOT EXISTS (SELECT 1 FROM mapping.tag_sece ts WHERE ts.tag_id=t.id AND ts.mapping_status='Active');
```

---

### CRS-C48 — property_code_raw не разрешился в ontology (неизвестный код)

**Паттерн:** *"Property code not recognised in ISM — property not part of class scope"*  
**Поля схемы:** `project_core.property_value.property_id` (NULL = FK не разрешился), `property_code_raw`

```sql
-- property_id IS NULL → property_code_raw не найден в ontology_core.property при импорте
SELECT
    pv.property_code_raw,
    COUNT(DISTINCT pv.tag_id) AS affected_tags,
    'UNKNOWN PROPERTY CODE'   AS issue
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.property_id IS NULL
  AND pv.property_code_raw IS NOT NULL AND pv.property_code_raw != ''
GROUP BY pv.property_code_raw
ORDER BY affected_tags DESC;

-- Список затронутых тегов для конкретного кода
-- SELECT t.tag_name, pv.property_code_raw
-- FROM project_core.property_value pv
-- JOIN project_core.tag t ON t.id = pv.tag_id
-- WHERE pv.object_status='Active' AND pv.property_id IS NULL AND pv.property_code_raw = '<CODE>'
-- ORDER BY t.tag_name;
```

---

### CRS-C49 — Дубликат doc_number в project_core.document

**Паттерн:** AVEVA / ASSAI — один doc_number может иметь только одну активную запись  
**Поле схемы:** `project_core.document.doc_number`

```sql
-- Несколько активных строк на один doc_number
SELECT
    doc_number,
    ARRAY_AGG(rev ORDER BY rev) AS revisions,
    COUNT(*)                    AS cnt
FROM project_core.document
WHERE object_status = 'Active'
GROUP BY doc_number
HAVING COUNT(*) > 1
ORDER BY cnt DESC;

-- Детализация дублей
SELECT doc_number, rev, status, title
FROM project_core.document
WHERE object_status = 'Active'
  AND doc_number IN (
      SELECT doc_number FROM project_core.document
      WHERE object_status = 'Active'
      GROUP BY doc_number HAVING COUNT(*) > 1
  )
ORDER BY doc_number, rev;
```

---

### CRS-C50 — Circular parent reference (циклическая иерархия тегов)

**Паттерн:** ISO 15926 Part 2 — иерархия тегов не должна содержать циклов  
**Поля схемы:** `project_core.tag.parent_tag_id`

```sql
-- Рекурсивный CTE для обнаружения circular parent reference (глубина до 10)
WITH RECURSIVE tag_hierarchy AS (
    -- Базовый шаг: теги с parent_tag_id
    SELECT
        id,
        tag_name,
        parent_tag_id,
        1                AS depth,
        ARRAY[id]        AS path,
        FALSE            AS is_cycle
    FROM project_core.tag
    WHERE object_status = 'Active'
      AND parent_tag_id IS NOT NULL

    UNION ALL

    -- Рекурсивный шаг: подниматься по иерархии
    SELECT
        t.id,
        t.tag_name,
        t.parent_tag_id,
        th.depth + 1,
        th.path || t.id,
        t.id = ANY(th.path)  -- цикл обнаружен
    FROM project_core.tag t
    JOIN tag_hierarchy th ON t.id = th.parent_tag_id
    WHERE NOT th.is_cycle   -- прерываем при первом обнаружении цикла
      AND th.depth < 10     -- защита от бесконечной рекурсии
)
SELECT DISTINCT
    tag_name,
    depth AS cycle_detected_at_depth
FROM tag_hierarchy
WHERE is_cycle = TRUE
ORDER BY cycle_detected_at_depth DESC, tag_name;
```

---

## Сводная таблица объектов БД

| Таблица | query_codes | Ключевые поля проверки |
|---|---|---|
| `project_core.tag` | C01–C16, C23–C29, C39–C47 | `description`, `class_id`, `area_id`, `process_unit_id`, `parent_tag_id`, `safety_critical_item`, `serial_no`, `equip_no`, `ex_class`, `ip_grade`, `mc_package_code`, `alias`, `tech_id`, `from_tag_raw`, `to_tag_raw` |
| `project_core.property_value` | C17–C22, C48 | `tag_id`, `property_value`, `property_uom_raw`, `property_code_raw`, `property_id` |
| `project_core.document` | C30, C32, C49 | `status`, `object_status`, `mdr_flag`, `doc_number` |
| `mapping.tag_document` | C31–C35, C40 | `tag_id`, `document_id`, `mapping_status`, `tag_name_raw`, `doc_number_raw` |
| `mapping.document_po` | C36 | `document_id`, `po_id` |
| `mapping.tag_sece` | C14, C47 | `tag_id`, `sece_id`, `mapping_status` |
| `reference_core.area` | C06–C07, C34 | `code`, `plant_id` |
| `reference_core.process_unit` | C08–C09, C35 | `code`, `plant_id` |
| `reference_core.plant` | C29 | `code` |
| `reference_core.purchase_order` | C36–C37 | `code`, `po_date`, `issuer_id` |
| `reference_core.company` | C38 | `name` |
| `reference_core.model_part` | C26 | `code`, `name` |
| `ontology_core.class` | C04, C10, C12, C20, C22–C23 | `name`, `is_abstract`, `concept`, `parent_class_id` |
| `ontology_core.class_property` | C20, C22 | `class_id`, `property_id`, `mapping_presence`, `mapping_status`, `mapping_concept` |
| `ontology_core.property` | C22, C48 | `code`, `name`, `data_type` |

---

## Changelog — Исправления v2.0

| # | Категория | Что изменено | Причина |
|---|---|---|---|
| 1 | C18, C19 | `pv.value` → `pv.property_value`; `pv.unit_raw` → `pv.property_uom_raw` | Реальные имена колонок `project_core.property_value` по schema.sql |
| 2 | C22 | `cp.is_required = TRUE` → `cp.mapping_presence = 'Mandatory'` | Поле `is_required` отсутствует в schema.sql; реальное поле `mapping_presence TEXT` подтверждено в `export_tag_class_properties.py` |
| 3 | C05 | Добавлен `LEFT JOIN ontology_core.class c ON c.id = t.class_id` в третий запрос | Без JOIN запрос упадёт с `column "c.name" does not exist` |
| 4 | C28 | Убрана предположительная проверка `equip_no = 'Equip_' \|\| tag_name` | Соглашение нигде не задокументировано в schema.sql; заменено на structural check через `source_id` |
| 5 | C39 | Запрос сужен до дублирующихся пар (без проверки FK) | FK-проверки выделены в новую категорию **C45** |
| 6 | Сводная таблица | Добавлены колонки `query_code` (формат `CRS-Cxx`) и `mapping_presence` | Для прямой вставки в `audit_core` и классификации по обязательности |
| 7 | C41–C50 | Добавлены 10 новых категорий | Поля `ex_class`, `ip_grade`, `mc_package_code`, `alias`, `tech_id`, `from/to_tag`, `tag_sece` присутствуют в schema.sql и не были покрыты в v1.0 |

---

## Примечания по реализации

1. **Все запросы** используют `WHERE object_status = 'Active'` для entity-таблиц и `WHERE mapping_status = 'Active'` для mapping-таблиц — в строгом соответствии с архитектурным контрактом проекта.

2. **`sync_status`** намеренно не используется как фильтр ни в одном запросе — это ETL-контрольное поле, не фильтр экспорта.

3. **C22** зависит от заполненности `ontology_core.class_property.mapping_presence` из RDL-онтологии. Проверить: `SELECT COUNT(*) FROM ontology_core.class_property WHERE mapping_presence = 'Mandatory' AND mapping_status = 'Active';` — если 0, заполнение из JDAW-PT-D-JA-7880-00001_A05.xlsx ещё не произошло.

4. **C50** (recursive CTE) — выполнять с осторожностью на больших данных. Параметр `depth < 10` защищает от бесконечной рекурсии при реальных циклах.

5. **C41–C44** (ex_class, mc_package_code, alias, tech_id) — применимость зависит от доменного контекста: не все классы тегов обязаны иметь эти поля. Запросы содержат class-фильтры для сужения выборки.

6. **C45** отделена от **C39**: дубликаты physical connection (C39) и нераспознанные FK references (C45) — разные по природе дефекты, требующие разных корректирующих действий.
