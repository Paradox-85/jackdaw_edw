"""
ui/pages/tag_history.py — SCD audit trail. Real data from audit_core.tag_status_history.
"""
from __future__ import annotations
import io
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from ui.common import db_read, section

_STATUS_CLR = {
    "New":        "#3FB950",
    "Updated":    "#58A6FF",
    "Extended":   "#58A6FF",
    "Reduced":    "#D29922",
    "Deleted":    "#F85149",
    "No Changes": "#8B949E",
}


def render() -> None:
    st.markdown("### 📋 Tag History")
    st.caption("SCD audit trail · `audit_core.tag_status_history`")

    # ── Timeline chart ────────────────────────────────────────────────────────
    section("Tag Activity Timeline")
    df_chart = db_read("""
        SELECT DATE(sync_timestamp) AS dt,
               sync_status          AS status,
               COUNT(*)             AS cnt
        FROM audit_core.tag_status_history
        GROUP BY DATE(sync_timestamp), sync_status
        ORDER BY dt
    """)
    if not df_chart.empty:
        df_pivot = df_chart.pivot(index="dt", columns="status", values="cnt").fillna(0)
        st.bar_chart(df_pivot, height=160)

    # ── Filters ───────────────────────────────────────────────────────────────
    section("Filters")
    f1, f2, f3 = st.columns([2, 2, 2])
    search  = f1.text_input("Tag name (contains)", placeholder="JDA-21-", key="th_s")
    status_opts = ["All", "New", "Updated", "Extended", "Reduced", "Deleted", "No Changes"]
    status  = f2.selectbox("Status", status_opts, key="th_st")
    periods = {
        "Last 24h":    timedelta(hours=24),
        "Last 7 days": timedelta(days=7),
        "Last 30 days": timedelta(days=30),
        "All time":    None,
    }
    period = f3.selectbox("Period", list(periods.keys()), index=1, key="th_p")

    # SECURITY NOTE: {w} contains only hardcoded WHERE clauses assembled from
    # selectbox constants and ILIKE bind parameters. All user input uses
    # SQLAlchemy :param binding. Do NOT add user-controlled strings to `where`
    # list directly.
    limit = 10000  # hard cap to avoid OOM; no UI selector
    where, p = [], {"lim": limit}
    if search:
        where.append("h.tag_name ILIKE :ts")
        p["ts"] = f"%{search}%"
    if status != "All":
        where.append("h.sync_status = :ss")
        p["ss"] = status
    if periods[period]:
        where.append("h.sync_timestamp >= :since")
        p["since"] = datetime.now() - periods[period]
    w = ("WHERE " + " AND ".join(where)) if where else ""

    # Add LAG to detect tag name changes per source_id
    df = db_read(f"""
        SELECT
            h.tag_name                                       AS "Tag Name",
            TO_CHAR(h.sync_timestamp,'YYYY-MM-DD HH24:MI:SS') AS "Timestamp",
            h.sync_status                                    AS "Status",
            t.area_code_raw                                  AS "Area",
            t.discipline_code_raw                            AS "Discipline",
            LAG(h.tag_name) OVER (PARTITION BY h.source_id ORDER BY h.sync_timestamp) AS prev_name
        FROM   audit_core.tag_status_history h
        LEFT JOIN project_core.tag t ON t.id = h.tag_id
        {w}
        ORDER  BY h.sync_timestamp DESC
        LIMIT  :lim
    """, p)

    # Compute Name Changed flag
    if not df.empty and "prev_name" in df.columns:
        df["Name Changed"] = df.apply(
            lambda r: "YES" if pd.notna(r.get("prev_name")) and r["Tag Name"] != r.get("prev_name")
            else "NO",
            axis=1,
        )
        df = df.drop(columns=["prev_name"])
        # Sort: rows with name changes (YES) first
        df = df.sort_values("Name Changed", ascending=True)  # NO < YES alphabetically → NO first

    cr, cdl, _ = st.columns([1, 1, 6])
    if cr.button("⟳", key="th_ref"):
        st.cache_data.clear()
        st.rerun()

    if df.empty:
        st.info("No records match current filters.")
    else:
        # XLSX export
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w_xl:
            df.to_excel(w_xl, index=False, sheet_name="Tag History")
        cdl.download_button(
            "⬇ XLSX",
            data=buf.getvalue(),
            file_name=f"tag_history_{datetime.now():%Y%m%d_%H%M}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="th_dl",
        )

        st.caption(f"{len(df):,} rows" + (" (limit)" if len(df) == limit else ""))

        def _highlight_name_change(row: pd.Series):
            if row.get("Name Changed") == "NO":
                return ["color: #F85149"] * len(row)
            return [""] * len(row)

        styled = df.style.applymap(
            lambda v: f"color:{_STATUS_CLR.get(v, '#C9D1D9')};font-weight:500",
            subset=["Status"],
        )
        if "Name Changed" in df.columns:
            styled = styled.apply(_highlight_name_change, axis=1)

        st.dataframe(styled, use_container_width=True, hide_index=True, height=440)

    # ── Tag Drill-Down ────────────────────────────────────────────────────────
    section("Tag Drill-Down")
    drill = st.text_input("Exact tag name → full chronological history", key="th_drill")
    if drill:
        df_d = db_read("""
            SELECT TO_CHAR(h.sync_timestamp,'YYYY-MM-DD HH24:MI:SS') AS "Timestamp",
                   h.sync_status AS "Status", h.row_hash AS "Hash", h.snapshot AS "Snapshot"
            FROM   audit_core.tag_status_history h
            JOIN   project_core.tag t ON t.id = h.tag_id
            WHERE  t.tag_name = :tn ORDER BY h.sync_timestamp ASC
        """, {"tn": drill})
        if df_d.empty:
            st.warning(f"No history for `{drill}`")
        else:
            st.caption(f"{len(df_d)} events")
            st.dataframe(
                df_d.drop(columns=["Snapshot"]).style.applymap(
                    lambda v: f"color:{_STATUS_CLR.get(v, '#C9D1D9')}",
                    subset=["Status"],
                ),
                use_container_width=True,
                hide_index=True,
            )
            snaps = df_d["Snapshot"].dropna()
            if not snaps.empty:
                with st.expander("Latest Snapshot (JSONB)"):
                    st.json(snaps.iloc[-1])
