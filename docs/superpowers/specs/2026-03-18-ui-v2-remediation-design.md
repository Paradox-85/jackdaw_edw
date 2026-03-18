# UI v2 Remediation — Design Spec
**Date:** 2026-03-18
**Scope:** Jackdaw EDW Control Center — `ui/` module
**Approach:** Sequential (DB schema first → bugs → features → design)

---

## Context

UI v2 was released (commit `9400e42`) with several known issues identified during user testing and documented in `docs/ui_review_and_remediation_plan.md`. This spec covers the agreed remediation scope for the next iteration: auth system, ETL audit bug, navigation fix, reports diagnostics, help page, feedback form, Material Design CSS, and home metrics delta.

---

## 1. New Schema: `app_core`

**Purpose:** Separate schema for application-level service data (auth, feedback, future metadata). Keeps `audit_core` clean for ETL audit data.

### Tables

```sql
-- Migration: migration_008_app_core.sql

CREATE SCHEMA IF NOT EXISTS app_core;

CREATE TABLE app_core.ui_user (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,           -- bcrypt hash, never plaintext
    role          TEXT NOT NULL DEFAULT 'viewer'
                  CHECK (role IN ('viewer', 'admin')),
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login    TIMESTAMPTZ
);

CREATE TABLE app_core.ui_feedback (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES app_core.ui_user(id) ON DELETE SET NULL,
    username      TEXT,                    -- denormalized for display
    feedback_type TEXT NOT NULL
                  CHECK (feedback_type IN ('Bug', 'Enhancement', 'Question')),
    title         TEXT NOT NULL,
    body          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'Open'
                  CHECK (status IN ('Open', 'In Progress', 'Done', 'Rejected')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed: default admin user (password must be changed on first login)
-- Generate hash before running migration:
--   python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt(rounds=12)).decode())"
-- Replace <BCRYPT_HASH_HERE> with the generated output.
INSERT INTO app_core.ui_user (username, password_hash, role)
VALUES ('admin', '<BCRYPT_HASH_HERE>', 'admin')
ON CONFLICT (username) DO NOTHING;
```

**Dependencies:** `bcrypt` Python package added to `requirements.txt`.
**Migration file:** `sql/migrations/migration_008_app_core.sql`
**Schema.sql:** Updated in same commit.

---

## 2. Login System

**Files affected:** `ui/app.py`, `ui/common.py`, `ui/pages/` (no page changes needed)

### Flow

```
App starts → check session_state["authenticated"]
  → False: render login form only, st.stop()
  → True:  render sidebar + current page normally
```

### Implementation

**`ui/common.py`** additions:
- Remove `ADMIN_PASSWORD` env var (replaced by DB auth)
- Add `verify_password(username, password) -> tuple[bool, str]` — queries `app_core.ui_user`, verifies bcrypt hash, returns `(success, role)`
- Add `get_current_user() -> dict | None` — returns `session_state.get("user")` dict

**`ui/app.py`** changes:
- Add `render_login()` function at top of file: `st.text_input(username)` + `st.text_input(password, type="password")` + Login button
- Login gate before sidebar: `if not session_state.get("authenticated"): render_login(); st.stop()`
- On successful login: `session_state["authenticated"] = True`, `session_state["role"] = role`, `session_state["user"] = {id, username, role}`, `st.rerun()`
- Remove `ADMIN_PASSWORD` env var and its import from `common.py`
- Update `require_admin()` in `common.py`: remove password input/button logic, keep only `if is_admin(): return` + `st.warning()` + `st.stop()`. Role is now always set via login gate, not inline password entry.
- Admin pages in sidebar shown only when `is_admin()` — already implemented

### `VIEWER_PAGES` update
Add `Help` and `Feedback` to viewer pages (see sections 5 and 6).

---

## 3. ETL Audit Bug Fix

**File:** `etl/tasks/export_pipeline.py`

### Bug 1: `_log_audit_end()` — wrong field
Current code writes `row_count` to `count_unchanged`, breaking the semantic meaning of all count columns.

**Resolution:** Add `count_exported` column to `audit_core.sync_run_stats` via `migration_009_add_count_exported.sql`. Write `row_count` to the new column; leave `count_unchanged` for actual unchanged-record counts from sync flows.

This requires a `/schema-change` workflow: migration SQL + `sql/schema/schema.sql` update in the same commit.

```sql
-- migration_009_add_count_exported.sql
ALTER TABLE audit_core.sync_run_stats
    ADD COLUMN IF NOT EXISTS count_exported INTEGER DEFAULT 0;
```

```python
# _log_audit_end() fix:
conn.execute(text("""
    UPDATE audit_core.sync_run_stats SET
        end_time       = :et,
        count_exported = :rc,   -- row_count of exported rows
        count_errors   = :er
    WHERE run_id = :rid
"""), {"et": ..., "rc": row_count, "er": count_errors, "rid": run_id})
```

