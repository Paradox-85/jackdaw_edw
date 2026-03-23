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
    """
    Refresh state for the active export run from Prefect.

    Returns updated run dict or None if no run is tracked.
    Skips API call if run is already in a terminal state.
    """
    run = st.session_state.get("export_run")
    if not run:
        return None
    if run["run_id"] and run["state"] not in _TERMINAL_STATES:
        info = get_flow_run_status(run["run_id"])
        if info:
            run = {**run, "state": (info.get("state") or {}).get("type", run["state"])}
            st.session_state["export_run"] = run
    return run


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
        state = run["state"]
        is_terminal = state in _TERMINAL_STATES

        _STATE_COLOR = {
            "COMPLETED": "#3FB950",
            "FAILED":    "#F85149",
            "CRASHED":   "#F85149",
            "RUNNING":   "#1976D2",
            "SCHEDULED": "#D29922",
            "CANCELLED": "#8B949E",
        }
        color = _STATE_COLOR.get(state, "#8B949E")
        progress_val = 1.0 if is_terminal else 0.5
        st.progress(
            progress_val,
            text=f'<span style="color:{color};font-weight:600">{state}</span> — {run["name"]}',
        )

        if not is_terminal:
            time.sleep(5)
            st.rerun()

    # ── Download Exported Files ───────────────────────────────────────────────
    section("Download Exported Files")
    last = st.session_state.get("last_export")
    run  = st.session_state.get("export_run")
    any_completed = run is not None and run["state"] == "COMPLETED"

    if not last or not any_completed:
        if last and run:
            st.caption("Waiting for export to complete before download is available.")
        else:
            st.caption("Run an export to generate files.")
    else:
        export_path = Path(last["folder"])
        rev = last["revision"]
        triggered_at = last["triggered_at"].strftime("%Y-%m-%d %H:%M")
        st.caption(f"Revision `{rev}` · Triggered: {triggered_at} · `{last['folder']}`")
        if export_path.exists():
            files = sorted(export_path.glob("*.CSV"), key=lambda f: f.stat().st_mtime, reverse=True)
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
