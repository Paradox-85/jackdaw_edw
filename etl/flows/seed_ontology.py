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

# Load Config
config = load_config()
DB_URL = get_db_engine_url(config)
FILE_PATH = config.get('storage', {}).get('master_rdl')

def read_sheet_smart(file_path, sheet_name, header_keyword):
    """
    Finds the header row and reads data correctly.
    Uses header=i to ensure the first data row isn't consumed as header.
    """
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    for i, row in df_raw.iterrows():
        if header_keyword in row.values:
            # FIX: Use header=i to correctly identify columns and keep row i+1 as data
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=i)
            return df.loc[:, df.columns.notna()].copy()
    return pd.DataFrame()

@task(name="Sync Validation Rules")
def sync_validation_rules():
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    df_pl = read_sheet_smart(FILE_PATH, 'Property picklist', 'Id')
    df_vals = read_sheet_smart(FILE_PATH, 'Property picklist value ', 'Picklist ID')
    
    stats = {"created": 0, "updated": 0}
    with engine.begin() as conn:
        for _, pl in df_pl.iterrows():
            pl_id = str(pl['Id']).strip()
            items = df_vals[df_vals['Picklist ID'] == pl_id]['Picklist Item Name'].dropna().unique()
            if len(items) > 0:
                regex_val = f"({'|'.join(map(str, items))})"
                res = conn.execute(text("""
                    INSERT INTO ontology_core.validation_rule (code, name, validation_type, validation_value)
                    VALUES (:c, :n, 'picklist', :v)
                    ON CONFLICT (code) DO UPDATE SET 
                        validation_value = EXCLUDED.validation_value,
                        name = EXCLUDED.name
                    RETURNING (xmax = 0) AS inserted;
                """), {"c": pl_id, "n": pl['Name'], "v": regex_val})
                
                if res.fetchone()[0]: stats["created"] += 1
                else: stats["updated"] += 1
                
    logger.info(f"✅ COMPLETED: Validation Rules sync. Result: {stats['created']} created, {stats['updated']} updated.")

@task(name="Sync Unified Classes")
def sync_classes():
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    # 1. Reading sheets
    df_tag = read_sheet_smart(FILE_PATH, 'Tag class', 'Tag Class ID')
    df_eq = read_sheet_smart(FILE_PATH, 'Equipment class', 'Equipment Class ID')

    # 2. Cleanup and Normalize
    def process_df(df, c_col, n_col, p_col, d_col):
        df = df.dropna(subset=[c_col]).copy()
        df = df[[c_col, n_col, p_col, d_col]].rename(
            columns={c_col: 'code', n_col: 'name', p_col: 'parent_code', d_col: 'definition'})
        df['code'] = df['code'].astype(str).str.upper().str.strip()
        df['parent_code'] = df['parent_code'].apply(lambda x: str(x).upper().strip() if pd.notna(x) else None)
        return df

    df_tag_c = process_df(df_tag, 'Tag Class ID', 'Tag Class Name', 'Parent Class ID', 'Tag class definition')
    df_eq_c = process_df(df_eq, 'Equipment Class ID', 'Equipment Class Name', 'Parent Class ID', 'Equipment class definition')

    # 3. Combine
    all_data = pd.concat([df_tag_c, df_eq_c]).drop_duplicates(subset=['code'])

    # 4. Calculate Abstract Flag
    # A class is abstract if it is a parent to at least one other class
    parent_codes = set(all_data['parent_code'].dropna().unique())

    stats = {"created": 0, "abstract": 0}

    with engine.begin() as conn:
        # Step A: Upsert all classes
        for _, row in all_data.iterrows():
            code = row['code']
            is_tag = code in df_tag_c['code'].values
            is_eq = code in df_eq_c['code'].values
            concept = "Functional Physical" if (is_tag and is_eq) else ("Functional" if is_tag else "Physical")
            
            # Logic for abstract: has children in the current dataset
            is_abstract = code in parent_codes

            conn.execute(text("""
                INSERT INTO ontology_core.class (code, name, definition, concept, is_abstract, object_status)
                VALUES (:c, :n, :d, :cp, :abs, 'ACTIVE')
                ON CONFLICT (code) DO UPDATE SET 
                    concept = EXCLUDED.concept, 
                    name = EXCLUDED.name,
                    definition = EXCLUDED.definition,
                    is_abstract = EXCLUDED.is_abstract;
            """), {
                "c": code, 
                "n": str(row['name']).upper() if pd.notna(row['name']) else code, 
                "d": row['definition'] if pd.notna(row['definition']) else None,
                "cp": concept,
                "abs": is_abstract
            })
            stats["created"] += 1
            if is_abstract: stats["abstract"] += 1

        # Step B: Update Hierarchy (using the freshly created/updated IDs)
        linked_count = 0
        for _, row in all_data.iterrows():
            # Исправленное условие: проверяем, что код родителя не пустой и не является NaN
            if pd.notna(row['parent_code']) and str(row['parent_code']).upper() != 'NAN':
                res = conn.execute(text("""
                    UPDATE ontology_core.class 
                    SET parent_class_id = (SELECT id FROM ontology_core.class WHERE code = :pc)
                    WHERE code = :c;
                """), {
                    "pc": str(row['parent_code']).upper().strip(), 
                    "c": str(row['code']).upper().strip()
                })
                if res.rowcount > 0: linked_count += 1
            
    logger.info(f"✅ COMPLETED: {stats['created']} classes synced. {stats['abstract']} marked as abstract.")
    