### Bug 2: `_log_audit_start()` — hardcoded target_table
Current: `"tbl": "project_core.tag"` for all export flows.
Fix: add `target_table: str` parameter, resolve from explicit mapping dict (not `f"project_core.{scope}"` — scopes like `area`, `process_unit` live in `reference_core`, not `project_core`).

```python
_SCOPE_TO_TABLE: dict[str, str] = {
    "tag":                "project_core.tag",
    "equipment":          "project_core.equipment",
    "tag_property":       "project_core.property_value",
    "equipment_property": "project_core.property_value",
    "area":               "reference_core.area",
    "process_unit":       "reference_core.process_unit",
    "purchase_order":     "reference_core.purchase_order",
    "model_part":         "reference_core.model_part",
    "tag_class_property": "ontology_core.class_property",
}

def _log_audit_start(run_id: str, source_file: str, target_table: str) -> None:
    ...

# In run_export_pipeline():
target_table = _SCOPE_TO_TABLE.get(scope, f"project_core.{scope}")
_log_audit_start(run_id, source_file, target_table)
```

---

## 4. Navigation Fix (Double Click)

**File:** `ui/app.py`

### Root Cause
`st.radio` fires rerun on selection, but `render()` is called in the same cycle using `selected` directly. On pages that have nav buttons (Home cards), an extra `st.rerun()` causes a second cycle.

### Fix
Use `on_change` callback pattern. `ALL_PAGES` must be defined **before** the sidebar block so it is accessible both in the callback closure and in the render call after the sidebar.

```python
# Define ALL_PAGES before sidebar block (module level or top of main block)
ALL_PAGES = {**VIEWER_PAGES, **(ADMIN_PAGES if is_admin() else {})}

if "page" not in st.session_state or st.session_state["page"] not in ALL_PAGES:
    st.session_state["page"] = "🏠  Home"

def _on_nav_change() -> None:
    st.session_state["page"] = st.session_state["sidebar_nav"]

with st.sidebar:
    st.radio(
        "Navigation",
        list(ALL_PAGES.keys()),
        index=list(ALL_PAGES.keys()).index(st.session_state["page"]),
        key="sidebar_nav",
        on_change=_on_nav_change,
        label_visibility="collapsed",
    )
    # ... rest of sidebar

# Render OUTSIDE sidebar block, using session_state (not local variable)
ALL_PAGES[st.session_state["page"]].render()
```

Remove any `st.rerun()` calls from Home page navigation buttons if present.

---

## 5. Reports Diagnostics

**File:** `ui/pages/reports.py`

### Changes
Wrap each `_run_and_show()` call in `try/except`:

```python
def _run_and_show(sql, params, name, fmt):
    try:
        with st.spinner(f"Loading {name}..."):
            df = db_read(sql, params)
        # ... existing render logic
    except Exception as e:
        st.error(f"Report unavailable: {name}")
        if is_admin():
            with st.expander("🔍 Debug info (admin only)"):
                st.code(sql, language="sql")
                st.exception(e)
```

Admin sees full SQL + stack trace. Viewer sees generic error message only.

---

## 6. Help Page

**New files:** `ui/pages/help.py`, `docs/help.md`

### `ui/pages/help.py`

```python
from pathlib import Path
import streamlit as st
from ui.common import section

def render():
    section("Help & Guidelines")
    help_path = Path(__file__).parent.parent.parent / "docs" / "help.md"
    if help_path.exists():
        st.markdown(help_path.read_text(encoding="utf-8"))
    else:
        st.warning("Help file not found: docs/help.md")
```

### `docs/help.md` structure (stub)

```markdown
# Jackdaw EDW — User Guide

## Overview
<!-- TODO: System description -->

## Reports
<!-- TODO: How to use built-in reports, parameters -->

## Tag History
<!-- TODO: SCD audit trail explanation -->

## EIS Export
<!-- TODO: Revision naming, flow vs direct download -->

## FAQ
<!-- TODO: Common questions -->
```

Add `"❓  Help": help` to `VIEWER_PAGES` in `app.py`.

---

## 7. Feedback Form

**New file:** `ui/pages/feedback.py`

### Viewer view: Submit form

```python
def render():
    section("Feedback & Enhancement Requests")

    with st.form("feedback_form"):
        ftype  = st.selectbox("Type", ["Bug", "Enhancement", "Question"])
        title  = st.text_input("Title")
        body   = st.text_area("Description", height=150)
        submit = st.form_submit_button("Submit")

    if submit and title and body:
        user = get_current_user()
        db_write("""
            INSERT INTO app_core.ui_feedback
                (user_id, username, feedback_type, title, body)
            VALUES (:uid, :uname, :ftype, :title, :body)
        """, {"uid": user["id"], "uname": user["username"],
              "ftype": ftype, "title": title, "body": body})
        st.success("Feedback submitted. Thank you!")
```

### Admin view: Submissions table

Admin additionally sees all submissions below the form:

```python
if is_admin():
    section("All Submissions")
    status_filter = st.selectbox("Status", ["All", "Open", "In Progress", "Done", "Rejected"])
    df = db_read("SELECT ... FROM app_core.ui_feedback ...", admin=True)
    st.dataframe(df)
```

