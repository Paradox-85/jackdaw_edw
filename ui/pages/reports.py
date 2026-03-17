"""
ui/pages/reports.py — Reporting engine.

IMPLEMENTED:
  - 4 master reports with real SQL against schema.sql tables
  - Parametric widgets (date pickers etc.) where SQL has :placeholders
  - CSV + XLSX download

UNDER CONSTRUCTION:
  - Dynamic report catalogue from audit_core.report_metadata
    (table doesn't exist yet — migration_006 needed)
"""
from __future__ import annotations
import io
import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from ui.common import db_read, section, wip

# ─── Master report catalogue ──────────────────────────────────────────────────
# SQL uses only tables confirmed in schema.sql.
MASTER_REPORTS = [
    {
        "id":   "tag_register",
        "name": "Master Tag Register",
        "desc": "All active tags with class, area, discipline, company",
        "params": {},
        "sql": """
            SELECT
                COALESCE(pl.code,'—')   AS "Plant",
                t.tag_name              AS "Tag Name",
                t.tag_status            AS "Status",
                COALESCE(c.name,'—')    AS "Class",
                COALESCE(a.code,'—')    AS "Area",
                COALESCE(u.code,'—')    AS "Process Unit",
                COALESCE(d.code,'—')    AS "Discipline",
                t.design_company_name_raw AS "Company",
                t.sync_status           AS "Sync Status"
            FROM   project_core.tag t
            LEFT JOIN reference_core.plant         pl ON pl.id = t.plant_id
            LEFT JOIN reference_core.area          a  ON a.id  = t.area_id
            LEFT JOIN reference_core.process_unit  u  ON u.id  = t.process_unit_id
            LEFT JOIN reference_core.discipline    d  ON d.id  = t.discipline_id
            LEFT JOIN ontology_core.class          c  ON c.id  = t.class_id
            WHERE  t.object_status = 'Active'
            ORDER  BY t.tag_name
        """,
    },
    {
        "id":   "doc_tag_mapping",
        "name": "Document–Tag Cross-Reference",
        "desc": "Active doc↔tag assignments from mapping.tag_document",
        "params": {},
        "sql": """
            SELECT
                doc.doc_number  AS "Document",
                doc.title       AS "Title",
                doc.rev         AS "Rev",
                doc.status      AS "Doc Status",
                t.tag_name      AS "Tag Name",
                m.sync_status   AS "Mapping Status"
            FROM   mapping.tag_document m
            JOIN   project_core.document doc ON doc.id = m.document_id
            JOIN   project_core.tag      t   ON t.id   = m.tag_id
            WHERE  doc.object_status = 'Active'
              AND  t.object_status   = 'Active'
              AND  m.mapping_status  = 'Active'
            ORDER  BY doc.doc_number, t.tag_name
        """,
    },
    {
        "id":   "scd_delta",
        "name": "SCD Delta (by period)",
        "desc": "Tags changed between two dates — from audit_core.tag_status_history",
        "params": {"date_from": "date", "date_to": "date"},
        "sql": """
            SELECT
                TO_CHAR(h.sync_timestamp,'YYYY-MM-DD HH24:MI:SS') AS "Timestamp",
                h.sync_status   AS "Status",
                h.tag_name      AS "Tag Name",
                h.source_id     AS "Source ID",
                h.row_hash      AS "Hash"
            FROM   audit_core.tag_status_history h
            WHERE  h.sync_timestamp BETWEEN :date_from AND :date_to
              AND  h.sync_status != 'No Changes'
            ORDER  BY h.sync_timestamp DESC
        """,
    },
    {
        "id":   "validation_summary",
        "name": "Validation Summary",
        "desc": "Open violations grouped by tier and severity (audit_core.validation_result)",
        "params": {},
        "sql": """
            SELECT
                COALESCE(vr.tier,'—')     AS "Tier",
                COALESCE(vr.category,'—') AS "Category",
                vr.severity               AS "Severity",
                vr.rule_code              AS "Rule",
                COUNT(*)                  AS "Violations",
                COUNT(*) FILTER (WHERE vr.is_resolved) AS "Resolved",
                COUNT(*) FILTER (WHERE NOT vr.is_resolved) AS "Open"
            FROM   audit_core.validation_result vr
            GROUP  BY vr.tier, vr.category, vr.severity, vr.rule_code
            ORDER  BY vr.tier NULLS LAST, COUNT(*) DESC
        """,
    },
]


def _param_widgets(params_def: dict, key_prefix: str) -> dict:
    """Render date/text inputs for SQL :placeholders. Returns {name: value}."""
    if not params_def:
        return {}
    values = {}
    cols = st.columns(min(len(params_def), 3))
    for i, (name, ptype) in enumerate(params_def.items()):
        label = name.replace("_", " ").title()
        with cols[i % len(cols)]:
            if ptype == "date":
                default = datetime.now() if "to" in name else datetime.now() - timedelta(days=30)
                values[name] = st.date_input(label, value=default, key=f"{key_prefix}_{name}")
            else:
                values[name] = st.text_input(label, key=f"{key_prefix}_{name}")
    return values