@task(name="Sync UoM and Property Layer")
def sync_uom_properties():
    """Updated logic: Linking UoM and Properties using Unique ID codes."""
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    df_dim = read_sheet_smart(FILE_PATH, 'Unit of measure dimension', 'Unique ID')
    df_uom = read_sheet_smart(FILE_PATH, 'Unit of measure', 'Unique ID')
    df_prop = read_sheet_smart(FILE_PATH, 'Property', 'Property ID')
    
    with engine.begin() as conn:
        # 1. UoM Groups (Dimensions) - Use Unique ID as code
        for _, r in df_dim.iterrows():
            conn.execute(text("""
                INSERT INTO ontology_core.uom_group (code, name) 
                VALUES (:c, :n) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
            """), {"c": str(r['Unique ID']).upper().strip(), "n": r['Dimension Name']})
        
        # 2. UoMs - Link via UoM Group ID column from Excel
        uom_group_col = 'UoM Group ID' if 'UoM Group ID' in df_uom.columns else 'UoM Dimension'
        for _, r in df_uom.iterrows():
            group_code = str(r[uom_group_col]).upper().strip() if pd.notna(r[uom_group_col]) else None
            conn.execute(text("""
                INSERT INTO ontology_core.uom (code, name, symbol, uom_group_id)
                VALUES (:c, :n, :s, (SELECT id FROM ontology_core.uom_group WHERE code = :gc))
                ON CONFLICT (code) DO NOTHING
            """), {
                "c": str(r['Unique ID']).upper().strip(), 
                "n": r['UoM Name'], 
                "s": r['UoM Symbol'],
                "gc": group_code
            })
            
        # 3. Properties - Using full metadata and Unique ID for UoM mapping
        for _, r in df_prop.iterrows():
            pl_ref = str(r['picklist name']).strip() if pd.notna(r['picklist name']) else None
            ug_code = str(r['Unit of measure dimension code']).upper().strip() if pd.notna(r['Unit of measure dimension code']) else None
            p_len = int(r['property data type length']) if pd.notna(r['property data type length']) and str(r['property data type length']).isdigit() else None

            conn.execute(text("""
                INSERT INTO ontology_core.property (
                    code, name, definition, data_type, length, validation_rule_id, uom_group_id
                )
                VALUES (
                    :c, :n, :def, :dt, :len, 
                    (SELECT id FROM ontology_core.validation_rule WHERE code = :vrc),
                    (SELECT id FROM ontology_core.uom_group WHERE code = :ugc)
                )
                ON CONFLICT (code) DO UPDATE SET 
                    definition = EXCLUDED.definition,
                    data_type = EXCLUDED.data_type,
                    length = EXCLUDED.length,
                    validation_rule_id = EXCLUDED.validation_rule_id,
                    uom_group_id = EXCLUDED.uom_group_id
            """), {
                "c": str(r['Property ID']).upper().strip(), 
                "n": str(r['property name']).upper().strip(),
                "def": r['property definition'],
                "dt": r['property data type'],
                "len": p_len,
                "vrc": pl_ref, 
                "ugc": ug_code
            })
    logger.info("✅ COMPLETED: UoM and Property Layer with updated FK logic.")

