# Validation Rules — Review & Optimization Summary
**Project:** EDW for Jackdaw  
**Источники:** `export_validation_rule.xlsx` (82 правила) · `ex-data-extractor-help.txt` (Power Query логика)  
**Дата:** 2026-03-13  

---

## 1. Анализ комментариев из файла (твои замечания)

### [1] NO_INVALID_CHARS + ENCODING_ARTEFACTS → объединить в одно правило

**Текущее состояние:**
```
NO_INVALID_CHARS    → * contains "<"         fix: remove_char "<"
ENCODING_ARTEFACTS  → * has_encoding_artefacts  fix: encoding_repair
```

**Комментарий:** символ `<` — не единственный проблемный. Плюс предложено объединить с encoding.

**Рекомендация:** Разделить ответственность иначе — не объединять оба в одно:

- `ENCODING_ARTEFACTS` оставить как есть — это специализированный 12-step pipeline (`clean_engineering_text`), он несовместим с простым DSL `remove_char`
- `NO_INVALID_CHARS` расширить до полного списка проблемных символов по паттерну из Power Query:

```sql
-- Обновить rule_expression для NO_INVALID_CHARS:
rule_expression = '* matches_regex "[<>{}|\\\\^`]"'
fix_expression  = 'encoding_repair'   -- делегировать в clean_engineering_text, он уже убирает контрольные символы
description     = 'Invalid non-printable or structurally hazardous chars: <, >, {, }, |, ^, ` — removed by encoding_repair pipeline'
```

Из Power Query видно конкретные проблемные символы: `MM²`, `–>`, ` – `, `–`, NBSP (`\u00a0`), `    ` (4 пробела). Все они уже обрабатываются `clean_engineering_text()` в `ENCODING_ARTEFACTS`. Дублировать не нужно — нужно убедиться что `ENCODING_ARTEFACTS` is_builtin=true и выполняется первым.

---

### [2] SECE_SEMICOLON_DELIMITER — избыточное правило

**Комментарий:** Поле SAFETY_CRITICAL_ITEM_GROUP в источнике всегда заполняется через пробел, не через запятую.

**Рекомендация:** Перевести правило из `is_builtin=true` в `is_builtin=false`, scope оставить. Оставить как full-scan правило для аномалий — на случай если данные придут из другого источника. Добавить comment в description:

```sql
UPDATE: is_builtin = false, severity = 'Info'
description = 'SECE multi-values separator check — comma found (source always uses space; this fires only if data source changes)'
```

---

### [3] DESC_NO_DOUBLE_SPACE → расширить на все поля, перенести в common

**Комментарий:** Правило применимо ко всем полям, не только к description. Также нужны тройные+ пробелы.

**Рекомендация:** Заменить текущее правило на два более широких:

```sql
-- Удалить: DESC_NO_DOUBLE_SPACE (scope=tag, только TAG_DESCRIPTION)

-- Добавить вместо:
rule_code       = 'MULTIPLE_SPACES_IN_TEXT'
scope           = 'common'
tier            = 'L1'
rule_expression = '* matches_regex "  "'       -- 2+ пробела подряд
fix_expression  = 'normalize_spaces'           -- новая fix-операция (см. раздел 4)
is_builtin      = true
description     = 'Any text field must not contain consecutive spaces (2 or more) — collapse to single space'
```

Power Query подтверждает это требование: `Text.Replace([TAG_DESCRIPTION], "  ", " ")` и `Text.Replace([TAG_DESCRIPTION], "    ", " ")` применяются к description. Расширение на все поля логично.

---

### [4] PSEUDO_NULL_NA_FORMAT — расширить fix и добавить uppercase

**Комментарий:** Добавить в fix варианты `N/A`, `N.A` и всегда делать uppercase.

**Рекомендация:** Текущий DSL `fix_expression` поддерживает только одну операцию `replace`. Нужно либо:

**Вариант A** (без изменения движка) — добавить 3 отдельных builtin правила:
```sql
PSEUDO_NULL_NA_FORMAT_1: rule_expr='* matches_regex "(?i)^N\\.A\\.?$"'  fix='normalize_na_string'
PSEUDO_NULL_NA_FORMAT_2: rule_expr='* matches_regex "(?i)^[Nn]/[Aa]$"'  fix='normalize_na_string'  
PSEUDO_NULL_NA_FORMAT_3: rule_expr='* matches_regex "^na$"'             fix='normalize_na_string'
-- normalize_na_string = новая fix-операция: заменяет любой вариант на "NA" uppercase
```

**Вариант B** (рекомендуется) — добавить новую fix-операцию `normalize_na` в движок:
```python
# В _fix_series():
if fix_expr == "normalize_na":
    # Replace all NA variants with strict "NA"
    return s.str.replace(r"(?i)^(N\.A\.?|N/A|na|n/a)$", "NA", regex=True)
