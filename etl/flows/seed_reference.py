import pandas as pd
import re
from sqlalchemy import create_engine, text
from prefect import flow, task, get_run_logger
import sys
import os
from pathlib import Path

# Setup paths
current_dir = Path(__file__).resolve().parent
script_root = current_dir.parent
if str(script_root) not in sys.path:
    sys.path.append(str(script_root))

from tasks.common import load_config, get_db_engine_url

# Load Configuration
config = load_config()
DB_URL = get_db_engine_url(config)
FILE_PATH = config.get('storage', {}).get('master_rdl')

def read_sheet_with_header_search(file_path, sheet_name, keyword):
    """
    Finds the header row by searching for a keyword in the sheet.
    Useful for sheets where tables don't start at the first row.
    """
    # Load raw sheet without header to find the keyword
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    for i, row in df_raw.iterrows():
        if keyword in row.values:
            # Re-read the sheet starting from the identified header row
            df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=i+1)
            # Restore the header names found at row i
            df.columns = df_raw.iloc[i].values
            # Return cleaned dataframe without empty columns
            return df.loc[:, df.columns.notna()].copy()
    return pd.DataFrame()

@task(name="Sync Validation Rules (Regex)")
def sync_validation_rules():
    """Parses picklists and generates Regex values (e.g., '(value1|value2)')."""
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    # Sheets for validation rules
    df_pl = read_sheet_with_header_search(FILE_PATH, 'Property picklist', 'Id')
    df_vals = read_sheet_with_header_search(FILE_PATH, 'Property picklist value ', 'Picklist ID')
    
    count = 0
    with engine.begin() as conn:
        for _, pl in df_pl.iterrows():
            pl_id = str(pl['Id']).strip()
            # Extract items for this specific picklist
            items = df_vals[df_vals['Picklist ID'] == pl_id]['Picklist Item Name'].dropna().unique()
            
            if len(items) > 0:
                # Build Regex string: (Item 1|Item 2|Item 3)
                regex_pattern = f"({'|'.join(map(str, items))})"
                
                conn.execute(text("""
                    INSERT INTO ontology_core.validation_rule (code, name, validation_type, validation_value)
                    VALUES (:c, :n, 'picklist', :v)
                    ON CONFLICT (code) DO UPDATE SET validation_value = EXCLUDED.validation_value
                """), {"c": pl_id, "n": pl['Name'], "v": regex_pattern})
                count += 1
    logger.info(f"Synchronized {count} validation rules with generated Regex.")

@task(name="Sync Unified Classes")
def sync_unified_classes():
    """Merges Tag (Functional) and Equipment (Physical) classes."""
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    df_tag = read_sheet_with_header_search(FILE_PATH, 'Tag class', 'Tag Class ID')
    df_eq = read_sheet_with_header_search(FILE_PATH, 'Equipment class', 'Equipment Class ID')
    
    # Standardize columns for merging
    df_tag = df_tag[['Tag Class ID', 'Tag Class Name']].rename(columns={'Tag Class ID': 'code', 'Tag Class Name': 'name'})
    df_eq = df_eq[['Equipment Class ID', 'Equipment Class Name']].rename(columns={'Equipment Class ID': 'code', 'Equipment Class Name': 'name'})
    
    unique_codes = set(df_tag['code'].dropna()) | set(df_eq['code'].dropna())
    
    with engine.begin() as conn:
        for code in unique_codes:
            is_tag = code in df_tag['code'].values
            is_eq = code in df_eq['code'].values
            
            # Concept Logic: Combined, Functional or Physical
            concept = "Functional Physical" if (is_tag and is_eq) else ("Functional" if is_tag else "Physical")
            name = df_tag[df_tag['code'] == code]['name'].iloc[0] if is_tag else df_eq[df_eq['code'] == code]['name'].iloc[0]

            conn.execute(text("""
                INSERT INTO ontology_core.class (code, name, concept, object_status)
                VALUES (:c, :n, :cp, 'ACTIVE')
                ON CONFLICT (code) DO UPDATE SET concept = EXCLUDED.concept
            """), {"c": str(code).upper(), "n": str(name).upper(), "cp": concept})
    logger.info("Classes unified and synchronized.")

