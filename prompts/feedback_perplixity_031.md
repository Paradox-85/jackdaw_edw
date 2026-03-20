<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# проанализируй новую версию UI и давай подготовим новую порцию замечаний к UI, пожалуйста проаналазируй код и дай замечания и комментарии и рекомендации для claude code как ему внести эти изменения. задача - архитектурный и технический анализ и code review, не переписывание кода но формирование списка комментариев и замечаний

1. я обратил внимание что при переходе на master tag register время загрузки огромно, я не знаю как это оптимизировать, возможно стоит подготовить view на стороне postgres и открывать его - это увеличит скорость так как мы не будем вызывать тяжелый запрос из кода
2. на вложенной картинке ты видишь выделенное красным область - эти пункты меню я не знаю откуда они взялись и я хочу от них избавиться. при кликах на них открывается пустая страница
3. на странице Tag history я вижу список тегов за последние 7 дней, но они все красного цвета - почмеу не срабатывает схема о которой мы говорили ранее (разные статусы разными цветами). Также там вижу странную статистику, тегов со статусом no changes всего 1887 за последние 7 дней а всего тегов со всеми статусами - 2335, это явно ошибка потому что всего у меня порядка 23000 тегов в таблице.
4. в EIS management секции мне не нужны Individual reports, вообще убери, мне нужна выгрузка через flows но при этом я хочу скачивать файлы на компьютер. можно как то запустить flow экспортировать в папку экспорта и оттуда подгрузить в ui где я смогу их скачать в браузере такое возможно реализовать?
5. зачем мы пишем в базу sync_run_stats любую статитсику по export задачам - это же просто экспорт, нам не нужно это, давай уберем. оставим только импорт и только tag, document и property values, остальное не интересно

Полной картины достаточно. Формирую замечания.

***

## Code Review — Jackdaw EDW UI v0.3.0


***

### Замечание 1 | Фантомные пункты меню в sidebar

**Причина:** В `app.py`  файлы скрытых страниц переименованы в `_llm_chat`, `_crs_assistant`, `_etl_import`, `_services` — и при этом **всё равно импортируются**:[^1]

```python
from ui.pages import _llm_chat as llm_chat  # ← модуль импортируется
```

Streamlit при использовании `st.navigation()` или папки `pages/` автоматически регистрирует все файлы в директории `ui/pages/` как страницы, включая файлы с префиксом `_` если они там лежат физически. Фантомные пункты берутся именно оттуда — Streamlit сканирует директорию независимо от `app.py`.

**Инструкция для Claude Code:**

1. Проверить содержимое `ui/pages/` — убедиться что файлы `_llm_chat.py`, `_crs_assistant.py`, `_etl_import.py`, `_services.py` физически находятся в директории `pages/`.
2. Переместить их в отдельную директорию `ui/_hidden/` (вне `pages/`):

```
ui/_hidden/__init__.py  (пустой)
ui/_hidden/llm_chat.py
ui/_hidden/crs_assistant.py
ui/_hidden/etl_import.py
ui/_hidden/services.py
```

3. Обновить импорты в `app.py`:

```python
from ui._hidden import llm_chat, crs_assistant, etl_import, services
```

4. Убрать импорты скрытых модулей из `app.py` полностью — они нигде не используются в коде навигации, их хранение в `app.py` только создаёт путаницу. Оставить только комментарий: `# llm_chat, etl_import, services — moved to ui/_hidden/, Phase 2/3`.

***

### Замечание 2 | Tag Register — медленная загрузка (23 000 тегов)

**Анализ кода `tag_register.py`:**[^2]

Запрос в `_load_tags()` содержит **коррелированный подзапрос** на каждую строку:

```sql
(SELECT COUNT(*) FROM mapping.tag_document m
 JOIN project_core.document doc ON doc.id = m.document_id
 WHERE m.tag_id = t.id ...) AS "Tag-Doc Count"
```

При 23 000 тегов PostgreSQL выполняет этот подзапрос **23 000 раз**. Это главная причина медленной загрузки. Дополнительно — 5 LEFT JOIN к reference-таблицам и сортировка по `t.tag_name` без гарантии индекса.