```

```sql
-- Обновить правило:
rule_expression = '* matches_regex "(?i)^(N\\.A\\.?|N/A|na|n/a)$"'
fix_expression  = 'normalize_na'
```

---

## 2. Gap-анализ: Power Query → Validation Rules

Все Power Query трансформации проверены против списка правил. Ниже — что есть в PQ, но **не отражено** в validation rules.

### 2.1 MTR Dataset Query — пропущенные правила

**PQ логика:**
```powerquery
-- Фильтр дубликатов: не экспортировать SIGNAL-теги с COUNT>=2, 
-- не экспортировать дубли с TAG_STATUS VOID/Future/пустой
Filtered_By_Count = Table.SelectRows(..., 
    each not([COUNT] >= 2 and [TAG_CLASS_NAME] = "SIGNAL") 
    and not([COUNT] >= 2 and List.Contains({"VOID", "Future", ""}, [TAG_STATUS])))
```

**Статус:** ❌ Не отражено в validation rules.

**Новое правило:**
```sql
rule_code       = 'SIGNAL_TAG_NO_DUPLICATES'
scope           = 'tag'
tier            = 'L0'
category        = 'Uniqueness'
check_type      = 'aggregate'
rule_expression = 'aggregate: COUNT(tag_name) >= 2 WHERE tag_class_name = ''SIGNAL'''
description     = 'SIGNAL tags must be unique — duplicate SIGNAL tag names indicate a source extraction error (split/merge artifact)'
is_builtin      = false, is_blocking = true, severity = 'Critical'
```

---

**PQ логика:**
```powerquery
-- "unset" в PARENT_TAG_NAME заменяется на пустую строку
Replace_ParentTag = Table.ReplaceValue(..., "unset", "", ..., {"PARENT_TAG_NAME"})
```

**Статус:** ✅ Обрабатывается в `transform_tag_register()` Python-кодом (`df["PARENT_TAG_NAME"].replace("unset", "")`). Но в validation rules нет явного правила-свидетеля.

**Рекомендация:** Добавить как built-in правило для прозрачности:
```sql
rule_code       = 'PARENT_TAG_UNSET_VALUE'
scope           = 'tag'
tier            = 'L1'
category        = 'Syntax'
check_type      = 'dsl'
rule_expression = 'PARENT_TAG_NAME icontains "unset"'
fix_expression  = 'replace "unset" ""'
is_builtin      = true, severity = 'Info'
description     = 'PARENT_TAG_NAME value "unset" must be replaced with empty string — source system artifact'
```

---

**PQ логика:**
```powerquery
Replace_BadSymbols: 
  MM²     → mm2
  –>      → ->
  " – "   → " - "
  –       → -
  NBSP (\u00a0) → пробел
```

**Статус:** ✅ Частично покрыто `ENCODING_ARTEFACTS` через `clean_engineering_text()`. Но `MM²→mm2` и `–>→->` — это **семантические замены**, не только кодировочные артефакты.

**Рекомендация:** Добавить явные правила:
```sql
rule_code       = 'DESC_EM_DASH_REPLACE'
scope           = 'common', tier = 'L1', check_type = 'dsl'
rule_expression = '* contains "–"'
fix_expression  = 'replace "–" "-"'
is_builtin      = true, severity = 'Info'
description     = 'Em-dash (–) must be replaced with ASCII hyphen (-) — non-ASCII dash causes EIS import issues'