@task(name="Sync UoM and Property Layer")
def sync_uom_and_properties():
    """Syncs UoM dimensions and Properties with metadata linking."""
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    df_dim = read_sheet_with_header_search(FILE_PATH, 'Unit of measure dimension', 'Group Dimension')
    df_uom = read_sheet_with_header_search(FILE_PATH, 'Unit of measure', 'Unique ID')
    df_prop = read_sheet_with_header_search(FILE_PATH, 'Property', 'Property ID')
    
    with engine.begin() as conn:
        # 1. UoM Groups
        for _, r in df_dim.iterrows():
            conn.execute(text("INSERT INTO ontology_core.uom_group (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"),
                         {"c": str(r['Group Dimension']).upper(), "n": r['Dimension Name']})
        
        # 2. UoMs
        for _, r in df_uom.iterrows():
            conn.execute(text("""
                INSERT INTO ontology_core.uom (code, name, symbol, uom_group_id)
                VALUES (:c, :n, :s, (SELECT id FROM ontology_core.uom_group WHERE code = :gc))
                ON CONFLICT (code) DO NOTHING
            """), {"c": str(r['Unique ID']).upper(), "n": r['UoM Name'], "s": r['UoM Symbol'], "gc": str(r['UoM Dimension']).upper()})
            
        # 3. Properties
        for _, r in df_prop.iterrows():
            pl_ref = r['picklist name'] if not pd.isna(r['picklist name']) else None
            ug_code = str(r['Unit of measure dimension code']).upper() if not pd.isna(r['Unit of measure dimension code']) else None
            
            conn.execute(text("""
                INSERT INTO ontology_core.property (code, name, validation_rule_id, uom_group_id)
                VALUES (:c, :n, 
                    (SELECT id FROM ontology_core.validation_rule WHERE code = :vrc),
                    (SELECT id FROM ontology_core.uom_group WHERE code = :ugc))
                ON CONFLICT (code) DO UPDATE SET 
                    validation_rule_id = EXCLUDED.validation_rule_id,
                    uom_group_id = EXCLUDED.uom_group_id
            """), {"c": str(r['Property ID']).upper(), "n": str(r['property name']).upper(), "vrc": pl_ref, "ugc": ug_code})
    logger.info("UoM and Property layer synchronized.")

@task(name="Sync Unified Class-Property Mapping")
def sync_class_property_matrix():
    """Merges Tag and Equipment property assignments."""
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    df_tag_map = read_sheet_with_header_search(FILE_PATH, 'Tag class properties', 'Tag class ID')
    df_eq_map = read_sheet_with_header_search(FILE_PATH, 'Equipment class props', 'Equipment class ID')
    
    # Generate unique keys for comparison
    df_tag_map['key'] = df_tag_map['Tag class ID'].astype(str) + "|" + df_tag_map['Tag Property ID'].astype(str)
    df_eq_map['key'] = df_eq_map['Equipment class ID'].astype(str) + "|" + df_eq_map['Equipment Property ID'].astype(str)
    
    all_keys = set(df_tag_map['key']) | set(df_eq_map['key'])
    
    with engine.begin() as conn:
        for key in all_keys:
            in_tag = key in df_tag_map['key'].values
            in_eq = key in df_eq_map['key'].values
            
            concept = "Functional Physical" if (in_tag and in_eq) else ("Functional" if in_tag else "Physical")
            class_code, prop_code = key.split("|")
            
            conn.execute(text("""
                INSERT INTO ontology_core.class_property (class_id, property_id, mapping_concept)
                VALUES (
                    (SELECT id FROM ontology_core.class WHERE code = :cc),
                    (SELECT id FROM ontology_core.property WHERE code = :pc),
                    :mc
                ) ON CONFLICT (class_id, property_id) DO UPDATE SET mapping_concept = EXCLUDED.mapping_concept
            """), {"cc": class_code.upper(), "pc": prop_code.upper(), "mc": concept})
    logger.info("Unified Mapping Matrix synchronized.")

@flow(name="Ontology Master Seed", log_prints=True)
def ontology_master_flow():
    """Main Flow for Engineering Ontology Synchronization."""
    sync_validation_rules()
    sync_uom_and_properties()
    sync_unified_classes()
    sync_class_property_matrix()

if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    ontology_master_flow.serve(name="ontology-seeder")