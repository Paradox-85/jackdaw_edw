"""
ui/common.py — Shared config, CSS, DB/Prefect helpers.

DB ACCESS POLICY:
  - Admin mode  → postgres_admin (full access, trigger flows)
  - Viewer mode → edw_viewer     (read-only role, SELECT on reporting views only)

RBAC is currently env-var based (ADMIN_PASSWORD).
Phase 2: replace with proper OIDC/session auth.
"""
from __future__ import annotations
import os
from datetime import datetime

import httpx
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ─── Environment ──────────────────────────────────────────────────────────────
# Admin DB — full access (import triggers, audit writes)
_ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres_admin:password@postgres:5432/engineering_core",
)
# Read-only DB — viewer role, SELECT only on project_core/audit_core views
# Create with: CREATE ROLE edw_viewer LOGIN PASSWORD '...' IN ROLE pg_read_all_data;
_VIEWER_DB_URL = os.getenv(
    "DATABASE_VIEWER_URL",
    _ADMIN_DB_URL,  # fallback: same DB until edw_viewer role is created
)

PREFECT_URL    = os.getenv("PREFECT_API_URL", "http://prefect-server:4200/api")
OLLAMA_URL     = os.getenv("OLLAMA_URL",      "http://ollama:11434")
EIS_EXPORT_DIR = os.getenv("EIS_EXPORT_DIR",  "/mnt/shared-data/ram-user/Jackdaw/EIS_Exports/")

# Admin gate — simple password until proper auth is added
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

# External infra links — shown ONLY in admin mode
ADMIN_LINKS = {
    "Prefect UI": os.getenv("LINK_PREFECT",   "https://pve.prefect.adzv-pt.dev"),
    "DbGate":     os.getenv("LINK_DBGATE",    "https://pve.dbgate.adzv-pt.dev"),
    "Portainer":  os.getenv("LINK_PORTAINER", "https://pve.portainer.adzv-pt.dev"),
}

# ─── RBAC helper ──────────────────────────────────────────────────────────────
def is_admin() -> bool:
    return st.session_state.get("role") == "admin"