`@st.cache_data(ttl=60)` присутствует, но **только после первой загрузки**. Первый вход всегда медленный.

**Рекомендации — три уровня, применять по порядку:**

**Уровень 1 — PostgreSQL: создать materialized view (рекомендуется)**

Инструкция для Claude Code: добавить SQL-миграцию (новый файл `sql/migrations/V???__create_mv_tag_register.sql`):

```sql
CREATE MATERIALIZED VIEW reporting.mv_tag_register AS
SELECT
    t.id                                AS tag_id,
    t.tag_name,
    t.description,
    design_co.name                      AS owner,
    t.tag_status,
    po.name                             AS po_number,
    pkg.code                            AS package,
    c.name                              AS class_name,
    t.mc_package_code,
    a.code                              AS area,
    u.code                              AS process_unit,
    pt.tag_name                         AS parent_tag,
    d.code                              AS discipline_code,
    t.ex_class,
    t.serial_no,
    COUNT(m.id) FILTER (
        WHERE m.mapping_status = 'Active'
          AND doc.mdr_flag = TRUE
          AND doc.status != 'CAN'
          AND doc.object_status = 'Active'
    )                                   AS tag_doc_count,
    t.sync_status,
    t.sync_timestamp
FROM project_core.tag t
LEFT JOIN ontology_core.class c             ON c.id = t.class_id
LEFT JOIN reference_core.area a             ON a.id = t.area_id
LEFT JOIN reference_core.process_unit u     ON u.id = t.process_unit_id
LEFT JOIN reference_core.discipline d       ON d.id = t.discipline_id
LEFT JOIN project_core.tag pt               ON pt.id = t.parent_tag_id
LEFT JOIN reference_core.company design_co  ON design_co.id = t.design_company_id
LEFT JOIN reference_core.purchase_order po  ON po.id = t.po_id
LEFT JOIN reference_core.po_package pkg     ON pkg.id = po.package_id
LEFT JOIN mapping.tag_document m            ON m.tag_id = t.id
LEFT JOIN project_core.document doc         ON doc.id = m.document_id
WHERE t.object_status = 'Active'
GROUP BY t.id, design_co.name, po.name, pkg.code, c.name,
         a.code, u.code, pt.tag_name, d.code
ORDER BY t.tag_name;

CREATE UNIQUE INDEX ON reporting.mv_tag_register (tag_id);
CREATE INDEX ON reporting.mv_tag_register (tag_name);
```

Рефреш view добавить в Prefect sync flow (после завершения импорта тегов):

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_tag_register;
```

В `tag_register.py` заменить `_load_tags()` SQL на `SELECT * FROM reporting.mv_tag_register`.

**Уровень 2 — Python: заменить коррелированный подзапрос на агрегирующий JOIN**

Если materialized view не создаётся сейчас, минимальное исправление в `_load_tags()` — заменить scalar subquery на `LEFT JOIN` с агрегатом:

```sql
LEFT JOIN (
    SELECT m.tag_id, COUNT(*) AS cnt
    FROM mapping.tag_document m
    JOIN project_core.document doc ON doc.id = m.document_id
    WHERE m.mapping_status = 'Active'
      AND doc.mdr_flag = TRUE
      AND doc.status != 'CAN'
      AND doc.object_status = 'Active'
    GROUP BY m.tag_id
) td_cnt ON td_cnt.tag_id = t.id
```

Добавить `COALESCE(td_cnt.cnt, 0) AS "Tag-Doc Count"` в SELECT. Это убирает N+1 подзапрос.

**Уровень 3 — UI: увеличить TTL кэша**

Поменять `@st.cache_data(ttl=60)` → `@st.cache_data(ttl=300)` для `_load_tags()`. Данные тегов меняются только при синхронизации, обновление каждые 60 секунд избыточно.

***

### Замечание 3 | Tag History — все строки красные + неверная статистика

**Причина 1 — все строки красные:**

В `tag_history.py`  применяются **два стиля одновременно** и они конфликтуют:[^3]

```python
styled = df.style.applymap(
    lambda v: f"color:{_STATUS_CLR.get(v, '#C9D1D9')};font-weight:500",
    subset=["Status"],
)
if "Name Changed" in df.columns:
    styled = styled.apply(_highlight_name_change, axis=1)  # ← перезаписывает всю строку