rule_code       = 'DESC_MM2_FORMAT'
scope           = 'common', tier = 'L1', check_type = 'dsl'
rule_expression = '* contains "MM²"'
fix_expression  = 'replace "MM²" "mm2"'
is_builtin      = true, severity = 'Info'
description     = 'Area unit MM² must be normalized to mm2 (lowercase, ASCII 2) — Aveva format requirement'
```

---

### 2.2 TagProperties (RDL) Query — пропущенные правила

**PQ логика:**
```powerquery
-- N/A → NA (уже есть PSEUDO_NULL_NA_FORMAT, но частично)
-- NO → No  (YES/NO нормализация регистра)
-- YES → Yes
if [Property Value] = "N/A"  then "NA"
if [Property Value] = "NO"   then "No"
if [Property Value] = "YES"  then "Yes"
```

**Статус:** ❌ `YES→Yes` и `NO→No` нормализация регистра отсутствует.

**Новое правило:**
```sql
rule_code       = 'BOOLEAN_VALUE_CASING'
scope           = 'common', tier = 'L1', category = 'Validity', check_type = 'dsl'
rule_expression = 'PROPERTY_VALUE matches_regex "^YES$|^NO$"'
fix_expression  = 'normalize_boolean_case'    -- новая операция: YES→Yes, NO→No
is_builtin      = true, severity = 'Info'
description     = 'Boolean property values YES/NO must use Title Case: Yes/No — ALL CAPS variant is rejected by EIS picklist validator'
```

---

**PQ логика:**
```powerquery
-- 999999999 или 999999 → NA (псевдо-NULL для чисел конвертируется в NA)
if ([Property Value] = "999999999" or [Property Value] = "999999") then "NA"
```

**Статус:** ❌ Нет правила которое детектирует `999999` (6 девяток) — только `999999999` (9 девяток) упоминается в документации.

**Новое правило:**
```sql
rule_code       = 'NUMERIC_PSEUDO_NULL_VARIANT'
scope           = 'common', tier = 'L2', category = 'Validity', check_type = 'dsl'
rule_expression = 'PROPERTY_VALUE matches_regex "^999999$"'
fix_expression  = 'replace "999999" "NA"'
is_builtin      = true, severity = 'Warning'
description     = 'Numeric pseudo-NULL "999999" (6 nines) is a non-standard variant — must be normalized to "NA". Approved standard is 999999999 (9 nines).'
```

---

**PQ логика:**
```powerquery
-- UoM встроен в значение → извлечь, значение очистить:
-- "490mm"  → value=490, uom=mm
-- "50kW"   → value=50,  uom=kW
-- "degC" в значении → убрать из value, поставить в uom
-- "hertz" → Hz, "volt" → V, "ampere" → A, "pascal" → Pa
```

**Статус:** ✅ Частично — `VALUE_UOM_COMBINED_IN_CELL` есть. Но нет правил на нормализацию UoM-наименований.

**Новые правила:**
```sql
rule_code       = 'UOM_LONGFORM_NORMALIZE'
scope           = 'common', tier = 'L1', category = 'UoM', check_type = 'dsl'
rule_expression = 'PROPERTY_VALUE_UOM matches_regex "(?i)^(ampere|volt|pascal|hertz|kilowatt)$"'
fix_expression  = 'normalize_uom_longform'   -- новая операция: ampere→A, volt→V, pascal→Pa, hertz→Hz, kilowatt→kW
is_builtin      = true, severity = 'Info'
description     = 'UoM long-form names must be replaced with standard abbreviations: ampere→A, volt→V, pascal→Pa, hertz→Hz, kilowatt→kW'
```

---

**PQ логика:**
```powerquery
-- Запятая в числовом значении → точка (только когда UoM присутствует)
if (([Property UoM] <> "") and Text.Contains([Property Value], ",")) 
    then Text.Replace([Property Value], ",", ".")
```

**Статус:** ✅ Есть `DECIMAL_DOT_SEPARATOR` — но без `fix_expression`. PQ это автоматически исправляет.

**Рекомендация:** Добавить fix к существующему правилу:
```sql
-- Обновить DECIMAL_DOT_SEPARATOR:
fix_expression = 'replace "," "."'
is_builtin     = true    -- PQ это автоматически фиксит, должны делать то же
```

---

**PQ логика:**
```powerquery
-- PROPERTY_VALUE = "UNSET" → исключить строку из экспорта
Table.SelectRows(..., each ([Property Value] <> null and 
    Text.Length([Property Value]) > 0 and 
    Text.Upper([Property Value]) <> "UNSET"))
