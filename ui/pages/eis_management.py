"""
ui/pages/eis_management.py — EIS Management. ADMIN ONLY.

Sections:
  1. Export Flows — live list from Prefect API (export-* pattern)
  2. Run Export — set revision, trigger EIS Full Package Export via Prefect
  3. Export Progress — real-time polling of the triggered Prefect flow run
  4. Download Exported Files — browse and download files from EIS_EXPORT_DIR
"""
from __future__ import annotations
import io as _io
import re
import subprocess
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from ui.common import (
    CRS_DATA_DIR, EIS_EXPORT_DIR, db_read, db_write,
    get_flow_run_status, is_admin, log, render_log,
    section, trigger_deployment, prefect_post, prefect_run_ui_url,
)

# Single master deployment — runs all 11 EIS export flows sequentially
_EIS_DEPLOYMENT = "export_eis_data_deploy"

_REV_RE = re.compile(r"^[A-Z]\d{2}$")

# CRS file discovery patterns (mirrored from scripts/import_crs_data.py)
_CRS_MAIN_PATTERN = re.compile(
    r"^DOC_COMMENT_(JDAW-KVE-E-JA-6944-00001-\d{3}_A\d+)_[A-Za-z]{3}\.xlsx$",
    re.IGNORECASE,
)
_CRS_DETAIL_PATTERN = re.compile(
    r"^(JDAW-KVE-E-JA-6944-00001-\d{3}_A\d+)(?:_\d+|_Review_Comments)\.xlsx$",
    re.IGNORECASE,
)
_CRS_REV_RE = re.compile(r"_A(\d+)", re.IGNORECASE)
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Flow run states that require no further polling
_TERMINAL_STATES = {"COMPLETED", "FAILED", "CRASHED", "CANCELLED"}
_WARN_STATES     = {"PAUSED", "CANCELLING"}

_STATE_COLOR = {
    "COMPLETED":  "#3FB950",
    "FAILED":     "#F85149",
    "CRASHED":    "#F85149",
    "RUNNING":    "#1976D2",
    "SCHEDULED":  "#D29922",
    "CANCELLED":  "#8B949E",
    "PAUSED":     "#D29922",
    "CANCELLING": "#D29922",
    "PENDING":    "#8B949E",
}

_TOTAL_STEPS = 11

# Exact Prefect deployment name for CRS classification
# Registered by etl/flows/classify_crs_comments_deploy.py
_CRS_CLASSIFY_DEPLOYMENT = "classify_crs_comments_cascade"


@st.cache_data(ttl=120)
def _scan_crs_revisions(crs_data_dir: str) -> list[str]:
    """Scan crs_data_dir recursively for CRS Excel files, return sorted revision list."""
    p = Path(crs_data_dir)
    if not p.exists():
        return []
    keys: set[str] = set()
    for f in p.rglob("*.xlsx"):
        for pat in (_CRS_MAIN_PATTERN, _CRS_DETAIL_PATTERN):
            m = pat.match(f.name)
            if m:
                rev_m = _CRS_REV_RE.search(m.group(1))
                if rev_m:
                    keys.add(f"A{rev_m.group(1)}")
                break
    return sorted(keys, key=lambda r: int(r[1:]))


@st.cache_data(ttl=60, show_spinner=False)
def _sql_crs_revisions() -> list[str]:
    """Return sorted list of CRS revisions present in audit_core.crs_comment."""
    df = db_read(
        "SELECT DISTINCT revision FROM audit_core.crs_comment "
        "WHERE revision IS NOT NULL ORDER BY revision",
        admin=True,
    )
    if df.empty:
        return []
    revs = df["revision"].dropna().tolist()
    return sorted(revs, key=lambda r: int(r[1:]) if len(r) > 1 and r[1:].isdigit() else 0)


def _run_crs_import(rev: str, log_key: str) -> None:
    """Run import_crs_data.py in subprocess, stream stdout into session state log list."""
    cmd = ["python", "scripts/import_crs_data.py", "--debug", "--debug-rev", rev]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, cwd=str(_REPO_ROOT),
    )
    for line in proc.stdout:
        st.session_state.setdefault(log_key, []).append(line.rstrip())
    proc.wait()
    st.session_state[f"{log_key}_done"] = True
    st.session_state[f"{log_key}_rc"] = proc.returncode


def _trigger_crs_classify(rev: str) -> None:
    """Trigger classify_crs_comments_cascade deployment; log warning if not registered."""
    result = trigger_deployment(_CRS_CLASSIFY_DEPLOYMENT, {"revision_filter": rev})
    if result and "id" in result:
        log("ok", f"Classification scheduled — ID: {result['id'][:8]}", "crs_log")
    else:
        err = result.get("error", str(result)) if isinstance(result, dict) else str(result)
        log("warn", f"Classification deployment not found or failed: {err}", "crs_log")