```

Функция `_highlight_name_change` возвращает `["color: #F85149"] * len(row)` для строк где `"Name Changed" == "NO"`. Это перекрашивает **все колонки** красным, включая Status. Поскольку у большинства тегов `"Name Changed" == "NO"` (имя не менялось) — все строки становятся красными.

**Логика была написана неверно:** "NO" означает "нет изменений имени", то есть это нормальная строка — она не должна подсвечиваться. Красным должно быть "YES" (имя изменилось).

**Инструкция для Claude Code:** Исправить функцию `_highlight_name_change`:

```python
def _highlight_name_change(row: pd.Series):
    # YES = name changed → highlight red
    if row.get("Name Changed") == "YES":
        return ["color: #F85149; font-weight: 600"] * len(row)
    return [""] * len(row)
```

И убрать конфликт — `_highlight_name_change` должна применяться только к колонке `"Name Changed"`, не ко всей строке:

```python
if "Name Changed" in df.columns:
    styled = styled.applymap(
        lambda v: "color: #F85149; font-weight: 600" if v == "YES" else "color: #3FB950",
        subset=["Name Changed"],
    )
```

**Причина 2 — неверная статистика (2335 записей вместо 23 000):**

В `tag_history.py`  фильтр периода по умолчанию — `"Last 7 days"` (index=1). Запрос к `audit_core.tag_status_history` возвращает только записи за последние 7 дней, а не весь реестр. 2335 записей — это количество тегов затронутых синхронизацией за 7 дней, что корректно. Это не ошибка — это ожидаемое поведение фильтра.[^3]

Однако Timeline chart вверху `tag_history.py` загружает **все данные без фильтра периода**:

```python
df_chart = db_read("SELECT DATE(sync_timestamp) ... FROM audit_core.tag_status_history GROUP BY ...")
```

Это отдельный запрос без WHERE — он всегда показывает полную историю независимо от выбранного периода. Это несогласованность: chart и таблица показывают разные временные диапазоны.

**Инструкция для Claude Code:**

1. Добавить caption под таблицей: `st.caption(f"Period: {period} — showing {len(df):,} history records (not total tag count)")` — убрать визуальную путаницу.
2. Синхронизировать Timeline chart с выбранным фильтром периода — передавать `since` из `periods[period]` в запрос chart.
3. Сортировку `sort_values("Name Changed", ascending=True)` удалить — она бессмысленна теперь, когда "NO" не означает аномалию.

***

### Замечание 4 | EIS Management — убрать Individual Export, добавить download после flow

**Анализ:** В `eis_management.py`  секция "Individual Export" реализует прямой DB-запрос (`_quick_query`) в обход Prefect. Это именно то что нужно убрать.[^4]

**Архитектура "запустить flow → скачать результат"** — реализуема и вот как:

Prefect flow уже пишет файл в `EIS_EXPORT_DIR` (`/mnt/shared-data/...`). Эта директория смонтирована в контейнер UI как volume (проверить `docker-compose.yml` — `./data → /mnt/shared-data`). Значит UI может читать эти файлы через `pathlib.Path`.

**Паттерн: trigger → poll → download**

```
[User] → ▶ Run Export → trigger_deployment() → flow_run_id
         ← "Scheduled" + flow_run_id
         
[User] → ⟳ Check Status → prefect_get(f"/flow-runs/{flow_run_id}") 
         ← state: RUNNING / COMPLETED / FAILED

[COMPLETED] → scan EIS_EXPORT_DIR for file matching file_tmpl pattern
            → st.download_button() с данными файла
