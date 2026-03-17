"""ui/pages/services.py — Infrastructure links. Admin-only."""
from __future__ import annotations
import streamlit as st
from ui.common import ADMIN_LINKS, is_admin, prefect_get, prefect_post, require_admin, section


def render() -> None:
    st.markdown("### 🔗 Services")
    st.caption("Infrastructure component links · Admin access")

    require_admin()

    section("Infra Components")
    cols = st.columns(len(ADMIN_LINKS))
    for i, (name, url) in enumerate(ADMIN_LINKS.items()):
        cols[i].link_button(name, url, use_container_width=True)

    section("Prefect Health")
    if st.button("Check Prefect API", key="svc_h"):
        h = prefect_get("/health")
        if h:
            st.success("✓ Prefect API online")
            deps = prefect_post("/deployments/filter", {"limit":100})
            if deps and isinstance(deps, list):
                import pandas as pd
                df = pd.DataFrame([{
                    "Deployment": d.get("name",""),
                    "Flow":       d.get("flow_name",""),
                    "Active":     "✓" if d.get("is_schedule_active") else "—",
                } for d in deps])
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.error("✗ Prefect unreachable")
