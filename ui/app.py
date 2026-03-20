"""
app.py — Jackdaw EDW Control Center v0.3.2

Auth: DB-backed login gate (app_core.ui_user, bcrypt, viewer/admin roles).
      All users must authenticate before accessing any page.

Two modes:
  Viewer mode  — Home, Tag Register, Reports, Tag History, Validation, Help, Feedback
  Admin  mode  — + EIS Management

Architecture notes:
  - ALL_PAGES defined before sidebar to allow on_change callback access
  - Navigation uses on_change callback to fix single-click navigation
  - DB access via ui/common.py (viewer role by default, admin role for writes)
  - Prefect API called only from admin pages
  - llm_chat, crs_assistant, etl_import, services preserved in ui/_hidden/ (Phase 2/3)
"""
import streamlit as st

st.set_page_config(
    page_title="EDW Control Center",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.common import (  # noqa: E402
    GLOBAL_CSS, get_current_user, is_admin, verify_password,
)
from ui.version import version_string  # noqa: E402
from ui.pages import (   # noqa: E402
    home, tag_register, reports, tag_history, validation,
    eis_management, help as help_page, feedback,
)
# llm_chat, crs_assistant, etl_import, services — moved to ui/_hidden/, Phase 2/3

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ─── Login gate ───────────────────────────────────────────────────────────────
def _render_login() -> None:
    """Full-page login form shown to unauthenticated users."""
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center;padding:40px 0 24px">
          <div style="font-size:48px">🐦</div>
          <div style="font-size:22px;font-weight:700;color:#E6EDF3;margin-top:8px">Jackdaw EDW</div>
          <div style="font-size:13px;color:#8B949E;margin-top:4px">Engineering Data Warehouse · JDA</div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", key="login_username", placeholder="Enter username")
        password = st.text_input("Password", type="password", key="login_password",
                                 placeholder="Enter password")

        if st.button("Sign in", use_container_width=True, type="primary"):
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                ok, role = verify_password(username, password)
                if ok:
                    st.session_state.update({
                        "authenticated": True,
                        "role":          role,
                        "user":          {"username": username, "role": role},
                        "page":          "🏠  Home",
                    })
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

if not st.session_state.get("authenticated"):
    _render_login()
    st.stop()

# ─── Page registry (must be defined before sidebar) ───────────────────────────
VIEWER_PAGES: dict = {
    "🏠  Home":          home,
    "🗂  Tag Register":  tag_register,
    "📊  Reports":       reports,
    "📋  Tag History":   tag_history,
    "✅  Validation":    validation,
    # "🤖  LLM Chat":      llm_chat,       # hidden — Phase 3
    # "📎  CRS Assistant": crs_assistant,  # hidden — Phase 2 (part of EIS Management)
    "❓  Help":          help_page,
    "💬  Feedback":      feedback,
}

ADMIN_EXTRA_PAGES: dict = {
    "📤  EIS Management": eis_management,
    # "📥  ETL Import":  etl_import,   # hidden — trigger via Home Quick Sync
    # "🔗  Services":    services,     # hidden — duplicates Home admin block
}

ALL_PAGES: dict = {**VIEWER_PAGES, **(ADMIN_EXTRA_PAGES if is_admin() else {})}

# Guard: reset page if no longer in ALL_PAGES (e.g. after sign-out)
if st.session_state.get("page") not in ALL_PAGES:
    st.session_state["page"] = "🏠  Home"

# ─── Navigation callback ──────────────────────────────────────────────────────
def _on_nav_change() -> None:
    """Sync session_state page on radio change — fixes single-click navigation."""
    st.session_state["page"] = st.session_state["sidebar_nav"]

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:10px 0 18px">
      <div style="font-size:16px;font-weight:700;color:#E6EDF3">🐦 Jackdaw EDW</div>
      <div style="font-size:11px;color:#8B949E;margin-top:2px">Control Center · JDA</div>
    </div>
    """, unsafe_allow_html=True)

    # ── User info ─────────────────────────────────────────────────────────
    user = get_current_user()
    role = st.session_state.get("role", "viewer")
    uname = user["username"] if user else ""
    role_html = (
        f'<span class="role-admin">⚙ Admin · {uname}</span>'
        if role == "admin"
        else f'<span class="role-viewer">👤 {uname}</span>'
    )
    st.markdown(role_html, unsafe_allow_html=True)

    if st.button("Sign out", key="signout", use_container_width=True):
        for key in ["authenticated", "role", "user", "page"]:
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown("---")

    # ── Navigation ────────────────────────────────────────────────────────
    st.radio(
        "Navigation",
        list(ALL_PAGES.keys()),
        index=list(ALL_PAGES.keys()).index(st.session_state["page"]),
        key="sidebar_nav",
        on_change=_on_nav_change,
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:11px;color:#8B949E;line-height:1.8">
      PostgreSQL · Prefect 3.x<br>
      Neo4j · Qdrant · Ollama<br>
      <span style="color:#444">PVE LXC 200 · adzv-pt.dev</span><br>
      <span style="color:#444;font-family:monospace">{version_string()}</span>
    </div>
    """, unsafe_allow_html=True)

# ─── Top-right icon bar (Help / Feedback shortcuts) ───────────────────────────
_, col_icons = st.columns([8, 1])
with col_icons:
    icon_col1, icon_col2 = st.columns(2)
    with icon_col1:
        if st.button("❓", key="top_help", help="Help & Guidelines"):
            st.session_state["page"] = "❓  Help"
            st.rerun()
    with icon_col2:
        if st.button("💬", key="top_feedback", help="Submit Feedback"):
            st.session_state["page"] = "💬  Feedback"
            st.rerun()

# ─── Render current page ──────────────────────────────────────────────────────
ALL_PAGES[st.session_state["page"]].render()
