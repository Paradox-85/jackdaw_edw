"""
ui/pages/etl_import.py — ETL Import control. ADMIN ONLY.

IMPLEMENTED (deployments confirmed in repo):
  - sequential-master-sync   (main_sync.py → main_sync_flow.serve())
  - export-tag-register      (export_tag_register.py → .serve())
  - export-equipment-register (export_equipment_register.py → .serve())

UNDER CONSTRUCTION:
  - sync-tag-data standalone deployment
  - sync-doc-data standalone deployment
  - seed-reference-data deployment
  - tag-parent-resolution standalone deployment
"""
from __future__ import annotations
import streamlit as st
from ui.common import (
    ADMIN_LINKS, badge, db_read, log, recent_flow_runs,
    render_log, require_admin, section, trigger_deployment,
)

# Only include deployments confirmed to exist in the repo
IMPORT_FLOWS = [
    {
        "id":   "master_sync",
        "name": "Master Data Sync",
        "desc": "SEQUENTIAL: Docs → Tags → Hierarchy → Properties\n"
                "Deployment: sequential-master-sync",
        "deployment": "1_sequential-master-sync",
        "live": True,
    },
]

# Planned but not yet serving as standalone deployments
PLANNED_FLOWS = [
    {"name": "Tag Sync only",            "deployment": "2_sync-tag-data"},
    {"name": "Document Sync (MDR)",      "deployment": "3_sync-doc-data"},
    {"name": "Property Values Sync",     "deployment": "4_sync-property-values"},
    {"name": "Seed Reference Data",      "deployment": "5_seed-reference-data"},
    {"name": "Tag Hierarchy Resolution", "deployment": "6_tag-parent-resolution"},
]


def render() -> None:
    st.markdown("### 📥 ETL Import")
    st.caption("Trigger Prefect import flows · Monitor run statistics")

    require_admin()  # 🔒 gate — stops rendering if not admin

    # Quick links to infra
    c1, c2, _ = st.columns([1, 1, 5])
    c1.link_button("⚡ Prefect UI", ADMIN_LINKS["Prefect UI"], use_container_width=True)
    c2.link_button("🗄️ DbGate",   ADMIN_LINKS["DbGate"],   use_container_width=True)

    st.markdown("---")
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        section("Available Import Flows")

        for flow in IMPORT_FLOWS:
            with st.container():
                st.markdown(f"**{flow['name']}**")
                st.caption(flow["desc"])
                if st.button("▶  Trigger", key=f"btn_imp_{flow['id']}",
                             type="primary", use_container_width=True):
                    log("info", f"Triggering: {flow['name']}", "imp_log")
                    result = trigger_deployment(flow["deployment"], {})
                    if result and "id" in result:
                        log("ok", f"Scheduled — ID: {result['id'][:8]}", "imp_log")
                        st.success(f"✓ Run ID: `{result['id'][:8]}`")
                        st.cache_data.clear()
                    else:
                        log("err", str(result), "imp_log")
                        st.error(str(result))

        # Planned flows shown as disabled stubs
        section("Planned (Under Construction)")
        for pf in PLANNED_FLOWS:
            st.markdown(
                f'<span style="color:#8B949E;font-size:12px">🚧 {pf["name"]}</span> '
                f'<code style="font-size:10px;color:#444">{pf["deployment"]}</code>',
                unsafe_allow_html=True,
            )

    with col_r:
        section("Execution Log")
        render_log("imp_log")
        if st.button("Clear log", key="imp_clear"):
            st.session_state["imp_log"] = []; st.rerun()

    # ── Audit stats ──────────────────────────────────────────────────────────
    section("Import History — audit_core.sync_run_stats")
    col_ref, _ = st.columns([1, 8])
    if col_ref.button("⟳", key="imp_stats_ref"):
        st.cache_data.clear(); st.rerun()

    df = db_read("""
        SELECT
            s.run_id::text                                          AS "Run ID",
            s.target_table                                          AS "Table",
            TO_CHAR(s.start_time,'YYYY-MM-DD HH24:MI:SS')          AS "Started",
            ROUND(EXTRACT(EPOCH FROM (s.end_time-s.start_time)))::text||'s' AS "Dur",
            s.count_created   AS "New",
            s.count_updated   AS "Updated",
            s.count_unchanged AS "Unchanged",
            s.count_deleted   AS "Deleted",
            s.count_errors    AS "Errors"
        FROM   audit_core.sync_run_stats s
        ORDER  BY s.start_time DESC
        LIMIT  30
    """, admin=True)

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True, height=360)
    else:
        st.info("No records in audit_core.sync_run_stats.")

    # ── Recent Prefect runs ──────────────────────────────────────────────────
    section("Recent Prefect Runs")
    runs = recent_flow_runs(8)
    if not runs.empty:
        display = runs.copy()
        display["State"] = display["State"].apply(badge)
        st.markdown(display.to_html(escape=False, index=False), unsafe_allow_html=True)