```

**Статус:** ❌ Нет правила на значение "UNSET" в property value.

**Новое правило:**
```sql
rule_code       = 'PROP_VALUE_UNSET'
scope           = 'common', tier = 'L1', category = 'Validity', check_type = 'dsl'
rule_expression = 'PROPERTY_VALUE icontains "UNSET"'
fix_expression  = NULL    -- строки с UNSET должны быть исключены, не автофиксированы
is_builtin      = false, is_blocking = true, severity = 'Warning'
description     = 'PROPERTY_VALUE "UNSET" is a source-system placeholder — these rows must be excluded from EIS export (same rule as empty values)'
```

---

### 2.3 Tag-Doc Full Query — пропущенные правила

**PQ логика:**
```powerquery
-- Символ "‐" (U+2010 Unicode hyphen) → ASCII "-" (U+002D)
Table.ReplaceValue(..., "‐", "-", ..., {"TAG_NAME", "DOCUMENT_NUMBER"})
```

**Статус:** ❌ Нет явного правила. Частично покрыто `ENCODING_ARTEFACTS`, но Unicode hyphen отличается от em-dash — требует отдельного правила.

**Новое правило:**
```sql
rule_code       = 'UNICODE_HYPHEN_REPLACE'
scope           = 'common', tier = 'L1', category = 'Encoding', check_type = 'dsl'
rule_expression = '* contains "\u2010"'
fix_expression  = 'replace "\u2010" "-"'
is_builtin      = true, severity = 'Info'
description     = 'Unicode hyphen (U+2010 ‐) must be replaced with ASCII hyphen (-) — affects TAG_NAME and DOCUMENT_NUMBER field matching'
```

---

**PQ логика (MDR filter):**
```powerquery
-- Документы с DOCUMENT_STATUS = "CAN" исключаются
-- MDR=True только — документы не в MDR исключаются
-- Документы из SJDAW → PLANT_CODE = "SWA"
Table.SelectRows(..., each ([DOCUMENT_STATUS] <> "CAN" and [MDR] = "True"))
```

**Статус:** ✅ `DOC_EXISTS_IN_MDR` покрывает MDR-проверку. `VOID_DELETED_EXCLUDED_FROM_XREF` покрывает CAN статус документа частично.

**Рекомендация:** Уточнить `VOID_DELETED_EXCLUDED_FROM_XREF`:
```sql
-- Обновить description:
description = 'Tags with status VOID or DELETED and documents with status CAN must be excluded from all cross-reference matrices'
-- Обновить rule_expression:
rule_expression = 'cross_file: tag_name IN xref_matrix WHERE object_status IN (''VOID'',''DELETED'') OR doc_status = ''CAN'''
```

---

## 3. Обнаруженные дублирования в текущем списке

| Дублирующая пара | Проблема | Действие |
|---|---|---|
| `PROCESS_UNIT_MANDATORY` + `PROCESS_UNIT_NOT_NULL` | Идентичная проверка `PROCESS_UNIT_CODE is_null` в двух правилах | **Удалить** `PROCESS_UNIT_MANDATORY` (он старее, без tier/source_ref) |
| `AREA_CODE_EXPECTED` + `AREA_CODE_NOT_NULL` | Идентичная проверка `AREA_CODE is_null` | **Удалить** `AREA_CODE_EXPECTED` |
| `PO_CODE_NOT_VOID` + `PO_CODE_NOT_VOID_SUFFIX` | Одинаковый `PO_CODE icontains "-VOID"` | **Удалить** `PO_CODE_NOT_VOID` (без tier/source_ref), оставить `PO_CODE_NOT_VOID_SUFFIX` |
| `TAG_MIN_ONE_DOCUMENT` + `TAG_MIN_DOC_LINK` | Оба проверяют наличие минимум 1 Doc-link на тег | **Удалить** `TAG_MIN_ONE_DOCUMENT` — у него менее точный `rule_expression` |
| `DISCIPLINE_FK_RESOLVED` | `rule_expression = 'discipline_code_raw not_null AND discipline_code_raw not_null'` — опечатка, оба условия одинаковые | **Исправить** на `discipline_code_raw not_null AND discipline_id is_null` |

---

## 4. Новые fix-операции, необходимые для движка

Для реализации рекомендаций выше нужно добавить в `_fix_series()` в `export_validation.py`:

| fix_expression | Действие | Python |
|---|---|---|
| `normalize_na` | Любой NA-вариант → `"NA"` | `s.str.replace(r"(?i)^(N\.A\.?|N/A|na|n/a)$", "NA", regex=True)` |
| `normalize_spaces` | 2+ пробелов → один пробел | `s.str.replace(r" {2,}", " ", regex=True).str.strip()` |
| `normalize_boolean_case` | `YES→Yes`, `NO→No` | `s.replace({"YES": "Yes", "NO": "No"})` |
| `normalize_uom_longform` | `ampere→A`, `volt→V` и т.д. | dict lookup + str.replace |

---

## 5. Итоговая сводная таблица всех рекомендаций

### Изменения существующих правил

| rule_code | Действие | Суть изменения |
|---|---|---|
| `NO_INVALID_CHARS` | Обновить | Расширить `rule_expression` на `[<>{}|^]`, сменить fix на `encoding_repair` |
| `SECE_SEMICOLON_DELIMITER` | Обновить | `is_builtin=false`, severity=`Info` — избыточно для текущего источника |
| `DESC_NO_DOUBLE_SPACE` | Удалить | Заменить на `MULTIPLE_SPACES_IN_TEXT` (scope=common) |
| `PSEUDO_NULL_NA_FORMAT` | Обновить | Расширить `rule_expression` + новая `fix_expression = normalize_na` |
| `DECIMAL_DOT_SEPARATOR` | Обновить | Добавить `fix_expression = 'replace "," "."'`, `is_builtin=true` |
| `VOID_DELETED_EXCLUDED_FROM_XREF` | Обновить | Расширить description и rule_expression на `doc_status = CAN` |
| `DISCIPLINE_FK_RESOLVED` | Исправить | Опечатка: второй `discipline_code_raw not_null` → `discipline_id is_null` |

### Правила к удалению (дубли)

| rule_code | Причина |
|---|---|
| `PROCESS_UNIT_MANDATORY` | Дублирует `PROCESS_UNIT_NOT_NULL` |
| `AREA_CODE_EXPECTED` | Дублирует `AREA_CODE_NOT_NULL` |
| `PO_CODE_NOT_VOID` | Дублирует `PO_CODE_NOT_VOID_SUFFIX` |
| `TAG_MIN_ONE_DOCUMENT` | Дублирует `TAG_MIN_DOC_LINK` |

### Новые правила (из Power Query gap)

| rule_code | scope | tier | check_type | Источник |
|---|---|---|---|---|
| `SIGNAL_TAG_NO_DUPLICATES` | tag | L0 | aggregate | MTR PQ filter |
| `PARENT_TAG_UNSET_VALUE` | tag | L1 | dsl | MTR PQ replace |
| `DESC_EM_DASH_REPLACE` | common | L1 | dsl | MTR PQ bad symbols |
| `DESC_MM2_FORMAT` | common | L1 | dsl | MTR PQ bad symbols |
| `BOOLEAN_VALUE_CASING` | common | L1 | dsl | TagProperties PQ |
| `NUMERIC_PSEUDO_NULL_VARIANT` | common | L2 | dsl | TagProperties PQ (999999) |
| `UOM_LONGFORM_NORMALIZE` | common | L1 | dsl | TagProperties PQ UoM |
| `PROP_VALUE_UNSET` | common | L1 | dsl | TagProperties PQ filter |
| `UNICODE_HYPHEN_REPLACE` | common | L1 | dsl | Tag-Doc PQ |
| `MULTIPLE_SPACES_IN_TEXT` | common | L1 | dsl | Замена DESC_NO_DOUBLE_SPACE |

### Новые fix-операции для движка (4 шт.)

| fix_expression | Добавить в `export_validation.py` |
|---|---|
| `normalize_na` | str.replace regex NA-variants → `"NA"` |
| `normalize_spaces` | `re.sub(r" {2,}", " ", s).strip()` |
| `normalize_boolean_case` | `YES→Yes`, `NO→No` dict replace |
| `normalize_uom_longform` | dict: ampere→A, volt→V, pascal→Pa, hertz→Hz, kilowatt→kW |

---

## 6. Приоритет внедрения

```
P1 — Немедленно (правки без изменения кода):
  - Удалить 4 дублирующих правила
  - Исправить опечатку в DISCIPLINE_FK_RESOLVED
  - Обновить SECE_SEMICOLON_DELIMITER (is_builtin=false)
  - Обновить DECIMAL_DOT_SEPARATOR (добавить fix)

P2 — Следующий sprint (минимальные изменения кода):
  - Добавить fix-операции normalize_na, normalize_spaces в движок
  - Обновить PSEUDO_NULL_NA_FORMAT, DESC_NO_DOUBLE_SPACE → MULTIPLE_SPACES_IN_TEXT
  - Добавить новые DSL-правила из PQ gap (9 правил, check_type=dsl)

P3 — Отложено (новые executor-типы):
  - SIGNAL_TAG_NO_DUPLICATES (aggregate)
  - Topology rules (cross_table, aggregate, graph)
```

---

*Generated: 2026-03-13 | Jackdaw EDW — validation rules gap analysis vs Power Query logic*