def _run_and_show(sql: str, params: dict, label: str, fmt: str) -> None:
    str_params = {k: str(v) for k, v in params.items()}
    df = db_read(sql, str_params)
    if df.empty:
        st.info("Query returned no rows.")
        return
    st.caption(f"{len(df):,} rows")
    st.dataframe(df, use_container_width=True, hide_index=True, height=440)
    _download_btn(df, label, fmt)


def _download_btn(df: pd.DataFrame, label: str, fmt: str) -> None:
    stem = label.lower().replace(" ", "_").replace("–", "")
    if fmt == "CSV":
        st.download_button("⬇ Download CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{stem}.csv", mime="text/csv", key=f"dl_{stem}")
    else:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Report")
        st.download_button("⬇ Download XLSX",
            data=buf.getvalue(), file_name=f"{stem}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_{stem}_xlsx")


def render() -> None:
    st.markdown("### 📊 Reports")
    st.caption("Master reports + dynamic catalogue · CSV / XLSX export")

    fmt = st.radio("Output format", ["CSV", "XLSX"], horizontal=True, key="rpt_fmt")

    # ── Master Reports ────────────────────────────────────────────────────────
    section("Master Reports")
    st.caption("Pre-built reports against `engineering_core`. Click ▶ to generate.")

    for rpt in MASTER_REPORTS:
        with st.expander(f"**{rpt['name']}** — {rpt['desc']}"):
            params = _param_widgets(rpt["params"], key_prefix=f"m_{rpt['id']}")
            if st.button(f"▶ Generate", key=f"btn_{rpt['id']}", type="primary"):
                _run_and_show(rpt["sql"], params, rpt["name"], fmt)

    # ── Dynamic Report Catalogue ──────────────────────────────────────────────
    section("Dynamic Report Catalogue")

    # Check if audit_core.report_metadata exists
    df_check = db_read("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='audit_core' AND table_name='report_metadata'
    """)

    if df_check.empty:
        st.markdown("""
        <div style="background:#1C2128;border:1px dashed #21262D;border-radius:6px;
                    padding:20px;margin:8px 0;color:#8B949E;font-size:13px">
        <strong style="color:#D29922">🚧 Dynamic catalogue not available</strong><br><br>
        Table <code>audit_core.report_metadata</code> does not exist yet.<br>
        Run <strong>migration_006_report_metadata.sql</strong> to enable this feature.
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 Show migration SQL"):
            st.code("""
-- migration_006_report_metadata.sql
CREATE TABLE IF NOT EXISTS audit_core.report_metadata (
    id            UUID    NOT NULL DEFAULT gen_random_uuid(),
    report_name   TEXT    NOT NULL,
    category      TEXT    NOT NULL DEFAULT 'General',
    description   TEXT    NULL,
    sql_query     TEXT    NOT NULL,
    author        TEXT    NULL,
    is_parametric BOOLEAN NOT NULL DEFAULT false,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT report_metadata_pkey     PRIMARY KEY (id),
    CONSTRAINT report_metadata_name_key UNIQUE (report_name)
);
COMMENT ON TABLE audit_core.report_metadata IS
    'Dynamic SQL report catalogue. Each row is a named, categorised SQL query '
    'executed on-demand by the EDW Control Center.';
            """, language="sql")
        return

    # Table exists — load and display catalogue
    df_cat = db_read("""
        SELECT id::text AS id, report_name AS "Name", category AS "Category",
               description AS "Description", author AS "Author",
               created_at::date AS "Created", is_parametric AS "Params",
               sql_query
        FROM   audit_core.report_metadata
        WHERE  is_active = true
        ORDER  BY category, report_name
    """)

    if df_cat.empty:
        st.info("Catalogue is empty. Seed audit_core.report_metadata with reports."); return

    f1, f2 = st.columns(2)
    search = f1.text_input("Search", placeholder="tag register…", key="dyn_search")
    cats   = ["All"] + sorted(df_cat["Category"].dropna().unique().tolist())
    cat    = f2.selectbox("Category", cats, key="dyn_cat")

    mask = pd.Series(True, index=df_cat.index)
    if search:
        mask &= df_cat["Name"].str.contains(search, case=False, na=False)
    if cat != "All":
        mask &= df_cat["Category"] == cat

    filtered = df_cat[mask]
    st.caption(f"{len(filtered)} reports")
    st.dataframe(filtered.drop(columns=["id","sql_query"]),
                 use_container_width=True, hide_index=True, height=240)

    sel_name = st.selectbox("Run report", filtered["Name"].tolist(), key="dyn_sel")
    if not sel_name: return
    sel = filtered[filtered["Name"] == sel_name].iloc[0]

    st.caption(sel["Description"])
    sql_raw = sel["sql_query"]

    # Auto-detect :param placeholders
    detected = re.findall(r":([a-zA-Z_][a-zA-Z0-9_]*)", sql_raw)
    dyn_params = {}
    if detected:
        for p in detected:
            dyn_params[p] = st.text_input(p, key=f"dp_{sel['id']}_{p}")

    if st.button("▶ Run", key=f"btn_dyn_{sel['id']}", type="primary"):
        _run_and_show(sql_raw, dyn_params, sel_name, fmt)
