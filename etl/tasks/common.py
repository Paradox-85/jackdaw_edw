import yaml
import pandas as pd
import hashlib
from sqlalchemy import text
import re

def load_config(config_path="/mnt/shared-data/ram-user/Jackdaw/EDW-repository/config/config.yaml"):
    """Load database configuration from YAML file"""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def get_db_engine_url(config):
    """Generate SQLAlchemy connection URL from config dict"""
    pg = config['postgres']
    return f"postgresql://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}"

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

def to_dt(val):
    if not val or pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nat":
        return None
    try:
        # Explicitly tell Pandas that the day comes first
        dt = pd.to_datetime(clean_string(val), dayfirst=True)
        return dt.date() if pd.notna(dt) else None
    except Exception:
        return None