@task(name="Sync Unified Class-Property Mapping")
def sync_mappings():
    """
    Merges Tag and Equipment property assignments.
    Now captures raw codes and names from the mapping sheets to identify 
    inconsistencies with the main Property/Class definitions.
    """
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    # 1. Read mapping sheets
    df_tag_map = read_sheet_smart(FILE_PATH, 'Tag class properties', 'Tag class ID')
    df_eq_map = read_sheet_smart(FILE_PATH, 'Equipment class props', 'Equipment class ID')
    
    # 2. Standardize columns to a single format for merging
    # We explicitly keep the 'Name' columns from the mapping sheet
    df_tag_prep = df_tag_map[[
        'Tag class ID', 'Tag Class Name', 'Tag Property ID', 'Tag Property Name'
    ]].rename(columns={
        'Tag class ID': 'class_code_raw',
        'Tag Class Name': 'class_name_raw',
        'Tag Property ID': 'prop_code_raw',
        'Tag Property Name': 'prop_name_raw'
    })
    df_tag_prep['source_type'] = 'Functional'

    df_eq_prep = df_eq_map[[
        'Equipment class ID', 'Equipment Class Name', 'Equipment Property ID', 'Equipment Property Name'
    ]].rename(columns={
        'Equipment class ID': 'class_code_raw',
        'Equipment Class Name': 'class_name_raw',
        'Equipment Property ID': 'prop_code_raw',
        'Equipment Property Name': 'prop_name_raw'
    })
    df_eq_prep['source_type'] = 'Physical'

    # 3. Combine both sources
    # We don't drop duplicates yet because we need to calculate the concept
    combined_maps = pd.concat([df_tag_prep, df_eq_prep])
    
    # Create a unique key for grouping: CLASS_CODE|PROP_CODE
    combined_maps['key'] = (
        combined_maps['class_code_raw'].astype(str).str.upper().str.strip() + "|" + 
        combined_maps['prop_code_raw'].astype(str).str.upper().str.strip()
    )

    # 4. Process unique mappings
    unique_keys = combined_maps['key'].unique()
    new_links = 0
    
    with engine.begin() as conn:
        for key in unique_keys:
            # Get all rows for this specific mapping
            rows = combined_maps[combined_maps['key'] == key]
            
            # Determine mapping concept
            has_functional = 'Functional' in rows['source_type'].values
            has_physical = 'Physical' in rows['source_type'].values
            concept = "Functional Physical" if (has_functional and has_physical) else (
                "Functional" if has_functional else "Physical"
            )
            
            # Take the first available raw values for metadata
            sample = rows.iloc[0]
            c_code = str(sample['class_code_raw']).upper().strip()
            p_code = str(sample['prop_code_raw']).upper().strip()

            conn.execute(text("""
                INSERT INTO ontology_core.class_property (
                    class_id, 
                    property_id, 
                    mapping_concept,
                    mapping_class_code_raw,
                    mapping_class_name_raw,
                    mapping_property_code_raw,
                    mapping_property_name_raw
                )
                VALUES (
                    (SELECT id FROM ontology_core.class WHERE code = :cc),
                    (SELECT id FROM ontology_core.property WHERE code = :pc),
                    :mc,
                    :cc_raw,
                    :cn_raw,
                    :pc_raw,
                    :pn_raw
                ) 
                ON CONFLICT (class_id, property_id) DO UPDATE SET 
                    mapping_concept = EXCLUDED.mapping_concept,
                    mapping_class_name_raw = EXCLUDED.mapping_class_name_raw,
                    mapping_property_name_raw = EXCLUDED.mapping_property_name_raw;
            """), {
                "cc": c_code,
                "pc": p_code,
                "mc": concept,
                "cc_raw": c_code,
                "cn_raw": sample['class_name_raw'],
                "pc_raw": p_code,
                "pn_raw": sample['prop_name_raw']
            })
            new_links += 1

    logger.info(f"✅ COMPLETED: Mapping Matrix. Processed {new_links} links with raw metadata capture.")

@flow(name="Ontology Master Seed", log_prints=True)
def ontology_master_flow():
    logger = get_run_logger()
    
    if FILE_PATH is None or not os.path.exists(FILE_PATH):
        logger.error(f"CRITICAL: Master RDL file not found at {FILE_PATH}")
        return

    sync_validation_rules()
    sync_uom_properties() # Move properties before classes if mapping needed, but here we sync parents separately
    sync_classes()
    sync_mappings()

if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    ontology_master_flow.serve(name="ontology-seeder")