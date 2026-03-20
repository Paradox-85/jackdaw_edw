"""
ui/pages/eis_management.py — EIS Management. ADMIN ONLY.

Sections:
  1. Active Export Deployments — live list from Prefect API (export-* pattern)
  2. Individual Export — select one register, set revision, trigger or download
  3. Full EIS Package Export — trigger all registered export deployments at once
"""
from __future__ import annotations
import io, re
import pandas as pd
import streamlit as st
from ui.common import (
    EIS_EXPORT_DIR, db_read, log, render_log,
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
    {
        "id":         "document_crossref",
        "name":       "Document Cross-Reference (doc-to-* registers)",
        "file_tmpl":  "JDAW-KVE-E-JA-6944-00001-016..024-{rev}.CSV",
        "deployment": "export-document-crossref-deployment",
        "live":       True,
    },
]

_REV_RE = re.compile(r"^[A-Z]\d{2}$")


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


def render() -> None:
    st.markdown("### 📤 EIS Management")
    st.caption("Export EIS data packages · Revision control · Prefect orchestration")

    require_admin()

    # ── Active Export Deployments ─────────────────────────────────────────────
    section("Active Export Deployments")
    if st.button("⟳", key="eis_dep_refresh", help="Refresh deployment list"):
        st.rerun()
    df_deps = _fetch_export_deployments()
    if not df_deps.empty:
        st.dataframe(df_deps, use_container_width=True, hide_index=True)
    else:
        st.caption("⚠ No export deployments found in Prefect — run `python scripts/deploy_all.py` to register them.")

    # ── Individual Export ─────────────────────────────────────────────────────
    section("Individual Export")
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        sel_id = st.radio(
            "Export",
            [f["id"] for f in EXPORT_FLOWS],
            format_func=lambda x: next(f["name"] for f in EXPORT_FLOWS if f["id"] == x),
            key="eis_radio",
            label_visibility="collapsed",
        )
        sel = next(f for f in EXPORT_FLOWS if f["id"] == sel_id)
        st.caption(f"Output: `{sel['file_tmpl']}`")

    with col_r:
        rev = st.text_input("Document revision", value="A35", help="Format: [A-Z]\\d{2} e.g. A35")
        fmt = st.selectbox("Output format", ["CSV", "XLSX"], key="eis_fmt")
        dest = st.radio(
            "Destination",
            ["⬇ Browser download (direct query)", "💾 Server-side via Prefect flow"],
            key="eis_dest",
        )
        server_side = dest.startswith("💾")
        out_dir = st.text_input("Server directory", value=EIS_EXPORT_DIR) if server_side else None

        rev_err = None if _REV_RE.match(rev) else f"Invalid revision '{rev}' — expected e.g. A35"
        if rev_err:
            st.warning(rev_err)

        if st.button("▶ Run Export", type="primary", use_container_width=True,
                     disabled=bool(rev_err), key="btn_eis_single"):
            _trigger_or_download([sel], rev, fmt, server_side, out_dir)

    # ── Full EIS Package Export ───────────────────────────────────────────────
    section("Full EIS Package Export")
    st.caption("Triggers all registered export deployments via Prefect in sequence.")

    live_flows = [f for f in EXPORT_FLOWS if f["live"]]
    pkg_rev = st.text_input(
        "Package revision", value="A35",
        help="Format: [A-Z]\\d{2} — applied to all exports", key="eis_pkg_rev",
    )
    pkg_rev_err = None if _REV_RE.match(pkg_rev) else f"Invalid revision '{pkg_rev}'"
    if pkg_rev_err:
        st.warning(pkg_rev_err)

    st.caption(
        f"{len(live_flows)} flows will be triggered: "
        + " · ".join(f["name"] for f in live_flows)
    )

    if st.button("▶ Export Full EIS Package", type="primary", use_container_width=True,
                 disabled=bool(pkg_rev_err), key="btn_eis_pkg"):
        _trigger_or_download(live_flows, pkg_rev, "CSV", server_side=True, out_dir=None)

    # ── Execution Log ─────────────────────────────────────────────────────────
    section("Execution Log")
    render_log("eis_log")
    if st.button("Clear", key="eis_clr"):
        st.session_state["eis_log"] = []
        st.rerun()


def _trigger_or_download(
    flows: list[dict],
    rev: str,
    fmt: str,
    server_side: bool,
    out_dir: str | None,
) -> None:
    for f in flows:
        if server_side:
            params: dict = {"doc_revision": rev}
            if out_dir:
                params["output_dir"] = out_dir
            log("info", f"Triggering: {f['name']} rev={rev}", "eis_log")
            result = trigger_deployment(f["deployment"], params)
            if result and "id" in result:
                log("ok", f"Scheduled — ID: {result['id'][:8]}", "eis_log")
                st.success(f"✓ {f['name']} · `{result['id'][:8]}`")
            else:
                log("err", str(result), "eis_log")
                st.error(str(result))
        else:
            df = _quick_query(f["id"])
            if not df.empty:
                _download(df, f["file_tmpl"].format(rev=rev), fmt)


def _quick_query(eid: str) -> pd.DataFrame:
    """Direct DB query for browser-side download (no Prefect, no audit)."""
    if eid == "tag_register":
        return db_read("""
            SELECT pl.code AS PLANT_CODE, t.tag_name AS TAG_NAME,
                   t.tag_status AS TAG_STATUS, a.code AS AREA_CODE,
                   c.name AS TAG_CLASS_NAME, t.object_status
            FROM   project_core.tag t
            LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
            LEFT JOIN reference_core.area  a  ON a.id = t.area_id
            LEFT JOIN ontology_core.class  c  ON c.id = t.class_id
            WHERE  t.object_status = 'Active' ORDER BY t.tag_name
        """)
    if eid == "equipment_register":
        return db_read("""
            SELECT pl.code AS PLANT_CODE, t.tag_name AS TAG_NAME,
                   t.equip_no AS EQUIPMENT_NUMBER, t.tag_status,
                   a.code AS AREA_CODE, c.name AS TAG_CLASS_NAME
            FROM   project_core.tag t
            LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
            LEFT JOIN reference_core.area  a  ON a.id = t.area_id
            LEFT JOIN ontology_core.class  c  ON c.id = t.class_id
            WHERE  t.object_status = 'Active' AND t.equip_no IS NOT NULL
            ORDER  BY t.tag_name
        """)
    return pd.DataFrame()


def _download(df: pd.DataFrame, filename: str, fmt: str) -> None:
    if fmt == "CSV":
        st.download_button(
            "⬇ Download CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=filename,
            mime="text/csv",
            key=f"dl_{filename}",
        )
    else:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False)
        st.download_button(
            "⬇ Download XLSX",
            data=buf.getvalue(),
            file_name=filename.replace(".CSV", ".xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_{filename}_xl",
        )
