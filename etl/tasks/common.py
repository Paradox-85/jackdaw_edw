import os
import yaml
import pandas as pd
import hashlib
from pathlib import Path
from sqlalchemy import text
import re
from datetime import date, datetime
from typing import Optional

# Default: <repo_root>/config/config.yaml — resolved relative to this file's location.
# Override with EDW_CONFIG_PATH env var or by passing config_path explicitly.
_DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "config.yaml"

# Order is important: more specific patterns first
_DATE_FORMATS: list[tuple[re.Pattern, str]] = [
    # ISO with time: 2024-11-15 08:30:00  or  2024-11-15T08:30:00
    (re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"), "%Y-%m-%d %H:%M:%S"),
    # ISO only date: 2024-11-15
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"),                      "%Y-%m-%d"),
    # ISO with / : 2024/11/15
    (re.compile(r"^\d{4}/\d{2}/\d{2}$"),                      "%Y/%m/%d"),
    # European: 15.11.2024  or  15-11-2024  or  15/11/2024
    (re.compile(r"^\d{2}[.\-/]\d{2}[.\-/]\d{4}$"),            "%d.%m.%Y"),
    # American: 11/15/2024  — only if day > 12 in the second position
    # (ambiguity 01/02/2024 is resolved in favor of European)
    (re.compile(r"^\d{2}/\d{2}/\d{4}$"),                      "%m/%d/%Y"),
    # Excel serial number (number): pandas will handle separately
]

_SEPARATOR_NORM = re.compile(r"[.\-/]")

def load_config(config_path: "str | Path | None" = None) -> dict:
    """Load configuration from YAML file, then overlay secrets from config/.env.

    Resolution order for config file:
    1. config_path argument (if provided)
    2. EDW_CONFIG_PATH environment variable
    3. <repo_root>/config/config.yaml (relative to this file)

    After loading YAML, secrets from config/.env are applied (silent if missing).

    .env overlay rules (only these keys are recognised):
      LLM_API_KEY     → config["llm"]["api_key"]
      LLM_BASE_URL    → config["llm"]["base_url"]     (optional override)
      LLM_MODEL       → config["llm"]["model"]         (optional override)
      DB_PASSWORD     → config["postgres"]["password"]

    os.environ always wins over .env file (Docker/Prefect env injection support).
    """
    if config_path is None:
        config_path = os.getenv("EDW_CONFIG_PATH") or _DEFAULT_CONFIG

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Load config/.env — same directory as config.yaml, silent if missing.
    _env_file = Path(_DEFAULT_CONFIG).parent / ".env"

    try:
        from dotenv import dotenv_values  # type: ignore[import]
        env_vals = dotenv_values(_env_file)  # empty dict if file missing
    except ImportError:
        env_vals = {}

    # Overlay: .env values take priority over config.yaml placeholders.
    _llm = config.setdefault("llm", {})
    if env_vals.get("LLM_API_KEY"):
        _llm["api_key"] = env_vals["LLM_API_KEY"]
    if env_vals.get("LLM_BASE_URL"):
        _llm["base_url"] = env_vals["LLM_BASE_URL"]
    if env_vals.get("LLM_MODEL"):
        _llm["model"] = env_vals["LLM_MODEL"]

    _pg = config.setdefault("postgres", {})
    if env_vals.get("DB_PASSWORD"):
        _pg["password"] = env_vals["DB_PASSWORD"]

    # os.environ always wins — covers Docker/Prefect env injection
    if os.environ.get("LLM_API_KEY"):
        _llm["api_key"] = os.environ["LLM_API_KEY"]
    if os.environ.get("LLM_BASE_URL"):
        _llm["base_url"] = os.environ["LLM_BASE_URL"]
    if os.environ.get("LLM_MODEL"):
        _llm["model"] = os.environ["LLM_MODEL"]
    if os.environ.get("DB_PASSWORD"):
        _pg["password"] = os.environ["DB_PASSWORD"]

    return config

def get_db_engine_url(config):
    """Generate SQLAlchemy connection URL from config dict"""
    pg = config['postgres']
    return f"postgresql://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}"

def get_llm_config(config: dict) -> dict:
    """Return LLM settings section from config dict."""
    return config.get("llm", {})

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize strings: strip spaces and convert to UPPER case"""
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.upper().str.strip()
            df[col] = df[col].replace('NAN', None)
    return df

def get_object_status(row_status):
    """Return status from file if exists, otherwise default to 'Active'"""
    if pd.isna(row_status) or str(row_status).strip() == "":
        return "Active"
    return str(row_status).strip()

def calculate_row_hash(row):
    """
    Generates a unique MD5 hash for a given row of data.
    Works with pandas Series or standard Python dictionaries.
    Used to detect changes between source file and database.
    """
    if isinstance(row, pd.Series):
        # Join values, ensuring consistent ordering and filtering out NaNs
        content = "".join(str(v) for v in row.values if pd.notna(v))
    elif isinstance(row, dict):
        # For dicts, sort keys to ensure hash stability
        content = "".join(str(row[k]) for k in sorted(row.keys()) if row[k] is not None)
    else:
        content = str(row)
        
    return hashlib.md5(content.encode()).hexdigest()

def clean_string(val):
    """Trims and removes tabs/newlines, keeping internal spaces."""
    if pd.isna(val) or str(val).strip().upper() in ['NAN', 'NA', '', 'UNSET']:
        return None
    s = str(val)
    s = re.sub(r'[\t\n\r]', ' ', s) 
    return s.strip()

def normalize_to_id_code(text_val):
    """Strict alphanumeric normalization for ID codes (PO, Companies, Models)."""
    s = clean_string(text_val)
    if not s:
        return None
    return re.sub(r'[^A-Z0-9]', '', s.upper())

def parse_bool(val):
    """Converts Excel value to boolean, defaults to False."""
    if pd.isna(val): return False
    s = str(val).strip().upper()
    return s in ['TRUE', '1', 'YES', 'Y']

def get_ref_id(conn, schema, table, value, logger, search_by='code', auto_create=False, use_normalization=False):
    """Universal resolver for UUIDs across all parsers."""
    raw_val = clean_string(value)
    if not raw_val:
        return None
    
    lookup_val = normalize_to_id_code(raw_val) if use_normalization else raw_val
    
    find_sql = text(f"SELECT id FROM {schema}.{table} WHERE {search_by} = :v")
    res = conn.execute(find_sql, {"v": lookup_val}).scalar()
    
    if res:
        return res
    
    if auto_create:
        logger.warning(f"JIT: Reference record for '{raw_val}' not found in {schema}.{table}. Creating DRAFT.")
        ins_sql = text(f"INSERT INTO {schema}.{table} (code, name, object_status) VALUES (:c, :n, 'Draft') RETURNING id")
        # For DRAFTs: code is normalized (lookup_val), name is clean raw (raw_val)
        return conn.execute(ins_sql, {"c": lookup_val[:50], "n": raw_val}).scalar()
    
    return None

def _detect_and_parse(s: str) -> Optional[date]:
    """Detect date format by pattern, parse with explicit strptime."""
    s = s.strip()

    # Excel serial number (openpyxl sometimes returns float as string)
    if re.match(r"^\d{5}(\.\d+)?$", s):
        try:
            dt = pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(s))
            return dt.date()
        except Exception:
            return None

    # Normalize T → space for ISO datetime
    s_norm = s.replace("T", " ")

    for pattern, fmt in _DATE_FORMATS:
        if pattern.match(s_norm):
            # For European format, normalize separator to dot
            if fmt == "%d.%m.%Y":
                s_norm = _SEPARATOR_NORM.sub(".", s_norm)
            try:
                return datetime.strptime(s_norm[:len(fmt.replace("%Y","0000").replace("%m","00").replace("%d","00").replace("%H","00").replace("%M","00").replace("%S","00"))], fmt).date()
            except ValueError:
                # Pattern matched, but date is invalid (e.g., 31/02/2024)
                continue

    return None

def to_dt(val) -> Optional[date]:
    """
    Parse any date/datetime value to Python date.

    Accepts:
      - datetime / date objects     → returned as-is
      - pandas Timestamp            → .date()
      - Excel serial float/int      → converted via 1899-12-30 base
      - str in formats:
            YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY/MM/DD
            DD.MM.YYYY, DD-MM-YYYY, DD/MM/YYYY  (European, dayfirst)
            MM/DD/YYYY                           (American fallback)

    Returns:
      datetime.date or None
    """
    if val is None:
        return None

    # Native Python/pandas date types — without extra parsing
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, pd.Timestamp):
        return val.date() if pd.notna(val) else None

    # Excel numeric serial (from openpyxl as int/float)
    if isinstance(val, (int, float)):
        try:
            dt = pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(val))
            return dt.date()
        except Exception:
            return None

    # String
    s = clean_string(val)
    if not s or s.lower() in ("nat", "none", "null", "nan"):
        return None

    result = _detect_and_parse(s)
    if result is None:
        # Last fallback: pandas without dayfirst (no warnings)
        try:
            dt = pd.to_datetime(s, dayfirst=False)
            return dt.date() if pd.notna(dt) else None
        except Exception:
            pass

    return result