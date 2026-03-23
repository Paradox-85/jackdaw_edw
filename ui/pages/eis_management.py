"""
ui/pages/eis_management.py — EIS Management. ADMIN ONLY.

Sections:
  1. Export Flows — live list from Prefect API (export-* pattern)
  2. Run Export — select one or all flows, set revision, trigger via Prefect
  3. Export Progress — real-time polling of triggered Prefect flow runs
  4. Download Exported Files — browse and download files from EIS_EXPORT_DIR
"""
from __future__ import annotations
import io as _io
import re
import time
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from ui.common import (
    EIS_EXPORT_DIR, get_flow_run_status, log, render_log,
    require_admin, section, trigger_deployment, prefect_post,
)

# All EIS export flows — ordered for display
EXPORT_FLOWS = [
    {
        "id":         "tag_register",
        "name":       "Tag Register (seq 003)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-003-{rev}.CSV",
        "deployment": "export-tag-register-deployment",
        "live":       True,
    },
    {
        "id":         "equipment_register",
        "name":       "Equipment Register (seq 004)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-004-{rev}.CSV",
        "deployment": "export-equipment-register-deployment",
        "live":       True,
    },
    {
        "id":         "tag_properties",
        "name":       "Tag Properties (seq 303)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-010-{rev}.CSV",
        "deployment": "export-tag-properties-deployment",
        "live":       True,
    },
    {
        "id":         "equipment_properties",
        "name":       "Equipment Properties (seq 301)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-011-{rev}.CSV",
        "deployment": "export-equipment-properties-deployment",
        "live":       True,
    },
    {
        "id":         "area_register",
        "name":       "Area Register (seq 203)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-017-{rev}.CSV",
        "deployment": "export-area-register-deployment",
        "live":       True,
    },
    {
        "id":         "process_unit",
        "name":       "Process Unit (seq 204)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-018-{rev}.CSV",
        "deployment": "export-process-unit-deployment",
        "live":       True,
    },
    {
        "id":         "purchase_order",
        "name":       "Purchase Order (seq 214)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-008-{rev}.CSV",
        "deployment": "export-purchase-order-deployment",
        "live":       True,
    },
    {
        "id":         "model_part",
        "name":       "Model Part (seq 209)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-005-{rev}.CSV",
        "deployment": "export-model-part-deployment",
        "live":       True,
    },
    {
        "id":         "tag_class_properties",
        "name":       "Tag Class Properties (seq 307)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-009-{rev}.CSV",
        "deployment": "export-tag-class-properties-deployment",
        "live":       True,
    },
    {
        "id":         "tag_connections",
        "name":       "Tag Connections (seq 212)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-006-{rev}.CSV",
        "deployment": "export-tag-connections-deployment",
        "live":       True,
    },
    # Document cross-reference: master + 8 individual sub-flows
    {
        "id":         "document_crossref",
        "name":       "Document Cross-Reference — All 8 (seq 408-420)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-016..024-{rev}.CSV",
        "deployment": "export-document-crossref-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_site",
        "name":       "Doc→Site (seq 408)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-024-{rev}.CSV",
        "deployment": "export-doc-to-site-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_plant",
        "name":       "Doc→Plant (seq 409)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-023-{rev}.CSV",
        "deployment": "export-doc-to-plant-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_process_unit",
        "name":       "Doc→Process Unit (seq 410)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-018-{rev}.CSV",
        "deployment": "export-doc-to-process-unit-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_area",
        "name":       "Doc→Area (seq 411)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-017-{rev}.CSV",
        "deployment": "export-doc-to-area-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_tag",
        "name":       "Doc→Tag (seq 412)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-016-{rev}.CSV",
        "deployment": "export-doc-to-tag-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_equipment",
        "name":       "Doc→Equipment (seq 413)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-019-{rev}.CSV",
        "deployment": "export-doc-to-equipment-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_model_part",
        "name":       "Doc→Model Part (seq 414)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-020-{rev}.CSV",
        "deployment": "export-doc-to-model-part-deployment",
        "live":       True,
    },
    {
        "id":         "doc_to_po",
        "name":       "Doc→Purchase Order (seq 420)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-022-{rev}.CSV",
        "deployment": "export-doc-to-po-deployment",
        "live":       True,
    },
]

_REV_RE = re.compile(r"^[A-Z]\d{2}$")

# Flow run states that require no further polling
_TERMINAL_STATES = {"COMPLETED", "FAILED", "CRASHED", "CANCELLED"}


def _fetch_export_deployments() -> pd.DataFrame:
    """Query Prefect API for all export-* deployments."""
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


def _poll_runs() -> list[dict]:
    """
    Refresh state for all tracked export runs from Prefect.

    Skips polling for runs already in a terminal state to avoid
    unnecessary API calls on completed exports.
    """
    runs = st.session_state.get("export_runs", [])
    updated = []
    for r in runs:
        if r["run_id"] and r["state"] not in _TERMINAL_STATES:
            info = get_flow_run_status(r["run_id"])
            if info:
                r = {**r, "state": (info.get("state") or {}).get("type", r["state"])}
        updated.append(r)
    st.session_state["export_runs"] = updated
    return updated