def require_admin() -> None:
    """Render admin login gate if not authenticated."""
    if is_admin():
        return
    st.warning("🔒 This section requires admin access.")
    pwd = st.text_input("Admin password", type="password", key="admin_gate_pwd")
    if st.button("Unlock", key="admin_gate_btn"):
        if pwd == ADMIN_PASSWORD:
            st.session_state["role"] = "admin"
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ─── CSS ──────────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDeployButton"] { display: none; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #21262D; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 6px !important;
    padding: 14px 18px !important;
}
[data-testid="metric-container"] label {
    font-size: 10px !important; color: #8B949E !important;
    text-transform: uppercase; letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] { font-size: 24px !important; color: #E6EDF3 !important; font-weight: 600 !important; }

/* Section header */
.sec {
    font-size: 10px; font-weight: 600; color: #8B949E;
    text-transform: uppercase; letter-spacing: 0.1em;
    border-bottom: 1px solid #21262D; padding-bottom: 6px; margin: 18px 0 12px;
}

/* Log box */
.log-box {
    background: #0D1117; border: 1px solid #21262D; border-radius: 6px;
    padding: 12px 16px; font-family: 'SF Mono','Fira Code',monospace;
    font-size: 11px; max-height: 260px; overflow-y: auto; line-height: 1.9;
}

/* Under construction banner */
.wip-banner {
    background: #1C2128; border: 1px dashed #D29922; border-radius: 6px;
    padding: 24px; text-align: center; color: #D29922;
    font-size: 13px; margin: 16px 0;
}

/* Inline status badges */
.badge { display:inline-block; padding:2px 9px; border-radius:10px; font-size:11px; font-weight:500; }
.badge-green  { background:rgba(63,185,80,.15);  color:#3FB950; border:1px solid rgba(63,185,80,.3);  }
.badge-blue   { background:rgba(88,166,255,.12); color:#58A6FF; border:1px solid rgba(88,166,255,.3); }
.badge-yellow { background:rgba(210,153,34,.15); color:#D29922; border:1px solid rgba(210,153,34,.3); }
.badge-red    { background:rgba(248,81,73,.15);  color:#F85149; border:1px solid rgba(248,81,73,.3);  }
.badge-gray   { background:rgba(110,118,129,.12);color:#8B949E; border:1px solid rgba(110,118,129,.3);}

/* Role pill */
.role-admin  { color:#58A6FF; font-size:11px; font-weight:600; }
.role-viewer { color:#8B949E; font-size:11px; }
</style>
"""

STATE_BADGE = {
    "COMPLETED": ("badge-green",  "✓ Completed"),
    "FAILED":    ("badge-red",    "✗ Failed"),
    "RUNNING":   ("badge-blue",   "⟳ Running"),
    "SCHEDULED": ("badge-yellow", "⏳ Scheduled"),
    "CRASHED":   ("badge-red",    "✗ Crashed"),
    "CANCELLED": ("badge-gray",   "— Cancelled"),
}

def badge(state: str) -> str:
    cls, label = STATE_BADGE.get(state, ("badge-gray", state))
    return f'<span class="badge {cls}">{label}</span>'

def wip(label: str = "Under Construction") -> None:
    st.markdown(f'<div class="wip-banner">🚧 &nbsp; <strong>{label}</strong> &nbsp; 🚧<br>'
                '<span style="font-size:12px;color:#8B949E">This module is planned but not yet implemented.</span></div>',
                unsafe_allow_html=True)

def section(label: str) -> None:
    st.markdown(f'<div class="sec">{label}</div>', unsafe_allow_html=True)

# ─── DB engines ───────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _admin_engine() -> Engine:
    return create_engine(_ADMIN_DB_URL, pool_pre_ping=True, pool_size=3)

@st.cache_resource(show_spinner=False)
def _viewer_engine() -> Engine:
    return create_engine(_VIEWER_DB_URL, pool_pre_ping=True, pool_size=5)

def db_read(sql: str, params: dict | None = None, admin: bool = False) -> pd.DataFrame:
    """Execute read SQL. Uses viewer engine by default, admin engine if admin=True."""
    engine = _admin_engine() if admin else _viewer_engine()
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except Exception as exc:
        st.error(f"DB error: {exc}")
        return pd.DataFrame()

# ─── Prefect helpers ──────────────────────────────────────────────────────────
def prefect_get(path: str):
    try:
        r = httpx.get(f"{PREFECT_URL}{path}", timeout=5)
        r.raise_for_status(); return r.json()
    except Exception:
        return None

def prefect_post(path: str, payload: dict):
    try:
        r = httpx.post(f"{PREFECT_URL}{path}", json=payload, timeout=10)
        r.raise_for_status(); return r.json()
    except Exception as exc:
        return {"error": str(exc)}

def trigger_deployment(name: str, params: dict) -> dict:
    """Schedule a flow run by deployment name."""
    data = prefect_post("/deployments/filter",
                        {"limit": 5, "deployments": {"name": {"any_": [name]}}})
    if not data or not isinstance(data, list) or not data:
        return {"error": f"Deployment '{name}' not found in Prefect"}
    dep_id = data[0]["id"]
    return prefect_post(f"/deployments/{dep_id}/create_flow_run",
                        {"parameters": params, "state": {"type": "SCHEDULED"}})

def recent_flow_runs(limit: int = 10) -> pd.DataFrame:
    data = prefect_post("/flow_runs/filter", {
        "limit": limit, "sort": "START_TIME_DESC",
        "flow_runs": {"state": {"operator": "and_", "type": {"any_": [
            "COMPLETED","FAILED","RUNNING","CRASHED","SCHEDULED"
        ]}}},
    })
    if not data or isinstance(data, dict): return pd.DataFrame()
    return pd.DataFrame([{
        "Flow":       r.get("flow_name",""),
        "Run":        r.get("name",""),
        "State":      r.get("state",{}).get("type",""),
        "Started":    (r.get("start_time") or "")[:19].replace("T"," "),
        "Duration s": round(r.get("total_run_time",0),1),
    } for r in data])

# ─── Ollama helpers ───────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def ollama_models() -> list[str]:
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=4)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []

# ─── Shared log helpers ───────────────────────────────────────────────────────
def log(level: str, msg: str, key: str = "run_log") -> None:
    ts  = datetime.now().strftime("%H:%M:%S")
    clr = {"ok":"#3FB950","info":"#58A6FF","warn":"#D29922","err":"#F85149"}.get(level,"#8B949E")
    tag = {"ok":"OK  ","info":"INFO","warn":"WARN","err":"ERR "}.get(level,"    ")
    entry = (f'<span style="color:#8B949E">{ts}</span> '
             f'<span style="color:{clr};font-weight:600">[{tag}]</span> '
             f'<span style="color:#C9D1D9">{msg}</span>')
    st.session_state.setdefault(key, []).append(entry)

def render_log(key: str = "run_log") -> None:
    lines = st.session_state.get(key, [])[-50:]
    html  = "<br>".join(lines) if lines else '<span style="color:#8B949E">— no output yet —</span>'
    st.markdown(f'<div class="log-box">{html}</div>', unsafe_allow_html=True)
