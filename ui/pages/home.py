"""
ui/pages/home.py — Dashboard: KPIs, service health, recent runs, tag analytics.
Read-only queries only. No write operations except admin sync trigger.
"""
from __future__ import annotations
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from ui.common import (
    ADMIN_LINKS, badge, db_read, is_admin,
    prefect_get, ollama_models, recent_flow_runs, section, trigger_deployment,
)
from ui.version import version_string

# Path to docker-compose.yml — configurable via env for Docker deployments
_DOCKER_COMPOSE_PATH = os.getenv(
    "DOCKER_COMPOSE_PATH",
    "/mnt/shared-data/ram-user/Jackdaw/EDW-repository/docker/jackdaw-edw_docker-compose.yml",
)


# ─── Cached KPI queries (ttl=60s to avoid hammering DB on every rerun) ────────
@st.cache_data(ttl=60, show_spinner=False)
def _kpi_tags() -> int | None:
    df = db_read("SELECT COUNT(*) AS n FROM project_core.tag WHERE object_status='Active'")
    return int(df["n"].iloc[0]) if not df.empty else None


@st.cache_data(ttl=60, show_spinner=False)
def _kpi_docs() -> int | None:
    df = db_read("SELECT COUNT(*) AS n FROM project_core.document WHERE object_status='Active'")
    return int(df["n"].iloc[0]) if not df.empty else None


@st.cache_data(ttl=60, show_spinner=False)
def _kpi_last_sync() -> str:
    df = db_read("SELECT MAX(end_time) AS ts FROM audit_core.sync_run_stats WHERE end_time IS NOT NULL")
    if df.empty:
        return "—"
    last_ts = df["ts"].iloc[0]
    if last_ts is None or pd.isna(last_ts):
        return "—"
    mins = int((pd.Timestamp.now() - pd.to_datetime(last_ts)).total_seconds() / 60)
    return f"{mins}m ago" if mins < 60 else f"{mins // 60}h ago"


@st.cache_data(ttl=60, show_spinner=False)
def _kpi_violations() -> int | None:
    df = db_read("""
        SELECT COUNT(*) AS n FROM audit_core.validation_result
        WHERE is_resolved = false AND run_time >= NOW() - INTERVAL '7 days'
    """)
    return int(df["n"].iloc[0]) if not df.empty else None


