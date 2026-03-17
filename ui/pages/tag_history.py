"""
ui/pages/tag_history.py — SCD audit trail. Real data from audit_core.tag_status_history.
"""
from __future__ import annotations
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from ui.common import db_read, section

_STATUS_CLR = {
    "New":"#3FB950","Updated":"#58A6FF","Extended":"#58A6FF",
    "Reduced":"#D29922","Deleted":"#F85149","No Changes":"#8B949E",
}

def render() -> None:
    st.markdown("### 📋 Tag History")
    st.caption("SCD audit trail · `audit_core.tag_status_history`")

    f1, f2, f3, f4 = st.columns([2,2,2,1])
    search    = f1.text_input("Tag name (contains)", placeholder="JDA-21-", key="th_s")
    status_opts = ["All","New","Updated","Extended","Reduced","Deleted","No Changes"]
    status    = f2.selectbox("Status", status_opts, key="th_st")
    periods   = {"Last 24h":timedelta(hours=24),"Last 7 days":timedelta(days=7),
                 "Last 30 days":timedelta(days=30),"All time":None}
    period    = f3.selectbox("Period", list(periods.keys()), index=1, key="th_p")
    limit     = f4.selectbox("Rows",[100,500,1000], key="th_l")

    where, p = [], {"lim":limit}
    if search: where.append("h.tag_name ILIKE :ts"); p["ts"]=f"%{search}%"
    if status!="All": where.append("h.sync_status=:ss"); p["ss"]=status
    if periods[period]: where.append("h.sync_timestamp>=:since"); p["since"]=datetime.now()-periods[period]
    w = ("WHERE "+" AND ".join(where)) if where else ""

    df = db_read(f"""
        SELECT TO_CHAR(h.sync_timestamp,'YYYY-MM-DD HH24:MI:SS') AS "Timestamp",
               h.sync_status AS "Status", h.tag_name AS "Tag Name",
               h.source_id AS "Source ID",
               t.area_code_raw AS "Area", t.discipline_code_raw AS "Discipline",
               h.row_hash AS "Hash"
        FROM   audit_core.tag_status_history h
        LEFT JOIN project_core.tag t ON t.id=h.tag_id
        {w}
        ORDER  BY h.sync_timestamp DESC LIMIT :lim
    """, p)

    cr, cdl, _ = st.columns([1,1,6])
    if cr.button("⟳",key="th_ref"): st.cache_data.clear(); st.rerun()

    if df.empty:
        st.info("No records match current filters.")
    else:
        cdl.download_button("⬇ CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"tag_history_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv", key="th_dl")
        st.caption(f"{len(df):,} rows"+(" (limit)" if len(df)==limit else ""))
        st.dataframe(
            df.style.applymap(lambda v: f"color:{_STATUS_CLR.get(v,'#C9D1D9')};font-weight:500",
                              subset=["Status"]),
            use_container_width=True, hide_index=True, height=440)

    section("Tag Drill-Down")
    drill = st.text_input("Exact tag name → full chronological history", key="th_drill")
    if drill:
        df_d = db_read("""
            SELECT TO_CHAR(h.sync_timestamp,'YYYY-MM-DD HH24:MI:SS') AS "Timestamp",
                   h.sync_status AS "Status", h.row_hash AS "Hash", h.snapshot AS "Snapshot"
            FROM   audit_core.tag_status_history h
            JOIN   project_core.tag t ON t.id=h.tag_id
            WHERE  t.tag_name=:tn ORDER BY h.sync_timestamp ASC
        """, {"tn":drill})
        if df_d.empty:
            st.warning(f"No history for `{drill}`")
        else:
            st.caption(f"{len(df_d)} events")
            st.dataframe(df_d.drop(columns=["Snapshot"]).style.applymap(
                lambda v: f"color:{_STATUS_CLR.get(v,'#C9D1D9')}", subset=["Status"]),
                use_container_width=True, hide_index=True)
            snaps = df_d["Snapshot"].dropna()
            if not snaps.empty:
                with st.expander("Latest Snapshot (JSONB)"):
                    st.json(snaps.iloc[-1])
