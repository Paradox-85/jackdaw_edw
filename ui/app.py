"""
app.py — Jackdaw EDW Control Center v2

Two modes:
  Viewer mode  — Reports, Tag History, Validation stats, LLM Chat
  Admin  mode  — + ETL Import, EIS Export, Services (password-gated)

Architecture notes:
  - DB access via ui/common.py (viewer role by default, admin role for writes)
  - Prefect API called only from admin pages
  - Infra links (DbGate, Portainer) visible only in admin mode
  - All pages in ui/pages/ expose a render() function
"""
import streamlit as st

st.set_page_config(
    page_title="Jackdaw EDW",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.common import GLOBAL_CSS, is_admin  # noqa: E402
from ui.pages import (                       # noqa: E402
    home, reports, tag_history, validation,
    llm_chat, crs_assistant, services,
    etl_import, eis_export,
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:10px 0 18px">
      <div style="font-size:16px;font-weight:700;color:#E6EDF3">🐦 Jackdaw EDW</div>
      <div style="font-size:11px;color:#8B949E;margin-top:2px">Control Center · JDA</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Role indicator ─────────────────────────────────────────────────────
    role = st.session_state.get("role", "viewer")
    role_html = (
        '<span class="role-admin">⚙ Admin mode</span>'
        if role == "admin"
        else '<span class="role-viewer">👤 Viewer mode</span>'
    )
    st.markdown(role_html, unsafe_allow_html=True)

    if role == "admin":
        if st.button("Sign out admin", key="signout", use_container_width=True):
            st.session_state["role"] = "viewer"
            st.session_state["page"] = "🏠  Home"
            st.rerun()

    st.markdown("---")

    # ── Navigation — viewer pages ─────────────────────────────────────────
    VIEWER_PAGES = {
        "🏠  Home":          home,
        "📊  Reports":       reports,
        "📋  Tag History":   tag_history,
        "✅  Validation":    validation,
        "🤖  LLM Chat":      llm_chat,
        "📎  CRS Assistant": crs_assistant,
    }

    # Admin pages shown only when authenticated
    ADMIN_PAGES = {
        "📥  ETL Import":    etl_import,
        "📤  EIS Export":    eis_export,
        "🔗  Services":      services,
    }

    ALL_PAGES = {**VIEWER_PAGES, **(ADMIN_PAGES if is_admin() else {})}

    if "page" not in st.session_state or st.session_state["page"] not in ALL_PAGES:
        st.session_state["page"] = "🏠  Home"

    selected = st.radio(
        "Navigation",
        list(ALL_PAGES.keys()),
        index=list(ALL_PAGES.keys()).index(st.session_state["page"]),
        key="sidebar_nav",
        label_visibility="collapsed",
    )
    st.session_state["page"] = selected

    # ── Admin section shown at bottom of sidebar ───────────────────────────
    if not is_admin():
        st.markdown("---")
        st.markdown('<div style="font-size:11px;color:#8B949E">Admin access</div>',
                    unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", key="sidebar_pwd",
                            label_visibility="collapsed", placeholder="Admin password…")
        if st.button("Unlock admin", key="sidebar_unlock", use_container_width=True):
            from ui.common import ADMIN_PASSWORD
            if pwd == ADMIN_PASSWORD:
                st.session_state["role"] = "admin"
                st.rerun()
            else:
                st.error("Incorrect password.")

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#8B949E;line-height:1.8">
      PostgreSQL · Prefect 3.x<br>
      Neo4j · Qdrant · Ollama<br>
      <span style="color:#444">PVE LXC 200 · adzv-pt.dev</span>
    </div>
    """, unsafe_allow_html=True)

# ─── Render ───────────────────────────────────────────────────────────────────
ALL_PAGES[selected].render()