def render() -> None:
    st.markdown("### 📤 EIS Management")
    st.caption("Export EIS data packages · Revision control · Prefect orchestration")

    require_admin()

    # ── Export Flows ──────────────────────────────────────────────────────────
    section("Export Flows")
    if st.button("⟳", key="eis_dep_refresh", help="Refresh deployment list"):
        st.rerun()
    df_deps = _fetch_export_deployments()
    if not df_deps.empty:
        st.dataframe(df_deps, use_container_width=True, hide_index=True)
    else:
        st.caption("⚠ No export deployments found in Prefect — run `python scripts/deploy_all.py` to register them.")

    # ── Run Export ────────────────────────────────────────────────────────────
    section("Run Export")
    live_flows = [f for f in EXPORT_FLOWS if f["live"]]

    col_l, col_r = st.columns([2, 1], gap="large")
    with col_l:
        export_scope = st.radio(
            "Scope",
            ["Single flow", "Full EIS Package (all flows)"],
            key="eis_scope",
            horizontal=True,
        )
        if export_scope == "Single flow":
            sel_id = st.selectbox(
                "Flow",
                [f["id"] for f in live_flows],
                format_func=lambda x: next(f["name"] for f in live_flows if f["id"] == x),
                key="eis_sel_flow",
            )
            selected_flows = [next(f for f in live_flows if f["id"] == sel_id)]
            st.caption(f"Output: `{selected_flows[0]['file_tmpl']}`")
        else:
            selected_flows = live_flows
            st.caption(
                f"{len(live_flows)} flows: "
                + " · ".join(f["name"] for f in live_flows)
            )

    with col_r:
        rev = st.text_input("Document revision", value="A35", help="Format: [A-Z]\\d{2} e.g. A35", key="eis_rev")
        rev_err = None if _REV_RE.match(rev) else f"Invalid revision '{rev}' — expected e.g. A35"
        if rev_err:
            st.warning(rev_err)

        if st.button("▶ Run Export", type="primary", use_container_width=True,
                     disabled=bool(rev_err), key="btn_eis_run"):
            _trigger_flows(selected_flows, rev)

    # ── Export Progress ───────────────────────────────────────────────────────
    section("Export Progress")
    runs = _poll_runs()

    if not runs:
        st.caption("No active export. Trigger a run above.")
    else:
        done  = sum(1 for r in runs if r["state"] in _TERMINAL_STATES)
        total = len(runs)
        failed = sum(1 for r in runs if r["state"] in {"FAILED", "CRASHED"})

        progress_text = f"{done} / {total} flows finished"
        if failed:
            progress_text += f" · {failed} failed"
        st.progress(done / total if total else 0, text=progress_text)

        # Per-flow status rows — colour-coded via badge HTML
        _STATE_COLOR = {
            "COMPLETED": "#3FB950",
            "FAILED":    "#F85149",
            "CRASHED":   "#F85149",
            "RUNNING":   "#1976D2",
            "SCHEDULED": "#D29922",
            "CANCELLED": "#8B949E",
        }
        rows_html = []
        for r in runs:
            color = _STATE_COLOR.get(r["state"], "#8B949E")
            state_html = (
                f'<span style="color:{color};font-weight:600;font-size:11px">'
                f'{r["state"]}</span>'
            )
            rows_html.append(
                f'<tr><td style="padding:4px 12px;font-size:12px;color:#C9D1D9">{r["name"]}</td>'
                f'<td style="padding:4px 12px">{state_html}</td></tr>'
            )
        table_html = (
            '<table style="width:100%;border-collapse:collapse">'
            + "".join(rows_html)
            + "</table>"
        )
        st.markdown(table_html, unsafe_allow_html=True)

        # Auto-rerun every 5 s while any flow is still in-progress
        if done < total:
            time.sleep(5)
            st.rerun()

    # ── Download Exported Files ───────────────────────────────────────────────
    section("Download Exported Files")
    last  = st.session_state.get("last_export")
    runs  = st.session_state.get("export_runs", [])
    any_completed = any(r["state"] == "COMPLETED" for r in runs)

    if not last or not any_completed:
        if last and runs:
            st.caption("Waiting for flows to complete before download is available.")
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
                st.info("Files not yet written — flows are running, please wait.")
        else:
            st.info("Output folder not yet created — flows are running, please wait.")

    # ── Execution Log ─────────────────────────────────────────────────────────
    section("Execution Log")
    render_log("eis_log")
    if st.button("Clear", key="eis_clr"):
        st.session_state["eis_log"] = []
        st.rerun()


def _trigger_flows(flows: list[dict], rev: str) -> None:
    subdir = f"{rev}/{datetime.now():%Y%m%d_%H%M}"
    output_dir = str(Path(EIS_EXPORT_DIR) / subdir)
    st.session_state["last_export"] = {
        "revision":     rev,
        "folder":       output_dir,
        "triggered_at": datetime.now(),
    }
    runs: list[dict] = []
    for f in flows:
        params: dict = {"doc_revision": rev, "output_dir": output_dir}
        log("info", f"Triggering: {f['name']} rev={rev} → {subdir}", "eis_log")
        result = trigger_deployment(f["deployment"], params)
        if result and "id" in result:
            runs.append({"name": f["name"], "run_id": result["id"], "state": "SCHEDULED"})
            log("ok", f"Scheduled — ID: {result['id'][:8]}", "eis_log")
        else:
            runs.append({"name": f["name"], "run_id": None, "state": "FAILED"})
            log("err", str(result), "eis_log")
    st.session_state["export_runs"] = runs
