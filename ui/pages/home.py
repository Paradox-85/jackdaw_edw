"""
ui/pages/home.py — Dashboard: KPIs from real tables, service health, recent runs.
Read-only queries only. No write operations.
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
from ui.common import (
    ADMIN_LINKS, badge, db_read, is_admin,
    prefect_get, ollama_models, recent_flow_runs, section,
)
from ui.version import version_string

def render() -> None:
    st.markdown("### 🐦 Jackdaw EDW — Control Center")
    st.caption(f"Plant **JDA** · engineering_core · Ryzen 7 7700 + RTX 3090 · `{version_string()}`")

    # ── KPIs ────────────────────────────────────────────────────────────────
    section("System Metrics")

    df_tags  = db_read("SELECT COUNT(*) AS n FROM project_core.tag WHERE object_status='Active'")
    df_docs  = db_read("SELECT COUNT(*) AS n FROM project_core.document WHERE object_status='Active'")
    df_sync  = db_read("SELECT MAX(end_time) AS ts FROM audit_core.sync_run_stats WHERE end_time IS NOT NULL")
    df_viol  = db_read("""
        SELECT COUNT(*) AS n FROM audit_core.validation_result
        WHERE is_resolved = false AND run_time >= NOW() - INTERVAL '7 days'
    """)

    # Delta: previous sync run tag count (for delta indicator on metric card)
    df_prev_tags = db_read("""
        WITH runs AS (
            SELECT start_time,
                   ROW_NUMBER() OVER (ORDER BY start_time DESC) AS rn
            FROM audit_core.sync_run_stats
            WHERE end_time IS NOT NULL
              AND target_table = 'project_core.tag'
        ),
        prev_run AS (SELECT start_time FROM runs WHERE rn = 2)
        SELECT COUNT(*) AS n
        FROM project_core.tag
        WHERE sync_timestamp < (SELECT start_time FROM prev_run)
          AND sync_status != 'Deleted'
    """)

    n_tags  = int(df_tags["n"].iloc[0])      if not df_tags.empty      else None
    n_docs  = int(df_docs["n"].iloc[0])      if not df_docs.empty      else None
    n_viol  = int(df_viol["n"].iloc[0])      if not df_viol.empty      else None
    n_prev  = int(df_prev_tags["n"].iloc[0]) if not df_prev_tags.empty else None
    last_ts = df_sync["ts"].iloc[0]           if not df_sync.empty      else None

    # Delta: only show if previous run data available and both counts are integers
    tag_delta = (n_tags - n_prev) if (isinstance(n_tags, int) and isinstance(n_prev, int)) else None

    if last_ts and pd.notna(last_ts):
        mins = int((pd.Timestamp.now() - pd.to_datetime(last_ts)).total_seconds() / 60)
        sync_str = f"{mins}m ago" if mins < 60 else f"{mins//60}h ago"
    else:
        sync_str = "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Active Tags",
        f"{n_tags:,}" if isinstance(n_tags, int) else "—",
        delta=tag_delta,
        delta_color="normal",
        help="Change vs previous sync run" if tag_delta is not None else None,
    )
    c2.metric("Documents",          f"{n_docs:,}" if isinstance(n_docs, int) else "—")
    c3.metric("Last Sync",          sync_str)
    c4.metric("Open Violations 7d", str(n_viol) if n_viol is not None else "—")

    # ── Service health ───────────────────────────────────────────────────────
    section("Service Health")
    prefect_ok = prefect_get("/health") is not None
    ollama_ok  = bool(ollama_models())
    db_ok      = not db_read("SELECT 1").empty

    h1, h2, h3 = st.columns(3)
    h1.markdown(f"{'🟢' if db_ok else '🔴'} **PostgreSQL** `engineering_core`")
    h2.markdown(f"{'🟢' if prefect_ok else '🔴'} **Prefect API**")
    h3.markdown(f"{'🟢' if ollama_ok else '🔴'} **Ollama** (RTX 3090)")

    # ── Admin quick links — only in admin mode ───────────────────────────────
    if is_admin():
        section("Admin — Infra Links")
        cols = st.columns(len(ADMIN_LINKS))
        for i, (name, url) in enumerate(ADMIN_LINKS.items()):
            cols[i].link_button(name, url, use_container_width=True)

    # ── Recent Prefect runs ──────────────────────────────────────────────────
    section("Recent Flow Runs")
    col_r, _ = st.columns([1, 8])
    if col_r.button("⟳", key="home_refresh", help="Refresh"):
        st.cache_data.clear(); st.rerun()

    runs = recent_flow_runs(10)
    if not runs.empty:
        display = runs.copy()
        display["State"] = display["State"].apply(badge)
        st.markdown(display.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.caption("No recent runs — Prefect may be unreachable.")

    # ── Last sync stats ──────────────────────────────────────────────────────
    section("Last Sync Run — Statistics")
    df_stats = db_read("""
        SELECT
            target_table                                    AS "Table",
            TO_CHAR(start_time,'YYYY-MM-DD HH24:MI')        AS "Started",
            ROUND(EXTRACT(EPOCH FROM (end_time-start_time)))::text||'s' AS "Duration",
            count_created   AS "New",
            count_updated   AS "Updated",
            count_unchanged AS "Unchanged",
            count_deleted   AS "Deleted",
            count_errors    AS "Errors"
        FROM audit_core.sync_run_stats
        WHERE run_id = (SELECT run_id FROM audit_core.sync_run_stats ORDER BY start_time DESC LIMIT 1)
        ORDER BY start_time
    """)
    if not df_stats.empty:
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
    else:
        st.caption("No sync run data found.")
