"""
ui/pages/eis_export.py — EIS Export. ADMIN ONLY.
Confirmed deployments (matching etl/flows/*.serve() names):
  export-tag-register-deployment
  export-equipment-register-deployment
"""
from __future__ import annotations
import io, re
import pandas as pd
import streamlit as st
from ui.common import (
    EIS_EXPORT_DIR, db_read, log, render_log,
    require_admin, section, trigger_deployment,
)

EXPORT_FLOWS = [
    {
        "id": "tag_register",
        "name": "Tag Register (seq 003)",
        "file_tmpl": "JDAW-KVE-E-JA-6944-00001-003-{rev}.CSV",
        "deployment": "export-tag-register-deployment",
        "live": True,
    },
    {
        "id": "equipment_register",
        "name": "Equipment Register (seq 004)",
        "file_tmpl": "JDAW-KVE-E-JA-6944-00001-004-{rev}.CSV",
        "deployment": "export-equipment-register-deployment",
        "live": True,
    },
]

_REV = re.compile(r"^[A-Z]\d{2}$")


def render() -> None:
    st.markdown("### 📤 EIS Export")
    st.caption("Generate EIS data packages · Revision control")

    require_admin()

    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        section("Select Export")
        sel_id = st.radio("Export", [f["id"] for f in EXPORT_FLOWS],
                          format_func=lambda x: next(f["name"] for f in EXPORT_FLOWS if f["id"]==x),
                          key="eis_radio", label_visibility="collapsed")
        sel = next(f for f in EXPORT_FLOWS if f["id"]==sel_id)
        st.caption(f"Output: `{sel['file_tmpl']}`")

        pkg_all = st.checkbox("Package: run all export flows", value=False, key="eis_pkg")

    with col_r:
        section("Parameters")
        rev = st.text_input("Document revision", value="A35", help="Format: [A-Z]\\d{2}")
        fmt = st.selectbox("Output format", ["CSV","XLSX"], key="eis_fmt")
        dest = st.radio("Destination",
                        ["⬇ Browser download (direct query)",
                         "💾 Server-side via Prefect flow"],
                        key="eis_dest")
        server_side = dest.startswith("💾")
        if server_side:
            out_dir = st.text_input("Server directory", value=EIS_EXPORT_DIR)
        else:
            out_dir = None

        rev_err = None if _REV.match(rev) else f"Invalid revision '{rev}' — expected e.g. A35"
        if rev_err: st.warning(rev_err)

        if st.button("▶  Run Export", type="primary", use_container_width=True,
                     disabled=bool(rev_err), key="btn_eis"):
            flows = EXPORT_FLOWS if pkg_all else [sel]
            for f in flows:
                if server_side:
                    params = {"doc_revision": rev}
                    if out_dir: params["output_dir"] = out_dir
                    log("info", f"Triggering: {f['name']} rev={rev}", "eis_log")
                    result = trigger_deployment(f["deployment"], params)
                    if result and "id" in result:
                        log("ok", f"Scheduled — ID: {result['id'][:8]}", "eis_log")
                        st.success(f"✓ {f['name']} · `{result['id'][:8]}`")
                    else:
                        log("err", str(result), "eis_log")
                        st.error(str(result))
                else:
                    # Direct query download (no Prefect, no audit log)
                    df = _quick_query(f["id"])
                    if not df.empty:
                        _download(df, f["file_tmpl"].format(rev=rev), fmt)

    section("Execution Log")
    render_log("eis_log")
    if st.button("Clear", key="eis_clr"): st.session_state["eis_log"]=[]; st.rerun()


def _quick_query(eid: str) -> pd.DataFrame:
    if eid == "tag_register":
        return db_read("""
            SELECT pl.code AS PLANT_CODE, t.tag_name AS TAG_NAME,
                   t.tag_status AS TAG_STATUS, a.code AS AREA_CODE,
                   c.name AS TAG_CLASS_NAME, t.object_status
            FROM   project_core.tag t
            LEFT JOIN reference_core.plant pl ON pl.id=t.plant_id
            LEFT JOIN reference_core.area  a  ON a.id=t.area_id
            LEFT JOIN ontology_core.class  c  ON c.id=t.class_id
            WHERE  t.object_status='Active' ORDER BY t.tag_name
        """)
    if eid == "equipment_register":
        return db_read("""
            SELECT pl.code AS PLANT_CODE, t.tag_name AS TAG_NAME,
                   t.equip_no AS EQUIPMENT_NUMBER, t.tag_status,
                   a.code AS AREA_CODE, c.name AS TAG_CLASS_NAME
            FROM   project_core.tag t
            LEFT JOIN reference_core.plant pl ON pl.id=t.plant_id
            LEFT JOIN reference_core.area  a  ON a.id=t.area_id
            LEFT JOIN ontology_core.class  c  ON c.id=t.class_id
            WHERE  t.object_status='Active' AND t.equip_no IS NOT NULL
            ORDER  BY t.tag_name
        """)
    return pd.DataFrame()


def _download(df: pd.DataFrame, filename: str, fmt: str) -> None:
    if fmt == "CSV":
        st.download_button("⬇ Download CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=filename, mime="text/csv", key=f"dl_{filename}")
    else:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, index=False)
        st.download_button("⬇ Download XLSX",
            data=buf.getvalue(), file_name=filename.replace(".CSV",".xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_{filename}_xl")