_RESET_COLS = [
    "classification_tier",
    "classification_template",   # legacy name — skipped by migration guard if absent
    "template_id",
    "llm_response",
    "llm_response_timestamp",
    "llm_category",
    "llm_category_confidence",
    "llm_model_used",
    "category_code",
    "category_confidence",
]


def _reset_crs_classification(rev: str, log_key: str) -> None:
    """
    NULL-out classification fields for the given revision and write audit rows.
    Uses shared admin engine from ui.common (DATABASE_URL env var).
    No dependency on config.yaml.
    """
    import json
    import uuid as _uuid

    run_id = str(_uuid.uuid4())
    log("info",
        f"Resetting classification for revision {rev} (run_id={run_id[:8]})",
        log_key)

    # Step 1: collect IDs before resetting (for audit)
    df_ids = db_read(
        "SELECT id FROM audit_core.crs_comment "
        "WHERE revision = :rev AND object_status = 'Active'",
        {"rev": rev},
        admin=True,
    )
    if df_ids.empty:
        log("warn",
            f"No active comments for revision {rev} — nothing to reset",
            log_key)
        return
    ids = df_ids["id"].astype(str).tolist()

    # Step 2: check which optional columns exist (migration guard)
    df_cols = db_read(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'audit_core'
          AND table_name   = 'crs_comment'
          AND column_name  = ANY(:cols)
        """,
        {"cols": _RESET_COLS},
        admin=True,
    )
    existing_cols = set(df_cols["column_name"].tolist()) if not df_cols.empty else set()

    set_parts = ["status = 'RECEIVED'"]
    for col in _RESET_COLS:
        if col in existing_cols:
            set_parts.append(f"{col} = NULL")
        else:
            log("warn", f"Column {col} not found in crs_comment — skipped", log_key)

    set_clause = ", ".join(set_parts)
    ok = db_write(
        f"UPDATE audit_core.crs_comment SET {set_clause} "
        "WHERE revision = :rev AND object_status = 'Active'",
        {"rev": rev},
    )
    if not ok:
        raise RuntimeError("UPDATE failed — check DB error above")

    # Step 3: write one audit row per affected comment
    snap = json.dumps({
        "revision": rev,
        "reset_by": "ui",
        "reset_at": str(datetime.now()),
        "cleared_cols": [col for col in _RESET_COLS if col in existing_cols],
    })
    for cid in ids:
        db_write(
            "INSERT INTO audit_core.crs_comment_audit "
            "(comment_id, change_type, snapshot, run_id) "
            "VALUES (:cid, 'RESET', CAST(:snap AS jsonb), :rid)",
            {"cid": cid, "snap": snap, "rid": run_id},
        )

    log("ok",
        f"Reset complete — {len(ids)} comment(s) cleared for revision {rev}",
        log_key)


def _crs_needs_reset_count(rev: str) -> tuple[int, int]:
    """
    Return (total_active, needs_reset_count) for given revision.

    needs_reset_count > 0 means at least one comment has classification data
    that has not yet been cleared (status != RECEIVED or classification fields non-null).
    Uses migration guard — only checks columns that actually exist.
    """
    df_cols = db_read(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'audit_core' AND table_name = 'crs_comment' "
        "AND column_name = ANY(:cols)",
        {"cols": _RESET_COLS},
        admin=True,
    )
    existing = set(df_cols["column_name"].tolist()) if not df_cols.empty else set()

    # A comment needs reset if its status is no longer RECEIVED OR any classification
    # field has been written (non-null)
    cond_parts = ["status != 'RECEIVED'"]
    for col in _RESET_COLS:
        if col in existing:
            cond_parts.append(f"{col} IS NOT NULL")
    needs_reset_cond = " OR ".join(cond_parts)

    df = db_read(
        f"SELECT COUNT(*) AS total, "
        f"COUNT(*) FILTER (WHERE {needs_reset_cond}) AS needs_reset "
        f"FROM audit_core.crs_comment "
        f"WHERE revision = :rev AND object_status = 'Active'",
        {"rev": rev},
        admin=True,
    )
    if df.empty:
        return 0, 0
    return int(df["total"].iloc[0]), int(df["needs_reset"].iloc[0])


def _fetch_export_deployments():
    """Query Prefect API for all export-* deployments."""
    import pandas as pd
    data = prefect_post("/deployments/filter", {
        "limit": 50,
        "deployments": {"name": {"like_": "export_%"}},
    })
    if not data or isinstance(data, dict):
        return pd.DataFrame()
    rows = []
    for d in data:
        last_run = (d.get("updated") or "")[:19].replace("T", " ")
        rows.append({
            "Deployment": d.get("name", ""),
            "Status":     d.get("status", "—"),
            "Updated":    last_run,
        })
    return pd.DataFrame(rows)


def _poll_run() -> dict | None:
    run = st.session_state.get("export_run")
    if not run:
        return None
    if run.get("run_id") and run["state"] not in _TERMINAL_STATES:
        info = get_flow_run_status(run["run_id"])
        if info:
            state_obj  = info.get("state") or {}
            raw_type   = state_obj.get("type") or ""
            state_type = raw_type.upper() if raw_type else run["state"]
            state_name = state_obj.get("name") or state_type
            if state_type != run["state"]:
                log("info", f"[parent] {run['state']} → {state_type}", "eis_log")
            run = {**run, "state": state_type, "state_name": state_name}
            st.session_state["export_run"] = run
        else:
            log("warn", f"[parent] API returned None for {run['run_id'][:8]}", "eis_log")
    return run

def _fetch_child_runs(parent_run_id: str) -> list[dict]:
    """Query child flow runs for real step-level progress."""
    data = prefect_post("/flow_runs/filter", {
        "flow_runs": {"parent_flow_run_id": {"any_": [parent_run_id]}},
        "limit": 50,
    })
    if not isinstance(data, list):
        return []
    # Query flow names if flow_name is missing
    flow_ids = list({c["flow_id"] for c in data if c.get("flow_id") and not c.get("flow_name")})
    if flow_ids:
        flows_data = prefect_post("/flows/filter", {
            "flows": {"id": {"any_": flow_ids}},
            "limit": len(flow_ids),
        })
        if isinstance(flows_data, list):
            flow_map = {f["id"]: f.get("name", "") for f in flows_data}
            for c in data:
                if not c.get("flow_name") and c.get("flow_id"):
                    c["flow_name"] = flow_map.get(c["flow_id"], "")
    return data

def _log_child_changes(children: list[dict]) -> None:
    """Log state changes in child runs — compare against last known snapshot."""
    prev = st.session_state.get("_eis_child_snapshot", {})
    curr = {}
    for c in children:
        run_id   = c.get("id", "")[:8]
        label = (
            c.get("deployment_name")          # "export_tag_register_data_deploy"
            or c.get("flow_name")              # "export_tag_register_data"
            or c.get("name")                   # "merry-rabbit" — fallback
            or run_id
        )
        state_obj = c.get("state") or {}
        state    = (state_obj.get("type") or "UNKNOWN").upper()
        curr[run_id] = state

        prev_state = prev.get(run_id)
        if prev_state != state:
            end_time = c.get("end_time") or c.get("updated") or ""
            end_str  = end_time[:19].replace("T", " ") if end_time else ""
            duration = ""
            if c.get("total_run_time"):
                secs = round(c["total_run_time"])
                duration = f" [{secs}s]"

            level = "ok" if state == "COMPLETED" else ("err" if state in ("FAILED", "CRASHED") else "info")
            log(level, f"[subflow] {label} → {state}{duration} {end_str}", "eis_log")

    st.session_state["_eis_child_snapshot"] = curr

def _fetch_prefect_run_logs(flow_run_id: str) -> list[str]:
    """Fetch log lines for a Prefect flow run, sorted ascending by timestamp."""
    _LEVEL_MAP = {10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL"}
    payload = {
        "logs": {"flow_run_id": {"any_": [flow_run_id]}, "level": {"ge_": 20}},
        "sort": "TIMESTAMP_ASC",
        "limit": 500,
        "offset": 0,
    }
    try:
        data = prefect_post("/logs/filter", payload)
        if not isinstance(data, list):
            return []
        lines = []
        for entry in data:
            ts = (entry.get("timestamp") or "")[:19].replace("T", " ")
            time_part = ts[11:19] if len(ts) >= 19 else ts
            lvl_int = entry.get("level") or 20
            lvl = _LEVEL_MAP.get(lvl_int, str(lvl_int))
            name = entry.get("name") or ""
            msg = entry.get("message") or ""
            lines.append(f"{time_part} | {lvl:<8} | {name} - {msg}")
        return lines
    except Exception:
        return []


def render() -> None:
    st.markdown("### 📤 EIS & CRS Management")
    st.caption("Export EIS data packages · CRS classification · Revision control · Prefect orchestration")

    for _k, _v in [
        ("crs_log", []), ("crs_import_running", False),
        ("crs_log_done", False), ("crs_log_rc", None),
        ("crs_classify_running", False),
        ("crs_classify_done", False),
        ("crs_classify_run_id", None),
        ("crs_reset_confirm", False),
        ("crs_reset_done", False),
        ("_crs_reset_clear", False),          # Flush flag: removes widget key before re-render
        ("crs_debug_run_id",     None),
        ("crs_debug_running",    False),
        ("crs_debug_done",       False),
        ("crs_debug_log_lines",  []),
        ("crs_debug_log_count",  0),
        ("crs_debug_flow_state", None),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # ════════════════════════════════════════════════════════════════════════════
    with st.expander("📤 EIS Management", expanded=False):

        # ── Export Deployments ────────────────────────────────────────────────────
        section("Export Deployments")
        if st.button("⟳", key="eis_dep_refresh", help="Refresh deployment list"):
            st.rerun()
        df_deps = _fetch_export_deployments()
        if not df_deps.empty:
            st.dataframe(df_deps, use_container_width=True, hide_index=True)
        else:
            st.caption("⚠ No export deployments found in Prefect — run `python scripts/deploy_all.py` to register them.")

        # ── Run Export ────────────────────────────────────────────────────────────
        section("Run Export")
        col_l, col_r = st.columns([2, 1], gap="large")

        with col_l:
            st.caption(
                "Triggers **EIS Full Package Export** — all 11 export flows run sequentially: "
                "Tag Register (003) · Equipment Register (004) · Model Part (209) · "
                "Tag Connections (212) · Purchase Order (214) · Area Register (203) · "
                "Process Unit (204) · Tag Properties (303) · Equipment Properties (301) · "
                "Tag Class Properties (307) · Document Cross-References (408–420)."
            )

        with col_r:
            rev = st.text_input(
                "Document revision", value="A35",
                help="Format: [A-Z]\\d{2} e.g. A35",
                key="eis_rev",
            )
            rev_err = None if _REV_RE.match(rev) else f"Invalid revision '{rev}' — expected e.g. A35"
            if rev_err:
                st.warning(rev_err)

            if st.button("▶ Run Export", type="primary", use_container_width=True,
                         disabled=bool(rev_err), key="btn_eis_run"):
                _trigger_export(rev)

        # ── Execution Log ─────────────────────────────────────────────────────────
        section("Execution Log")
        render_log("eis_log")
        if st.button("Clear", key="eis_clr"):
            st.session_state["eis_log"] = []
            st.rerun()

        # ── Export Progress ───────────────────────────────────────────────────────
        section("Export Progress")
        # Create placeholder for log BEFORE calling _poll_run
        # It will be updated immediately after writing new lines
        _log_placeholder = st.empty()
        run = _poll_run()

        if not run:
            st.caption("No active export. Trigger a run above.")
        else:
            state      = run["state"]
            state_name = run.get("state_name", state)
            is_terminal = state in _TERMINAL_STATES
            color = _STATE_COLOR.get(state, "#8B949E")

            st.markdown(
                f'<span style="color:{color};font-weight:600;font-size:14px">'
                f'● {state_name}</span>'
                f' &nbsp; <span style="color:#8B949E">{run["name"]}</span>',
                unsafe_allow_html=True,
            )

            # Real progress via child flow runs
            if run.get("run_id") and not is_terminal:
                children  = _fetch_child_runs(run["run_id"])
                _log_child_changes(children)
                completed = sum(
                    1 for c in children
                    if (c.get("state") or {}).get("type") == "COMPLETED"
                )
                if len(children) == 0:
                    progress_val = 0.02
                    step_label   = "waiting for first step…"
                else:
                    progress_val = completed / _TOTAL_STEPS
                    step_label   = f"{completed}/{_TOTAL_STEPS}"

                if completed >= _TOTAL_STEPS and len(children) >= _TOTAL_STEPS:
                    log("ok", "[parent] all subflows completed → forcibly COMPLETED", "eis_log")
                    run = {**run, "state": "COMPLETED", "state_name": "Completed"}
                    st.session_state["export_run"] = run
                    state      = "COMPLETED"
                    is_terminal = True
                    progress_val = 1.0
                    step_label   = f"{_TOTAL_STEPS}/{_TOTAL_STEPS}"

                if st.toggle("🔍 Show raw Prefect data", value=False, key="_eis_debug_raw_toggle"):
                    st.write("**Parent run state:**", run)
                    st.write("**Child runs:**", [
                        {
                            "name":  c.get("name") or c.get("flow_run_name", "")[:30],
                            "state": (c.get("state") or {}).get("type", "?"),
                            "end":   (c.get("end_time") or "")[:19],
                            "dur":   c.get("total_run_time"),
                        }
                        for c in children
                    ])
            elif state == "COMPLETED":
                progress_val = 1.0
                step_label   = f"{_TOTAL_STEPS}/{_TOTAL_STEPS}"
            else:
                progress_val = 0.0
                step_label   = "failed"

            st.progress(progress_val, text=f"Steps: {step_label}")

            if state in ("FAILED", "CRASHED"):
                st.error("Export failed — check Prefect logs for details.")
            elif state == "CANCELLED":
                st.warning("Export was cancelled.")
            elif state == "PAUSED":
                st.warning("Export is paused — waiting for manual approval in Prefect UI.")
            elif state_name == "Late":
                st.warning("Run is late — check that workers are healthy and polling.")

            if is_terminal:
                # One final rerun to re-render the Download section with updated state
                if not st.session_state.get("_eis_final_rerun_done"):
                    st.session_state["_eis_final_rerun_done"] = True
                    st.rerun()
            elif state not in _WARN_STATES:
                time.sleep(5)
                st.rerun()

        # ── Download Exported Files ───────────────────────────────────────────────
        section("Download Exported Files")
        last        = st.session_state.get("last_export")
        current_run = st.session_state.get("export_run")
        any_completed = current_run is not None and current_run["state"] == "COMPLETED"

        if not last or not any_completed:
            if last and current_run:
                st.caption("Waiting for export to complete before download is available.")
            else:
                st.caption("Run an export to generate files.")
        else:
            export_path = Path(last["folder"])
            rev = last["revision"]
            triggered_at = last["triggered_at"].strftime("%Y-%m-%d %H:%M")
            st.caption(f"Revision `{rev}` · Triggered: {triggered_at} · `{last['folder']}`")
            if export_path.exists():
                rev_upper = rev.upper()
                all_csvs  = list(export_path.glob("*.CSV")) if export_path.exists() else []

                # Priority 1: by revision mask in file name
                by_rev = [f for f in all_csvs if rev_upper in f.name.upper()]
                # Fallback: by triggered time if mask did not yield results
                if by_rev:
                    files = sorted(by_rev, key=lambda f: f.stat().st_mtime, reverse=True)
                else:
                    triggered_ts = last["triggered_at"].timestamp()
                    files = sorted(
                        [f for f in all_csvs if f.stat().st_mtime >= triggered_ts - 30],
                        key=lambda f: f.stat().st_mtime,
                        reverse=True,
                    )
                if files:
                    zip_buf = _io.BytesIO()
                    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for fpath in files:
                            zf.write(fpath, fpath.name)
                    col_zip, _ = st.columns([2, 6])
                    col_zip.download_button(
                        "⬇ Download All (ZIP)",
                        data=zip_buf.getvalue(),
                        file_name=f"eis_export_{rev}_{datetime.now():%Y%m%d_%H%M}.zip",
                        mime="application/zip",
                        key="dl_all_zip",
                    )
                    for fpath in files:
                        col_name, col_dl = st.columns([5, 1])
                        col_name.caption(
                            f"`{fpath.name}` · {fpath.stat().st_size // 1024} KB · "
                            f"{datetime.fromtimestamp(fpath.stat().st_mtime):%Y-%m-%d %H:%M}"
                        )
                        col_dl.download_button(
                            "⬇",
                            data=fpath.read_bytes(),
                            file_name=fpath.name,
                            key=f"dl_{fpath.name}",
                        )
                else:
                    st.info("Files not yet written — flow is running, please wait.")
            else:
                st.info("Output folder not yet created — flow is running, please wait.")

    # ════════════════════════════════════════════════════════════════════════════
    with st.expander("🗂 CRS Management", expanded=True):

        can_manage_crs = is_admin()
        if not can_manage_crs:
            st.caption("🔒 Admin access required for CRS management actions.")

        # ── Section A: CRS Import ─────────────────────────────────────────────────
        section("Import CRS Comments")

        crs_data_dir = CRS_DATA_DIR
        revisions = _scan_crs_revisions(crs_data_dir) if crs_data_dir else []
        no_files  = not revisions

        col_sel, col_btn = st.columns([4, 1])
        with col_sel:
            selected_rev = st.selectbox(
                "CRS Revision", options=revisions if revisions else ["—"],
                disabled=no_files, key="crs_rev_sel",
            )
            if no_files:
                st.warning(f"No CRS files found in {crs_data_dir or '<crs_data_dir not set>'}")
            c_refresh, _ = st.columns([1, 8])
            if c_refresh.button("🔄", key="crs_rev_refresh", help="Rescan directory"):
                st.cache_data.clear()
                st.rerun()

        proceed_allowed = not no_files
        if not no_files and selected_rev and selected_rev != "—":
            df_existing = db_read(
                "SELECT status, COUNT(*) AS cnt FROM audit_core.crs_comment "
                "WHERE revision = :rev GROUP BY status ORDER BY status",
                {"rev": selected_rev},
                admin=True,
            )
            if not df_existing.empty:
                total = int(df_existing["cnt"].sum())
                st.warning(
                    f"Revision **{selected_rev}** already has **{total}** comments in DB. "
                    "Re-importing will overwrite existing data."
                )
                st.dataframe(df_existing, hide_index=True, use_container_width=True)
                proceed_allowed = st.checkbox(
                    "I understand — proceed with import", key="crs_import_confirm"
                )

        with col_btn:
            run_btn = st.button(
                "Load Revision", type="primary",
                disabled=(no_files or not proceed_allowed or st.session_state["crs_import_running"]),
                key="crs_import_run",
            )

        if run_btn and not st.session_state["crs_import_running"]:
            st.session_state["crs_import_running"] = True
            st.session_state["crs_log_done"] = False
            st.session_state["crs_log_rc"] = None
            st.session_state["crs_log"] = []
            log("info", f"Starting CRS import for revision {selected_rev}", "crs_log")
            t = threading.Thread(
                target=_run_crs_import, args=(selected_rev, "crs_log"), daemon=True,
            )
            t.start()
            st.rerun()

        if st.session_state["crs_import_running"]:
            if not st.session_state["crs_log_done"]:
                with st.spinner(f"Importing CRS revision {selected_rev}…"):
                    time.sleep(2)
                    st.rerun()
            else:
                st.session_state["crs_import_running"] = False
                rc = st.session_state.get("crs_log_rc", -1)
                if rc == 0:
                    st.success(f"Import completed successfully (rc={rc})")
                    log("ok", f"CRS import finished rc={rc}", "crs_log")
                    _trigger_crs_classify(selected_rev)
                else:
                    st.error(f"Import failed (rc={rc}) — check log below")
                    log("err", f"CRS import failed rc={rc}", "crs_log")

        # CRS Execution Log
        section("CRS Execution Log")
        render_log("crs_log")
        c_clr, _ = st.columns([1, 8])
        if c_clr.button("Clear", key="crs_log_clr"):
            st.session_state["crs_log"] = []
            st.session_state["crs_log_done"] = False
            st.session_state["crs_log_rc"] = None
            st.rerun()

        # ── Section D: Classify CRS Comments ─────────────────────────────────────
        section("Classify CRS Comments")

        sql_revs    = _sql_crs_revisions()
        no_sql_revs = not sql_revs

        col_cls_sel, col_cls_refresh, col_cls_btn = st.columns([5, 1, 2])

        with col_cls_sel:
            # Default to the latest (highest) revision; preserve user's current selection
            _current_classify_rev = st.session_state.get("crs_classify_rev_sel")
            if sql_revs:
                _default_idx = len(sql_revs) - 1
                if _current_classify_rev in sql_revs:
                    _default_idx = sql_revs.index(_current_classify_rev)
            else:
                _default_idx = 0

            classify_rev = st.selectbox(
                "Revision (from DB)",
                options=sql_revs if sql_revs else ["—"],
                index=_default_idx,
                disabled=no_sql_revs,
                key="crs_classify_rev_sel",
                help="Revisions available in audit_core.crs_comment",
            )

        with col_cls_refresh:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            if st.button("🔄", key="crs_classify_rev_refresh", help="Refresh revision list from DB"):
                st.cache_data.clear()
                st.rerun()

        with col_cls_btn:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            classify_btn = st.button(
                "▶ Classify",
                type="primary",
                disabled=(no_sql_revs or st.session_state["crs_classify_running"] or not can_manage_crs),
                key="btn_crs_classify",
                use_container_width=True,
            )

        if no_sql_revs:
            st.info(
                "No imported CRS revisions found in DB. "
                "Run **Import CRS Comments** first."
            )
        else:
            try:
                df_cls_summary = db_read(
                    """
                    SELECT
                        status                                                      AS "Status",
                        COUNT(*)                                                    AS "Total",
                        COUNT(*) FILTER (WHERE classification_tier IS NOT NULL)     AS "Classified",
                        COUNT(*) FILTER (WHERE classification_tier IS NULL)         AS "Pending"
                    FROM audit_core.crs_comment
                    WHERE revision = :rev
                    GROUP BY status
                    ORDER BY status
                    """,
                    {"rev": classify_rev},
                    admin=True,
                )
                if not df_cls_summary.empty:
                    total_rev  = int(df_cls_summary["Total"].sum())
                    total_pend = int(df_cls_summary["Pending"].sum())
                    st.caption(
                        f"Revision **{classify_rev}**: "
                        f"**{total_rev}** comments total · "
                        f"**{total_pend}** pending classification"
                    )
                    st.dataframe(df_cls_summary, hide_index=True, use_container_width=True)
            except Exception:
                st.warning(
                    "classification_tier column not found — run migration_012+ to enable this view."
                )

        if classify_btn and not st.session_state["crs_classify_running"]:
            st.session_state["crs_classify_running"] = True
            st.session_state["crs_classify_done"]    = False
            st.session_state["crs_classify_run_id"]  = None
            log("info", f"Triggering classification for revision {classify_rev}", "crs_log")
            result = trigger_deployment(
                _CRS_CLASSIFY_DEPLOYMENT,
                {"revision_filter": classify_rev},
            )
            if result and "id" in result:
                run_id = result["id"]
                st.session_state["crs_classify_run_id"]  = run_id
                st.session_state["crs_classify_running"] = False
                st.session_state["crs_classify_done"]    = True
                log("ok",
                    f"Classification scheduled — deployment ID: {run_id[:8]} rev={classify_rev}",
                    "crs_log")
                st.success(
                    f"✅ Classification flow scheduled for revision **{classify_rev}**. "
                    f"Run ID: `{run_id[:8]}`"
                )
            else:
                st.session_state["crs_classify_running"] = False
                err = (result.get("error", str(result))
                       if isinstance(result, dict) else str(result))
                log("err", f"Classification trigger failed: {err}", "crs_log")
                st.error(
                    f"❌ Could not schedule classification flow. "
                    f"Check that `{_CRS_CLASSIFY_DEPLOYMENT}` is registered in Prefect "
                    f"(run `python scripts/deploy_all.py`). "
                    f"Error: `{err}`"
                )

        # ── Reset Classification ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**⚠ Reset Classification**")
        st.caption(
            "Clears all classification fields (`classification_tier`, `template_id`, "
            "`llm_category`, `llm_category_confidence`, `llm_model_used`, `category_code`, "
            "`category_confidence`, `llm_response`, `llm_response_timestamp`) and resets "
            "status to `RECEIVED`. Uses migration guard — only clears columns that exist. "
            "Logged to `audit_core.crs_comment_audit`."
        )

        if not no_sql_revs:
            # Flush pending clear: remove widget key so it re-renders unchecked
            if st.session_state.pop("_crs_reset_clear", False):
                st.session_state.pop("crs_reset_confirm", None)

            # Determine how many comments actually need resetting
            _total_active, _needs_reset = _crs_needs_reset_count(classify_rev)
            _nothing_to_reset = (_needs_reset == 0)

            if _nothing_to_reset:
                st.caption(f"All comments for revision **{classify_rev}** are already reset.")
            else:
                st.caption(f"**{_needs_reset}** of {_total_active} comments can still be reset.")

            reset_confirm = st.checkbox(
                f"I understand — reset classification for revision **{classify_rev}**",
                key="crs_reset_confirm",
                value=False,
            )
            col_rst_btn, col_rst_info = st.columns([1, 2])
            with col_rst_btn:
                reset_btn = st.button(
                    "🔄 Reset",
                    type="secondary",
                    disabled=(not reset_confirm or _nothing_to_reset or not can_manage_crs),
                    key="btn_crs_reset",
                    use_container_width=True,
                )
            with col_rst_info:
                if not reset_confirm and not _nothing_to_reset:
                    st.caption("Check the box above to enable the Reset button.")

            if reset_btn and reset_confirm:
                try:
                    with st.spinner(f"Resetting classification for revision {classify_rev}…"):
                        _reset_crs_classification(classify_rev, "crs_log")
                    st.session_state["_crs_reset_clear"] = True
                    st.session_state["crs_reset_done"] = True
                    st.cache_data.clear()
                    st.success(
                        f"✅ Classification reset for revision **{classify_rev}**. "
                        "You can now re-run the Classify flow."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Reset failed: {exc}")

        # ── Debug: Reset & Reclassify ─────────────────────────────────────────────
        if is_admin() and not no_sql_revs:
            st.markdown("---")
            st.markdown("**🧪 Debug: Reset & Reclassify**")
            st.caption(
                "Resets classification fields for the selected revision (same as Reset above), "
                "then immediately triggers the classify flow with an optional comment limit. "
                "Admin-only. All actions logged to `audit_core.crs_comment_audit`."
            )
            debug_limit = st.number_input(
                "Comment limit (0 = all RECEIVED)",
                min_value=0,
                value=50,
                key="crs_debug_limit",
                help=f"Passed as `limit` parameter to `{_CRS_CLASSIFY_DEPLOYMENT}`. 0 = no limit.",
            )
            debug_confirm = st.checkbox(
                f"I understand — reset & reclassify revision **{classify_rev}**",
                key="crs_debug_confirm",
            )
            debug_btn = st.button(
                "🧪 Debug Reclassify",
                disabled=(not debug_confirm),
                key="btn_crs_debug",
            )
            if debug_btn and debug_confirm:
                try:
                    with st.spinner(f"Resetting classification for {classify_rev}…"):
                        _reset_crs_classification(classify_rev, "crs_log")
                    st.cache_data.clear()
                    result = trigger_deployment(
                        _CRS_CLASSIFY_DEPLOYMENT,
                        {"revision_filter": classify_rev, "limit": int(debug_limit)},
                    )
                    if result and "id" in result:
                        run_id = result["id"]
                        st.session_state["crs_debug_run_id"]     = run_id
                        st.session_state["crs_debug_running"]    = True
                        st.session_state["crs_debug_done"]       = False
                        st.session_state["crs_debug_log_lines"]  = []
                        st.session_state["crs_debug_log_count"]  = 0
                        st.session_state["crs_debug_flow_state"] = None
                        log("ok",
                            f"Debug run {run_id[:8]} started — rev={classify_rev} limit={debug_limit}",
                            "crs_log")
                        run_url = prefect_run_ui_url(run_id)
                        st.markdown(f"🔗 [Open in Prefect]({run_url})")
                    else:
                        err = (result.get("error", str(result))
                               if isinstance(result, dict) else str(result))
                        log("err", f"Debug classify trigger failed: {err}", "crs_log")
                        st.error(f"❌ Classify trigger failed: {err}")
                except Exception as exc:
                    st.error(f"❌ Debug reclassify failed: {exc}")

        # ── CRS Debug Run — Live Logs ─────────────────────────────────────────────
        if st.session_state.get("crs_debug_run_id"):
            section("CRS Debug Run")
            _debug_run_id  = st.session_state["crs_debug_run_id"]
            _debug_running = st.session_state.get("crs_debug_running", False)
            _debug_state   = st.session_state.get("crs_debug_flow_state") or "..."

            run_url = prefect_run_ui_url(_debug_run_id)
            st.markdown(
                f"Run `{_debug_run_id[:8]}` · state: **{_debug_state}** · "
                f"[Open in Prefect]({run_url})"
            )

            if _debug_running:
                new_lines = _fetch_prefect_run_logs(_debug_run_id)
                if len(new_lines) > st.session_state["crs_debug_log_count"]:
                    st.session_state["crs_debug_log_lines"] = new_lines
                    st.session_state["crs_debug_log_count"] = len(new_lines)

            if _debug_running:
                run_info = get_flow_run_status(_debug_run_id)
                if run_info:
                    state_obj = run_info.get("state") or {}
                    raw_state = (state_obj.get("type") or "").upper()
                    if raw_state:
                        st.session_state["crs_debug_flow_state"] = raw_state
                        _debug_state = raw_state
                    if raw_state in _TERMINAL_STATES:
                        st.session_state["crs_debug_running"] = False
                        st.session_state["crs_debug_done"]    = True
                        _debug_running = False

            log_lines = st.session_state.get("crs_debug_log_lines", [])
            if log_lines:
                st.code("\n".join(log_lines), language=None)
            else:
                st.caption("Waiting for first log lines…" if _debug_running else "No logs available.")

            if st.session_state.get("crs_debug_done"):
                final = st.session_state.get("crs_debug_flow_state", "")
                if final == "COMPLETED":
                    st.success("✅ Debug run completed.")
                elif final in ("FAILED", "CRASHED"):
                    st.error("❌ Debug run failed — see logs above.")
                elif final == "CANCELLED":
                    st.warning("⚠ Debug run was cancelled.")

            col_clr, col_ref = st.columns(2)
            with col_clr:
                if st.button("Clear Debug Log", key="crs_debug_log_clr"):
                    for _k, _v in [
                        ("crs_debug_run_id", None), ("crs_debug_running", False),
                        ("crs_debug_done", False), ("crs_debug_log_lines", []),
                        ("crs_debug_log_count", 0), ("crs_debug_flow_state", None),
                    ]:
                        st.session_state[_k] = _v
                    st.rerun()
            with col_ref:
                if _debug_running and st.button("Refresh", key="crs_debug_refresh"):
                    st.rerun()

            if _debug_running:
                time.sleep(3)
                st.rerun()

        # ── Section B: Validate (stub) ─────────────────────────────────────────────
        section("Validate CRS Comments")
        st.info("🚧 Validation not yet implemented. This button will trigger the "
                "CRS validation Prefect flow in a future release.")
        st.button("Validate", disabled=True, key="btn_crs_validate")

        # ── Section C: Export (stub) ───────────────────────────────────────────────
        section("Export CRS Comments")
        st.info("🚧 Export not yet implemented. Will generate a structured XLSX with "
                "classification results, LLM responses, and validation outcomes.")
        st.button("Export CRS Report", disabled=True, key="btn_crs_export")


def _trigger_export(rev: str) -> None:
    """Trigger the master EIS package export deployment."""
    st.session_state.pop("_eis_final_rerun_done", None)  # reset on new run
    st.session_state.pop("_eis_child_snapshot", None)   # reset child run tracking
    log("info", f"Triggering EIS Full Package Export rev={rev}", "eis_log")
    result = trigger_deployment(_EIS_DEPLOYMENT, {"doc_revision": rev})
    if result and "id" in result:
        st.session_state["export_run"] = {
            "name":   f"EIS Package Export rev={rev}",
            "run_id": result["id"],
            "state":  "SCHEDULED",
        }
        st.session_state["last_export"] = {
            "revision":     rev,
            "folder":       str(Path(EIS_EXPORT_DIR)),
            "triggered_at": datetime.now(),
        }
        log("ok", f"Scheduled — ID: {result['id'][:8]}", "eis_log")
    else:
        log("err", str(result), "eis_log")
