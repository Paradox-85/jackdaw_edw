"""
ui/pages/validation.py — Validation statistics (real data) + flow trigger (stub).
Real: audit_core.validation_result + export_validation_rule queries.
Stub: validation flow deployments don't exist yet as standalone Prefect deployments.
"""
from __future__ import annotations
import io
import pandas as pd
import streamlit as st
from ui.common import db_read, is_admin, section, wip


def render() -> None:
    st.markdown("### ✅ Validation")
    st.caption("QA statistics · `audit_core.validation_result` · `export_validation_rule`")

    # ── Stats (real — available to all users) ────────────────────────────────
    section("Latest Session — Tier Breakdown")

    df_tier = db_read("""
        WITH latest AS (
            SELECT session_id FROM audit_core.validation_result
            ORDER BY run_time DESC LIMIT 1
        )
        SELECT
            COALESCE(vr.tier,'—')     AS "Tier",
            vr.severity               AS "Severity",
            COUNT(*)                  AS "Violations",
            COUNT(*) FILTER (WHERE vr.is_resolved)     AS "Resolved",
            COUNT(*) FILTER (WHERE NOT vr.is_resolved) AS "Open"
        FROM audit_core.validation_result vr
        JOIN latest l ON l.session_id=vr.session_id
        GROUP BY vr.tier, vr.severity
        ORDER BY vr.tier NULLS LAST, vr.severity
    """)

    if not df_tier.empty:
        df_tags = db_read("SELECT COUNT(*) AS n FROM project_core.tag WHERE object_status='Active'")
        n_tags  = int(df_tags["n"].iloc[0]) if not df_tags.empty else 0
        n_viol  = int(df_tier["Violations"].sum())
        pct     = round(n_viol/n_tags*100,1) if n_tags else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("Tags checked", f"{n_tags:,}")
        c2.metric("Violations",   f"{n_viol:,}")
        c3.metric("Error rate",   f"{pct}%")
        st.dataframe(df_tier, use_container_width=True, hide_index=True)
    else:
        st.info("No validation results found.")

    # ── Session history ───────────────────────────────────────────────────────
    section("Session History")
    if st.button("⟳ Refresh", key="val_ref"): st.cache_data.clear(); st.rerun()

    df_sess = db_read("""
        SELECT session_id::text AS "Session ID",
               TO_CHAR(MIN(run_time),'YYYY-MM-DD HH24:MI') AS "Run Time",
               COUNT(*) AS "Total",
               COUNT(*) FILTER (WHERE severity='Critical') AS "Critical",
               COUNT(*) FILTER (WHERE severity='Warning')  AS "Warnings",
               COUNT(*) FILTER (WHERE is_resolved)         AS "Resolved",
               COUNT(*) FILTER (WHERE NOT is_resolved)     AS "Open"
        FROM   audit_core.validation_result
        GROUP  BY session_id ORDER BY MIN(run_time) DESC LIMIT 15
    """)

    if not df_sess.empty:
        st.dataframe(df_sess, use_container_width=True, hide_index=True)

        sel_sid = st.selectbox("Show detail for session", df_sess["Session ID"].tolist(), key="val_sid")
        df_det  = db_read("""
            SELECT tier AS "Tier", severity AS "Severity", rule_code AS "Rule",
                   object_name AS "Object", column_name AS "Column",
                   violation_detail AS "Detail", is_resolved AS "Resolved"
            FROM   audit_core.validation_result WHERE session_id=:sid
            ORDER  BY tier NULLS LAST, severity, rule_code
        """, {"sid": sel_sid})

        if not df_det.empty:
            st.caption(f"{len(df_det):,} violations")
            st.dataframe(df_det, use_container_width=True, hide_index=True, height=320)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_det.to_excel(w, index=False, sheet_name="Violations")
            st.download_button("⬇ Download XLSX", data=buf.getvalue(),
                file_name=f"val_{sel_sid[:8]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="val_dl")
    else:
        st.info("No sessions yet.")

    # ── Flow trigger — admin + wip ────────────────────────────────────────────
    section("Run Validation Flow")
    if is_admin():
        st.markdown("""
        <div style="background:#1C2128;border:1px dashed #21262D;border-radius:6px;
                    padding:16px;color:#8B949E;font-size:13px">
        <strong style="color:#D29922">🚧 Validation flow deployments not registered yet</strong><br><br>
        Planned deployments: <code>validation-full-scan</code>, <code>validation-basic-scan</code><br>
        These will appear here once registered via <code>prefect deploy</code>.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("_Validation flow triggers available to admin users._")

    # ── Rule catalogue ────────────────────────────────────────────────────────
    section("Validation Rule Catalogue")
    with st.expander("View rules — audit_core.export_validation_rule"):
        df_rules = db_read("""
            SELECT tier AS "Tier", category AS "Category", rule_code AS "Rule",
                   scope AS "Scope", severity AS "Severity", check_type AS "Type",
                   description AS "Description", is_builtin AS "Built-in",
                   is_blocking AS "Blocking"
            FROM   audit_core.export_validation_rule
            ORDER  BY tier NULLS LAST, sort_order NULLS LAST, rule_code
        """)
        if not df_rules.empty:
            st.caption(f"{len(df_rules)} rules")
            st.dataframe(df_rules, use_container_width=True, hide_index=True)
        else:
            st.info("No rules — run migration_003 to seed the catalogue.")
