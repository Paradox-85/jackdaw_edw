"""
ui/common.py — Shared config, CSS, DB/Prefect helpers.

DB ACCESS POLICY:
  - Admin mode  → postgres_admin (full access, trigger flows, INSERT to app_core)
  - Viewer mode → edw_viewer     (read-only role, SELECT on reporting views only)

Auth: DB-backed via app_core.ui_user (bcrypt passwords, viewer/admin roles).
Phase 2: replace with proper OIDC/session auth if user base grows.
"""
from __future__ import annotations
import os
from datetime import datetime

import bcrypt
import httpx
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ─── Environment ──────────────────────────────────────────────────────────────
# Admin DB — full access (import triggers, audit writes, app_core writes)
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

# External infra links — shown ONLY in admin mode
ADMIN_LINKS = {
    "Prefect UI": os.getenv("LINK_PREFECT", "https://pve.prefect.adzv-pt.dev"),
    "DbGate":     os.getenv("LINK_DBGATE",  "https://pve.db.adzv-pt.dev"),
}

# ─── RBAC helper ──────────────────────────────────────────────────────────────
def is_admin() -> bool:
    return st.session_state.get("role") == "admin"

def require_admin() -> None:
    """Stop rendering if user is not admin. Role is set at login — no inline gate."""
    if is_admin():
        return
    st.warning("🔒 This section requires admin access.")
    st.stop()

def get_current_user() -> dict | None:
    """Return current user dict {id, username, role} or None if not authenticated."""
    return st.session_state.get("user")

# ─── Auth ─────────────────────────────────────────────────────────────────────
def verify_password(username: str, password: str) -> tuple[bool, str]:
    """
    Verify credentials against app_core.ui_user.

    Updates last_login timestamp on success.

    Args:
        username: Plaintext username.
        password: Plaintext password to verify against bcrypt hash.

    Returns:
        (True, role) on success; (False, "") on failure or inactive user.
    """
    df = db_read(
        "SELECT id, password_hash, role, is_active FROM app_core.ui_user WHERE username = :u",
        {"u": username},
        admin=True,
    )
    if df.empty:
        return False, ""
    row = df.iloc[0]
    if not row["is_active"]:
        return False, ""
    try:
        match = bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8"))
    except Exception:
        return False, ""
    if match:
        # Update last_login — non-critical, failure does not affect auth result
        db_write(
            "UPDATE app_core.ui_user SET last_login = now() WHERE username = :u",
            {"u": username},
        )
        return True, str(row["role"])
    return False, ""

# ─── CSS ──────────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
/* Google Fonts — Roboto (MUI standard). Falls back gracefully if CDN unreachable. */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

body, p, div, span, label { font-family: 'Roboto', 'Segoe UI', Arial, sans-serif !important; }

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDeployButton"] { display: none; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #21262D; }

/* Metric cards — MUI elevation style */
[data-testid="metric-container"] {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 4px !important;
    padding: 14px 18px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2) !important;
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

/* Log box — monospace only here */
.log-box {
    background: #0D1117; border: 1px solid #21262D; border-radius: 4px;
    padding: 12px 16px; font-family: 'SF Mono','Fira Code',monospace !important;
    font-size: 11px; max-height: 260px; overflow-y: auto; line-height: 1.9;
}

/* Under construction banner */
.wip-banner {
    background: #1C2128; border: 1px dashed #D29922; border-radius: 4px;
    padding: 24px; text-align: center; color: #D29922;
    font-size: 13px; margin: 16px 0;
}

/* Inline status badges */
.badge { display:inline-block; padding:2px 9px; border-radius:10px; font-size:11px; font-weight:500; }
.badge-green  { background:rgba(63,185,80,.15);  color:#3FB950; border:1px solid rgba(63,185,80,.3);  }
.badge-blue   { background:rgba(25,118,210,.15); color:#1976D2; border:1px solid rgba(25,118,210,.3); }
.badge-yellow { background:rgba(210,153,34,.15); color:#D29922; border:1px solid rgba(210,153,34,.3); }
.badge-red    { background:rgba(248,81,73,.15);  color:#F85149; border:1px solid rgba(248,81,73,.3);  }
.badge-gray   { background:rgba(110,118,129,.12);color:#8B949E; border:1px solid rgba(110,118,129,.3);}

/* Role pill */
.role-admin  { color:#1976D2; font-size:11px; font-weight:600; }
.role-viewer { color:#8B949E; font-size:11px; }

/* Section dividers */
.section-header {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8B949E;
    border-bottom: 1px solid #21262D;
    padding-bottom: 4px;
    margin: 1.2rem 0 0.6rem 0;
}

/* Extended badge variants */
.badge-wip    { background: #2D1B69; color: #A78BFA; border: 1px solid #7C3AED; }

/* Login form container */
.login-box {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 2rem;
}

/* Disclaimer banner */
.disclaimer {
    background: #1C2128;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 0.75rem;
    color: #8B949E;
    margin-bottom: 1rem;
}
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

def db_write(sql: str, params: dict | None = None) -> bool:
    """
    Execute write SQL (INSERT/UPDATE/DELETE) using admin engine.

    Always uses admin engine — viewer role has no write rights on app_core.

    Args:
        sql:    Parameterised SQL with :param placeholders.
        params: Dict of parameter values.

    Returns:
        True on success, False on error (error displayed via st.error).
    """
    try:
        with _admin_engine().begin() as conn:
            conn.execute(text(sql), params or {})
        return True
    except Exception as exc:
        st.error(f"DB write error: {exc}")
        return False

# ─── Prefect helpers ──────────────────────────────────────────────────────────
def prefect_get(path: str, timeout: int = 10):
    """GET request to Prefect API. Returns parsed JSON or None on failure."""
    try:
        r = httpx.get(f"{PREFECT_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except httpx.TimeoutException:
        return {"error": f"Timeout: {path}"}
    except Exception as exc:
        return {"error": str(exc)}

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

def get_flow_run_status(run_id: str) -> dict | None:
    """
    Return normalised Prefect flow run dict.
    Guarantees data['state']['type'] is always populated.
    """
    data = prefect_get(f"/flow-runs/{run_id}", timeout=10)
    if not data or "error" in data:
        return None

    top_type = (data.get("state_type") or "").upper() or None
    top_name = data.get("state_name") or top_type

    state_obj = data.get("state") or {}
    nested_type = (state_obj.get("type") or "").upper() or None
    nested_name = state_obj.get("name") or nested_type

    resolved_type = nested_type or top_type or "UNKNOWN"
    resolved_name = nested_name or top_name or resolved_type

    data["state"] = {"type": resolved_type, "name": resolved_name}
    return data

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
    clr = {"ok":"#3FB950","info":"#1976D2","warn":"#D29922","err":"#F85149"}.get(level,"#8B949E")
    tag = {"ok":"OK  ","info":"INFO","warn":"WARN","err":"ERR "}.get(level,"    ")
    entry = (f'<span style="color:#8B949E">{ts}</span> '
             f'<span style="color:{clr};font-weight:600">[{tag}]</span> '
             f'<span style="color:#C9D1D9">{msg}</span>')
    st.session_state.setdefault(key, []).append(entry)

def render_log(key: str = "run_log") -> None:
    lines = st.session_state.get(key, [])[-50:]
    html  = "<br>".join(lines) if lines else '<span style="color:#8B949E">— no output yet —</span>'
    st.markdown(f'<div class="log-box">{html}</div>', unsafe_allow_html=True)
