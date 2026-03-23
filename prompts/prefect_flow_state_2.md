<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# вот модуль common, проверь его

Нашёл корневую причину. Вот она:

## Проблема найдена: `get_flow_run_status` использует `prefect_get`, а не `prefect_post`

```python
# common.py — текущий код:
def prefect_get(path: str):
    try:
        r = httpx.get(f"{PREFECT_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None  # ← глотает ошибку молча, возвращает None

def get_flow_run_status(run_id: str) -> dict | None:
    return prefect_get(f"/flow-runs/{run_id}")
```

**Два критических бага:**

### Баг 1 — `prefect_get` timeout слишком короткий (5 сек)

Когда flow завершается, Prefect Server под нагрузкой может отвечать медленнее. При timeout → `Exception` → возвращает `None` → `_poll_run()` игнорирует ответ → state не обновляется → вечный RUNNING.

### Баг 2 — `prefect_get` не логирует ошибки

Если API недоступен или возвращает 4xx/5xx — ошибка полностью скрыта. В `prefect_post` хотя бы возвращается `{"error": str(exc)}`, а здесь просто `None`.

### Баг 3 — структура ответа Prefect API для `/flow-runs/{id}`

Prefect возвращает `state_type` и `state_name` **на верхнем уровне**, а не внутри объекта `state`:

```json
{
  "id": "...",
  "name": "...",
  "state_type": "COMPLETED",      ← верхний уровень
  "state_name": "Completed",      ← верхний уровень
  "state": {
    "type": "COMPLETED",
    "name": "Completed"
  }
}
```


***

## Исправление `common.py`

```python
def prefect_get(path: str, timeout: int = 10):
    """GET request to Prefect API. Returns parsed JSON or None on failure."""
    try:
        r = httpx.get(f"{PREFECT_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except httpx.TimeoutException:
        # Отдельная обработка timeout — не скрывать молча
        return {"error": f"Timeout reaching Prefect API: {path}"}
    except Exception as exc:
        return {"error": str(exc)}


def get_flow_run_status(run_id: str) -> dict | None:
    """
    Return Prefect flow run dict for a single run ID, or None on failure.
    Normalises state fields to always expose top-level state_type / state_name.
    """
    data = prefect_get(f"/flow-runs/{run_id}", timeout=10)
    if not data or "error" in data:
        return None

    # Нормализация: гарантировать наличие state объекта
    # Prefect возвращает state_type/state_name на верхнем уровне
    if "state" not in data or not data["state"]:
        state_type = data.get("state_type", "UNKNOWN")
        state_name = data.get("state_name", state_type)
        data["state"] = {"type": state_type, "name": state_name}
    else:
        # Дополнить state объект если type отсутствует
        state_obj = data["state"]
        if not state_obj.get("type"):
            state_obj["type"] = data.get("state_type", "UNKNOWN")
        if not state_obj.get("name"):
            state_obj["name"] = data.get("state_name", state_obj["type"])

    return data
```


## Соответствующее упрощение `_poll_run()` в `eis_management.py`

После исправления `common.py` — `_poll_run()` можно упростить, убрав дублирующую нормализацию:

```python
def _poll_run() -> dict | None:
    run = st.session_state.get("export_run")
    if not run:
        return None
    if run.get("run_id") and run["state"] not in _TERMINAL_STATES:
        info = get_flow_run_status(run["run_id"])
        if info:
            state_obj  = info.get("state") or {}
            state_type = state_obj.get("type", run["state"]).upper()  # .upper() критично
            state_name = state_obj.get("name", state_type)
            run = {**run, "state": state_type, "state_name": state_name}
            st.session_state["export_run"] = run
    return run
```


***

## Итог найденных проблем

| Баг | Файл | Причина | Исправление |
| :-- | :-- | :-- | :-- |
| `prefect_get` timeout=5 | `common.py` | Сеть медленная → `None` → state не обновляется | `timeout=10` + отдельный `TimeoutException` |
| Ошибки скрываются | `common.py` | `except Exception: return None` | Возвращать `{"error": ...}` как в `prefect_post` |
| `state` может отсутствовать | `common.py` | Prefect кладёт `state_type` на верхний уровень | Нормализация в `get_flow_run_status` |
| `.upper()` не применяется | `eis_management.py` | `"Completed" not in _TERMINAL_STATES` | `.upper()` при чтении `state_type` |

<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: common.py

