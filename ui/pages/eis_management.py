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
import time
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from ui.common import (
    EIS_EXPORT_DIR, get_flow_run_status, log, render_log,
    require_admin, section, trigger_deployment, prefect_post,
)

# Single master deployment — runs all 11 EIS export flows sequentially
_EIS_DEPLOYMENT = "export-eis-package-deployment"

_REV_RE = re.compile(r"^[A-Z]\d{2}$")

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


def _fetch_export_deployments():
    """Query Prefect API for all export-* deployments."""
    import pandas as pd
    data = prefect_post("/deployments/filter", {
        "limit": 50,
        "deployments": {"name": {"like_": "export-%"}},
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
            c.get("deployment_name")          # "export-tag-register-deployment"
            or c.get("flow_name")              # "export_tag_register"
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

def render() -> None:
    st.markdown("### 📤 EIS Management")
    st.caption("Export EIS data packages · Revision control · Prefect orchestration")

    require_admin()

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

    # ── Export Progress ───────────────────────────────────────────────────────
    section("Export Progress")
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

            with st.expander("🔍 Debug: raw Prefect data", expanded=False):
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

    # ── Execution Log ─────────────────────────────────────────────────────────
    section("Execution Log")
    render_log("eis_log")
    if st.button("Clear", key="eis_clr"):
        st.session_state["eis_log"] = []
        st.rerun()


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