```

**Инструкция для Claude Code:**

1. **Убрать секцию "Individual Export"** целиком из `eis_management.py` — удалить `st.radio` выбора export, `st.selectbox` формата, `st.radio` destination, функции `_quick_query()` и `_download()`.
2. **Оставить только:**
    - Секцию "Active Export Deployments" (список из Prefect) — переименовать в "Export Flows"
    - Секцию "Full EIS Package Export" — переименовать в "Run Export"
    - Добавить возможность выбора: один flow или все
3. **Добавить секцию "Download Exported Files":**
```python
section("Download Exported Files")
export_path = Path(EIS_EXPORT_DIR)
if export_path.exists():
    files = sorted(export_path.glob("*.CSV"), key=lambda f: f.stat().st_mtime, reverse=True)
    files += sorted(export_path.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if files:
        for fpath in files[:20]:  # последние 20 файлов
            col_name, col_dl = st.columns([4, 1])
            col_name.caption(f"`{fpath.name}` · {fpath.stat().st_size // 1024} KB · "
                             f"{datetime.fromtimestamp(fpath.stat().st_mtime):%Y-%m-%d %H:%M}")
            col_dl.download_button(
                "⬇",
                data=fpath.read_bytes(),
                file_name=fpath.name,
                key=f"dl_{fpath.name}",
            )
    else:
        st.caption("No exported files found in export directory.")
else:
    st.warning(f"Export directory not mounted: `{EIS_EXPORT_DIR}`")
```

4. **Проверить в `docker-compose.yml`** что `EIS_EXPORT_DIR` смонтирован в jackdaw-ui сервис:
```yaml
jackdaw-ui:
  volumes:
    - /mnt/shared-data/ram-user/Jackdaw/EIS_Exports:/mnt/shared-data/ram-user/Jackdaw/EIS_Exports:ro
```

Флаг `:ro` (read-only) — UI только читает, не пишет.

***

### Замечание 5 | sync_run_stats — убрать запись для export flows

**Анализ:** `sync_run_stats` в Prefect flow пишется для **всех** flow-runs включая export. Это backend-задача (Prefect flows), не UI.

**Инструкция для Claude Code:** Это изменение НЕ в UI-коде. Сформировать задачу для Prefect-кода:

В файлах export flows (в `flows/` директории) найти и удалить все вызовы вида:

```python
# УДАЛИТЬ из export flows:
db.execute(
    "INSERT INTO audit_core.sync_run_stats (...) VALUES (...)",
    ...
)
```

Или аналогичный `log_sync_run()` / `record_stats()` helper вызов.

Оставить запись в `sync_run_stats` **только** для:

- import_tag_data_deploy
- import_doc_data_deploy
- import_prop_data_deploy

В `home.py` в секции "Last Sync Run Statistics" добавить фильтр чтобы исключить export-записи если они ещё присутствуют:

```sql
WHERE target_table IN (
    'project_core.tag',
    'project_core.document', 
    'project_core.property_value'
)
```

Это defensive coding — UI не упадёт если backend ещё не очищен.

***

### Дополнительное замечание | Tag History — `m.mdr_flag` vs `doc.mdr_flag`

В `_load_tags()` в `tag_register.py`:[^2]

```python
AND doc.mdr_flag = TRUE   -- ← флаг на таблице document
```

В `_load_documents()` в том же файле:

```python
AND doc.mdr_flag = TRUE   -- ← то же
```

Но в `eis_management.py`  в `_quick_query` этого условия нет вообще. Убедиться что схема `mdr_flag` консистентна: это поле `mapping.tag_document.mdr_flag` или `project_core.document.mdr_flag`. Если оно на junction table `mapping.tag_document` — исправить `doc.mdr_flag` → `m.mdr_flag` во всех запросах. Это **потенциальный логический баг** если поля на разных таблицах.[^4]

**Инструкция:** Claude Code должен выполнить:

```sql
-- В PostgreSQL проверить где реально живёт mdr_flag:
SELECT column_name, table_name, table_schema
FROM information_schema.columns
WHERE column_name = 'mdr_flag';
```

И исправить все запросы согласно результату.
<span style="display:none">[^10][^11][^12][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: app-2.py

[^2]: tag_register-12.py

[^3]: tag_history-11.py

[^4]: eis_management-6.py

[^5]: image.jpg

[^6]: home-4.py

[^7]: common-3.py

[^8]: version-5.py

[^9]: feedback-7.py

[^10]: reports-10.py

[^11]: help-8.py

[^12]: home-9.py