**New helper in `common.py`:** `db_write(sql, params)` — always uses admin engine for INSERT/UPDATE (viewer role has no INSERT rights on `app_core`). Returns `True` on success, `False` on error. Wraps in `try/except` with `st.error()`.

**`last_login` update:** `verify_password()` must UPDATE `app_core.ui_user SET last_login = now()` on successful authentication before returning `(True, role)`.

Add `"💬  Feedback": feedback` to `VIEWER_PAGES` in `app.py`.

---

## 8. CSS Material Design

**Files:** `ui/common.py` (GLOBAL_CSS), `.streamlit/config.toml`

### `config.toml` changes

```toml
[theme]
primaryColor = "#1976D2"        # MUI Blue (was #238636 GitHub green)
backgroundColor = "#0D1117"
secondaryBackgroundColor = "#161B22"
textColor = "#E6EDF3"
font = "sans serif"             # was "monospace"
```

### `GLOBAL_CSS` additions/changes

```css
/* Google Fonts — Roboto (MUI standard). Falls back to system sans-serif if CDN unreachable. */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

body, p, div { font-family: 'Roboto', 'Segoe UI', Arial, sans-serif !important; }

/* MUI elevation on metric cards */
[data-testid="metric-container"] {
    box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2) !important;
    border-radius: 4px !important;    /* MUI: 4px not 6px */
}

/* Monospace only for log/code */
.log-box { font-family: 'SF Mono','Fira Code',monospace !important; }
```

Primary color change propagates to all `st.button`, `st.radio`, progress bars automatically via `config.toml`.

---

## 9. Home Metrics with Delta

**File:** `ui/pages/home.py`

### New query: previous sync KPIs

Find the second-to-last completed sync run timestamp via CTE, then count tags as of that point using `tag_status_history`:

```sql
WITH runs AS (
    SELECT start_time,
           ROW_NUMBER() OVER (ORDER BY start_time DESC) AS rn
    FROM audit_core.sync_run_stats
    WHERE end_time IS NOT NULL
      AND target_table = 'project_core.tag'
),
prev_run AS (
    SELECT start_time FROM runs WHERE rn = 2  -- second-to-last run
)
SELECT COUNT(*) AS prev_active_tags
FROM project_core.tag t
WHERE t.sync_timestamp < (SELECT start_time FROM prev_run)
  AND t.sync_status != 'Deleted';
```

If `prev_run` returns no rows (only one run ever), delta = `None` (not shown).

### Delta rendering

```python
st.metric(
    label="Active Tags",
    value=f"{current_tags:,}",
    delta=current_tags - previous_tags,
    delta_color="normal"   # green = up, red = down
)
```

If previous data unavailable (first run) — `delta=None` (no delta shown).

---

## Implementation Order

| Step | Scope | Files |
|------|-------|-------|
| 1 | DB migration `app_core` + seed admin user | `sql/migrations/migration_008_app_core.sql`, `sql/schema/schema.sql` |
| 2 | DB migration `count_exported` column | `sql/migrations/migration_009_add_count_exported.sql`, `sql/schema/schema.sql` |
| 3 | ETL audit bug fix | `etl/tasks/export_pipeline.py` |
| 4 | `bcrypt` added to deps | `requirements.txt` (or `docker/jackdaw-edw_docker-compose.yml`) |
| 5 | `common.py` — auth helpers (`verify_password`, `get_current_user`, `db_write`), remove `ADMIN_PASSWORD`, update `require_admin()` | `ui/common.py` |
| 6 | Login gate in `app.py`, move `ALL_PAGES` before sidebar | `ui/app.py` |
| 7 | Navigation fix (`on_change` callback) | `ui/app.py` |
| 8 | Reports diagnostics | `ui/pages/reports.py` |
| 9 | Help page | `ui/pages/help.py`, `docs/help.md` |
| 10 | Feedback page | `ui/pages/feedback.py` |
| 11 | CSS + config | `ui/common.py`, `.streamlit/config.toml` |
| 12 | Home delta metrics | `ui/pages/home.py` |
| 13 | Register new pages (`help`, `feedback`) in `app.py` | `ui/app.py` |

---

## Verification

1. **Auth:** Create user via SQL, login with correct/wrong password, verify role gating
2. **ETL audit:** Run export flow, check `audit_core.sync_run_stats` — `count_created` = row count, `target_table` matches scope
3. **Navigation:** Single click navigates immediately, no second click needed
4. **Reports:** Break a report SQL intentionally, verify admin sees debug info, viewer sees generic error
5. **Help page:** `docs/help.md` renders with headings, tables, code blocks
6. **Feedback:** Submit form as viewer, verify row in `app_core.ui_feedback`, verify admin sees it
7. **CSS:** `primaryColor` = `#1976D2` visible on buttons/radio; Roboto font loaded
8. **Delta metrics:** Run two syncs with different tag counts, verify delta appears on Home