@st.cache_data(ttl=60, show_spinner=False)
def _kpi_prev_tags() -> int | None:
    df = db_read("""
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
    return int(df["n"].iloc[0]) if not df.empty else None


def render() -> None:
    st.markdown("### 🐦 Jackdaw EDW — Control Center")
    st.caption(f"Plant **JDA** · engineering_core · `{version_string()}`")

    # ── Disclaimer ────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="disclaimer">🔒 <strong>Internal Use Only</strong> — '
        'This system is for Jackdaw project internal use only. '
        'All data is stored on local servers and must not be used outside the project scope.</div>',
        unsafe_allow_html=True,
    )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    section("System Metrics")

    n_tags  = _kpi_tags()
    n_docs  = _kpi_docs()
    sync_str = _kpi_last_sync()
    n_viol  = _kpi_violations()
    n_prev  = _kpi_prev_tags()

    tag_delta = (n_tags - n_prev) if (isinstance(n_tags, int) and isinstance(n_prev, int)) else None

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

    # ── Service health ────────────────────────────────────────────────────────
    section("Service Health")
    prefect_ok = prefect_get("/health") is not None
    ollama_ok  = bool(ollama_models())
    db_ok      = not db_read("SELECT 1").empty

    h1, h2, h3 = st.columns(3)
    h1.markdown(f"{'🟢' if db_ok else '🔴'} **PostgreSQL** `engineering_core`")
    h2.markdown(f"{'🟢' if prefect_ok else '🔴'} **Prefect API**")
    h3.markdown(f"{'🟢' if ollama_ok else '🔴'} **Ollama**")

    # ── Admin quick links ─────────────────────────────────────────────────────
    if is_admin():
        section("Admin — Infra Links")
        cols = st.columns(len(ADMIN_LINKS))
        for i, (name, url) in enumerate(ADMIN_LINKS.items()):
            cols[i].link_button(name, url, use_container_width=True)

    # ── Admin Quick Sync ──────────────────────────────────────────────────────
    if is_admin():
        section("Admin — Quick Sync")
        col_s1, col_s2, col_s3 = st.columns([1, 1, 4])

        if col_s1.button("▶ Sync Tag Data", type="primary", key="home_sync_tags"):
            result = trigger_deployment("1_sequential-master-sync", {})
            if result and "id" in result:
                st.toast(f"✓ Sync scheduled — {result['id'][:8]}", icon="✅")
            else:
                st.toast(f"✗ Failed: {result}", icon="❌")

        if col_s2.button("▶ Sync Ref Data", key="home_sync_ref", disabled=True,
                         help="Planned — run via Prefect UI"):
            pass  # stub: Phase 2

        # Last 5 sync runs from audit log
        df_recent = db_read("""
            SELECT target_table AS "Table",
                   COALESCE(
                       NULLIF(
                           REGEXP_REPLACE(
                               COALESCE(source_file, ''),
                               '^.*?(\d{4}-\d{2}-\d{2}).*$', '\1'
                           ),
                           COALESCE(source_file, '')
                       ),
                       TO_CHAR(end_time, 'YYYY-MM-DD')
                   )              AS "File Date",
                   count_created  AS "New",
                   count_updated  AS "Updated",
                   count_deleted  AS "Deleted",
                   count_errors   AS "Errors"
            FROM audit_core.sync_run_stats
            ORDER BY start_time DESC
            LIMIT 5
        """)
        if not df_recent.empty:
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.caption("No sync history available.")

        # Download docker-compose.yml
        compose_path = Path(_DOCKER_COMPOSE_PATH)
        if compose_path.exists():
            st.download_button(
                "⬇ Download docker-compose.yml",
                data=compose_path.read_bytes(),
                file_name="docker-compose.yml",
                mime="text/yaml",
                key="dl_compose",
            )
        else:
            st.caption(f"docker-compose.yml not found at `{_DOCKER_COMPOSE_PATH}`")

    # ── Recent Prefect runs ───────────────────────────────────────────────────
    section("Recent Flow Runs")
    col_r, _ = st.columns([1, 8])
    if col_r.button("⟳", key="home_refresh", help="Refresh"):
        st.cache_data.clear()
        st.rerun()

    runs = recent_flow_runs(10)
    if not runs.empty:
        display = runs.copy()
        display["State"] = display["State"].apply(badge)
        st.markdown(display.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.caption("No recent runs — Prefect may be unreachable.")

    # ── Last sync stats ───────────────────────────────────────────────────────
    section("Last Sync Run — Statistics")
    df_stats = db_read("""
        SELECT
            target_table                                                    AS "Table",
            TO_CHAR(start_time,'YYYY-MM-DD HH24:MI')                       AS "Started",
            ROUND(EXTRACT(EPOCH FROM (end_time - start_time)))::text || 's' AS "Duration",
            count_created   AS "New",
            count_updated   AS "Updated",
            count_unchanged AS "Unchanged",
            count_deleted   AS "Deleted",
            count_errors    AS "Errors"
        FROM audit_core.sync_run_stats
        WHERE run_id = (
            SELECT run_id FROM audit_core.sync_run_stats
            WHERE end_time IS NOT NULL
            ORDER BY start_time DESC LIMIT 1
        )
        ORDER BY target_table
    """)
    if not df_stats.empty:
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
        if df_stats["Table"].nunique() == 1:
            st.warning(
                "⚠ Only one table row found. "
                "Check that Prefect flow writes per-table rows to `audit_core.sync_run_stats`, "
                "not a single aggregate row."
            )
    else:
        st.caption("No sync run data found.")

    # ── Tag Analytics ─────────────────────────────────────────────────────────
    section("Tag Analytics")
    col_ts, col_dc, col_ss = st.columns(3)

    df_tag_status = db_read("""
        SELECT tag_status AS "Status", COUNT(*) AS "Count"
        FROM project_core.tag
        WHERE object_status = 'Active'
        GROUP BY tag_status
        ORDER BY COUNT(*) DESC
    """)
    with col_ts:
        st.caption("**By Tag Status**")
        if not df_tag_status.empty:
            st.dataframe(df_tag_status, use_container_width=True, hide_index=True)

    df_company = db_read("""
        SELECT COALESCE(t.design_company_name_raw, '—') AS "Company",
               COUNT(*) AS "Count"
        FROM project_core.tag t
        WHERE t.object_status = 'Active'
        GROUP BY t.design_company_name_raw
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    with col_dc:
        st.caption("**By Design Company**")
        if not df_company.empty:
            st.dataframe(df_company, use_container_width=True, hide_index=True)

    df_sync_status = db_read("""
        SELECT sync_status AS "Sync Status", COUNT(*) AS "Count"
        FROM project_core.tag
        WHERE object_status = 'Active'
        GROUP BY sync_status
        ORDER BY COUNT(*) DESC
    """)
    with col_ss:
        st.caption("**By Sync Status**")
        if not df_sync_status.empty:
            st.dataframe(df_sync_status, use_container_width=True, hide_index=True)

    # Active Tag-Doc Links count
    df_tagdoc = db_read("""
        SELECT COUNT(*) AS n
        FROM mapping.tag_document m
        JOIN project_core.tag t ON t.id = m.tag_id
        JOIN project_core.document d ON d.id = m.document_id
        WHERE t.object_status = 'Active'
          AND t.tag_status NOT IN ('VOID')
          AND t.tag_status IS NOT NULL
          AND d.status != 'CAN'
          AND d.mdr_flag = TRUE
          AND m.mapping_status = 'Active'
    """)
    n_tagdoc = int(df_tagdoc["n"].iloc[0]) if not df_tagdoc.empty else None
    st.metric(
        "Active Tag-Doc Links",
        f"{n_tagdoc:,}" if isinstance(n_tagdoc, int) else "—",
        help="mdr_flag=true, tag_status≠VOID, doc_status≠CAN",
    )

    # ── Tag Growth Timeline ───────────────────────────────────────────────────
    section("Tag Growth Timeline")
    df_timeline = db_read("""
        SELECT
            DATE(sync_timestamp)                                       AS dt,
            COUNT(*) FILTER (WHERE sync_status = 'New')     AS "New",
            COUNT(*) FILTER (WHERE sync_status = 'Updated') AS "Updated",
            COUNT(*) FILTER (WHERE sync_status = 'Deleted') AS "Deleted"
        FROM audit_core.tag_status_history
        GROUP BY DATE(sync_timestamp)
        ORDER BY dt
    """)
    if not df_timeline.empty:
        df_timeline["dt"] = pd.to_datetime(df_timeline["dt"])
        st.line_chart(df_timeline.set_index("dt")[["New", "Updated", "Deleted"]])
    else:
        st.caption("No timeline data in audit_core.tag_status_history.")

    # ── Tag Name Changes (all time) ────────────────────────────────────────────
    section("Tag Name Changes")
    with st.expander("🔄 Tag Name Changes — all time (click to expand)", expanded=False):
        df_name_changes = db_read("""
            WITH ranked AS (
                SELECT
                    h.source_id,
                    h.tag_name,
                    h.sync_timestamp,
                    LAG(h.tag_name) OVER (PARTITION BY h.source_id ORDER BY h.sync_timestamp) AS prev_name
                FROM audit_core.tag_status_history h
                JOIN project_core.tag t ON t.source_id = h.source_id
                WHERE t.object_status = 'Active'
            )
            SELECT
                source_id                                      AS "Source ID",
                prev_name                                      AS "Name (was)",
                tag_name                                       AS "Name (now)",
                TO_CHAR(sync_timestamp, 'YYYY-MM-DD HH24:MI') AS "Changed At"
            FROM ranked
            WHERE prev_name IS NOT NULL
              AND prev_name != tag_name
            ORDER BY sync_timestamp DESC
        """)
        if df_name_changes.empty:
            st.success("✓ No tag name changes found.")
        else:
            st.warning(f"⚠ {len(df_name_changes)} tag name change(s) detected")
            st.dataframe(df_name_changes, use_container_width=True, hide_index=True)
