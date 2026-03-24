"""Prefect flow: seed ontology layer from Master RDL Excel (classes, UoM, properties, mappings)."""

import os
import re
import sys
from pathlib import Path

import pandas as pd
from prefect import flow, task, get_run_logger
from sqlalchemy import create_engine, text

# Setup paths
current_dir = Path(__file__).resolve().parent
script_root = current_dir.parent
if str(script_root) not in sys.path:
    sys.path.append(str(script_root))

try:
    from tasks.common import load_config, get_db_engine_url
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Load config
config = load_config()
DB_URL = get_db_engine_url(config)
FILE_PATH = config.get("storage", {}).get("master_rdl")


# ---------------------------------------------------------------------------
# Normalization helpers (module-private)
# ---------------------------------------------------------------------------

def _nc(val: object) -> str | None:
    """Normalize code field: uppercase + strip whitespace. Preserves hyphens and underscores."""
    # pd.isna() handles float NaN, None, pd.NA, pd.NaT uniformly
    if pd.isna(val):
        return None
    s = str(val).upper().strip()
    return s or None


def _nn(val: object) -> str | None:
    """Normalize name/definition: uppercase + collapse multiple spaces + strip."""
    if pd.isna(val):
        return None
    s = re.sub(r" {2,}", " ", str(val).upper().strip())
    return s or None


# ---------------------------------------------------------------------------
# Shared Excel reader
# ---------------------------------------------------------------------------

def read_sheet_smart(file_path: str, sheet_name: str, header_keyword: str) -> pd.DataFrame:
    """
    Find the header row by keyword and return a clean DataFrame.

    Scans sheet rows until header_keyword is found, then re-reads with
    that row as the header — avoids consuming the first data row.

    Args:
        file_path: Path to the Excel workbook.
        sheet_name: Name of the target sheet.
        header_keyword: A cell value expected in the header row.

    Returns:
        DataFrame with correct header and no empty columns.
        Empty DataFrame if keyword not found.

    Example:
        >>> df = read_sheet_smart(path, "Tag class", "Tag Class ID")
    """
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    for i, row in df_raw.iterrows():
        if header_keyword in row.values:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=i)
            return df.loc[:, df.columns.notna()].copy()
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="Sync Validation Rules")
def sync_validation_rules() -> None:
    """
    Upsert picklist validation rules from RDL Excel into ontology_core.validation_rule.

    Reads 'Property picklist' and 'Property picklist value' sheets, builds
    regex patterns of the form (value1|value2|...) per picklist, then
    INSERT ON CONFLICT UPDATE.

    Returns:
        None. Logs created/updated counts.
    """
    logger = get_run_logger()
    engine = create_engine(DB_URL)

    df_pl = read_sheet_smart(FILE_PATH, "Property picklist", "Id")
    df_vals = read_sheet_smart(FILE_PATH, "Property picklist value ", "Picklist ID")

    stats = {"created": 0, "updated": 0}
    with engine.begin() as conn:
        for _, pl in df_pl.iterrows():
            pl_id = _nc(pl["Id"])
            if pl_id is None:
                continue
            # Normalize both sides of the comparison to avoid case/whitespace mismatches
            items = df_vals[df_vals["Picklist ID"].apply(_nc) == pl_id]["Picklist Item Name"].dropna().unique()
            if len(items) > 0:
                regex_val = f"({'|'.join(map(str, items))})"
                res = conn.execute(text("""
                    INSERT INTO ontology_core.validation_rule (code, name, validation_type, validation_value)
                    VALUES (:c, :n, 'picklist', :v)
                    ON CONFLICT (code) DO UPDATE SET
                        validation_value = EXCLUDED.validation_value,
                        name = EXCLUDED.name
                    RETURNING (xmax = 0) AS inserted;
                """), {"c": pl_id, "n": _nn(pl["Name"]), "v": regex_val})

                if res.fetchone()[0]:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

    logger.info(f"Validation rules synced: {stats['created']} created, {stats['updated']} updated")


@task(name="Sync Unified Classes")
def sync_classes() -> None:
    """
    Upsert ontology classes (Functional + Physical) from RDL Excel.

    Reads 'Tag class' (Functional) and 'Equipment class' (Physical) sheets,
    merges them into a unified class list with concept assignment, then:
    - Step A: upsert all classes with is_abstract flag
    - Step B: resolve parent_class_id using pre-loaded code→id mapping

    Parent resolution uses in-memory dict lookup — no per-row SQL queries.

    Returns:
        None. Logs synced/abstract counts.
    """
    logger = get_run_logger()
    engine = create_engine(DB_URL)

    df_tag = read_sheet_smart(FILE_PATH, "Tag class", "Tag Class ID")
    df_eq = read_sheet_smart(FILE_PATH, "Equipment class", "Equipment Class ID")

    def process_df(
        df: pd.DataFrame, c_col: str, n_col: str, p_col: str, d_col: str
    ) -> pd.DataFrame:
        df = df.dropna(subset=[c_col]).copy()
        df = df[[c_col, n_col, p_col, d_col]].rename(
            columns={c_col: "code", n_col: "name", p_col: "parent_code", d_col: "definition"}
        )
        df["code"] = df["code"].apply(_nc)
        df["name"] = df["name"].apply(_nn)
        df["definition"] = df["definition"].apply(_nn)
        df["parent_code"] = df["parent_code"].apply(_nc)
        return df.dropna(subset=["code"])

    df_tag_c = process_df(df_tag, "Tag Class ID", "Tag Class Name", "Parent Class ID", "Tag class definition")
    df_eq_c = process_df(df_eq, "Equipment Class ID", "Equipment Class Name", "Parent Class ID", "Equipment class definition")

    all_data = pd.concat([df_tag_c, df_eq_c]).drop_duplicates(subset=["code"])

    # A class is abstract if it appears as a parent to at least one other class
    parent_codes = set(all_data["parent_code"].dropna().unique())

    stats = {"synced": 0, "abstract": 0}

    with engine.begin() as conn:
        # Step A: upsert all classes
        for _, row in all_data.iterrows():
            code = row["code"]
            is_tag = code in df_tag_c["code"].values
            is_eq = code in df_eq_c["code"].values
            concept = "Functional Physical" if (is_tag and is_eq) else ("Functional" if is_tag else "Physical")
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
                "n": row["name"] or code,
                "d": row["definition"],
                "cp": concept,
                "abs": is_abstract,
            })
            stats["synced"] += 1
            if is_abstract:
                stats["abstract"] += 1

        # Step B: resolve parent hierarchy using pre-loaded code→id map (zero per-row SQL)
        class_id_map = {
            row[0]: row[1]
            for row in conn.execute(text("SELECT code, id FROM ontology_core.class"))
        }
        for _, row in all_data.iterrows():
            # After process_df() normalizes via _nc(), codes are already upper+stripped
            parent_code = row["parent_code"]
            if parent_code and parent_code != "NAN":
                parent_id = class_id_map.get(parent_code)
                if parent_id:
                    conn.execute(text(
                        "UPDATE ontology_core.class SET parent_class_id = :pid WHERE code = :c"
                    ), {"pid": parent_id, "c": row["code"]})

    logger.info(f"Classes synced: {stats['synced']} total, {stats['abstract']} abstract")


@task(name="Sync UoM and Property Layer")
def sync_uom_properties() -> None:
    """
    Upsert UoM dimensions, units of measure, and properties from RDL Excel.

    Reads three sheets in sequence:
    1. 'Unit of measure dimension' → ontology_core.uom_group
    2. 'Unit of measure' → ontology_core.uom (linked to uom_group via code)
    3. 'Property' → ontology_core.property (linked to validation_rule + uom_group)

    Args:
        None (uses module-level FILE_PATH and DB_URL).

    Returns:
        None. Logs completion.
    """
    logger = get_run_logger()
    engine = create_engine(DB_URL)

    df_dim = read_sheet_smart(FILE_PATH, "Unit of measure dimension", "Unique ID")
    df_uom = read_sheet_smart(FILE_PATH, "Unit of measure", "Unique ID")
    df_prop = read_sheet_smart(FILE_PATH, "Property", "Property ID")

    with engine.begin() as conn:
        # 1. UoM Groups (Dimensions)
        for _, r in df_dim.iterrows():
            conn.execute(text("""
                INSERT INTO ontology_core.uom_group (code, name)
                VALUES (:c, :n)
                ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
            """), {"c": _nc(r["Unique ID"]), "n": _nn(r["Dimension Name"])})

        # 2. UoMs — linked to group via UoM Group ID column
        uom_group_col = "UoM Group ID" if "UoM Group ID" in df_uom.columns else "UoM Dimension"
        for _, r in df_uom.iterrows():
            conn.execute(text("""
                INSERT INTO ontology_core.uom (code, name, symbol, uom_group_id)
                VALUES (:c, :n, :s, (SELECT id FROM ontology_core.uom_group WHERE code = :gc))
                ON CONFLICT (code) DO NOTHING
            """), {
                "c": _nc(r["Unique ID"]),
                "n": _nn(r["UoM Name"]),
                "s": _nn(r["UoM Symbol"]),
                "gc": _nc(r[uom_group_col]),
            })

        # 3. Properties — full metadata including data_type, length, definition
        for _, r in df_prop.iterrows():
            p_len = int(r["property data type length"]) if (
                pd.notna(r["property data type length"])
                and str(r["property data type length"]).isdigit()
            ) else None

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
                "c": _nc(r["Property ID"]),
                "n": _nn(r["property name"]),
                "def": _nn(r["property definition"]),
                "dt": r["property data type"],
                "len": p_len,
                "vrc": _nc(r["picklist name"]),
                "ugc": _nc(r["Unit of measure dimension code"]),
            })

    logger.info("UoM and Property layer synced")


@task(name="Sync Unified Class-Property Mapping")
def sync_mappings() -> None:
    """
    Upsert class-property mapping matrix from Tag and Equipment property sheets.

    Merges 'Tag class properties' (Functional) and 'Equipment class props' (Physical)
    into unified ontology_core.class_property entries with concept assignment.
    Stores raw codes and names for auditability.

    Returns:
        None. Logs number of processed mapping links.
    """
    logger = get_run_logger()
    engine = create_engine(DB_URL)

    df_tag_map = read_sheet_smart(FILE_PATH, "Tag class properties", "Tag class ID")
    df_eq_map = read_sheet_smart(FILE_PATH, "Equipment class props", "Equipment class ID")

    df_tag_prep = df_tag_map[[
        "Tag class ID", "Tag Class Name", "Tag Property ID", "Tag Property Name"
    ]].rename(columns={
        "Tag class ID": "class_code_raw",
        "Tag Class Name": "class_name_raw",
        "Tag Property ID": "prop_code_raw",
        "Tag Property Name": "prop_name_raw",
    })
    df_tag_prep["source_type"] = "Functional"

    df_eq_prep = df_eq_map[[
        "Equipment class ID", "Equipment Class Name", "Equipment Property ID", "Equipment Property Name"
    ]].rename(columns={
        "Equipment class ID": "class_code_raw",
        "Equipment Class Name": "class_name_raw",
        "Equipment Property ID": "prop_code_raw",
        "Equipment Property Name": "prop_name_raw",
    })
    df_eq_prep["source_type"] = "Physical"

    combined_maps = pd.concat([df_tag_prep, df_eq_prep])
    combined_maps["key"] = (
        combined_maps["class_code_raw"].astype(str).str.upper().str.strip() + "|"
        + combined_maps["prop_code_raw"].astype(str).str.upper().str.strip()
    )

    unique_keys = combined_maps["key"].unique()
    new_links = 0

    with engine.begin() as conn:
        for key in unique_keys:
            rows = combined_maps[combined_maps["key"] == key]
            has_functional = "Functional" in rows["source_type"].values
            has_physical = "Physical" in rows["source_type"].values
            concept = "Functional Physical" if (has_functional and has_physical) else (
                "Functional" if has_functional else "Physical"
            )
            sample = rows.iloc[0]
            c_code = _nc(sample["class_code_raw"])
            p_code = _nc(sample["prop_code_raw"])

            conn.execute(text("""
                INSERT INTO ontology_core.class_property (
                    class_id, property_id, mapping_concept,
                    mapping_class_code_raw, mapping_class_name_raw,
                    mapping_property_code_raw, mapping_property_name_raw
                )
                VALUES (
                    (SELECT id FROM ontology_core.class WHERE code = :cc),
                    (SELECT id FROM ontology_core.property WHERE code = :pc),
                    :mc, :cc_raw, :cn_raw, :pc_raw, :pn_raw
                )
                ON CONFLICT (class_id, property_id) DO UPDATE SET
                    mapping_concept = EXCLUDED.mapping_concept,
                    mapping_class_name_raw = EXCLUDED.mapping_class_name_raw,
                    mapping_property_name_raw = EXCLUDED.mapping_property_name_raw;
            """), {
                "cc": c_code, "pc": p_code, "mc": concept,
                "cc_raw": c_code, "cn_raw": _nn(sample["class_name_raw"]),
                "pc_raw": p_code, "pn_raw": _nn(sample["prop_name_raw"]),
            })
            new_links += 1

    logger.info(f"Class-property mapping matrix synced: {new_links} links processed")


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="import_ontology_data", log_prints=True)
def ontology_master_flow() -> None:
    """
    Full ontology seed pipeline from Master RDL Excel.

    Execution order (dependencies):
    1. sync_validation_rules — picklist regex rules (required by properties)
    2. sync_uom_properties   — UoM groups, units, properties (requires validation rules)
    3. sync_classes          — tag + equipment classes with hierarchy
    4. sync_mappings         — class-property matrix (requires classes + properties)

    Returns:
        None.

    Raises:
        SystemExit: If master_rdl file is not found at configured path.

    Example:
        >>> ontology_master_flow()
    """
    logger = get_run_logger()

    if FILE_PATH is None or not os.path.exists(FILE_PATH):
        logger.error(f"Master RDL file not found at '{FILE_PATH}' — aborting")
        return

    sync_validation_rules()
    sync_uom_properties()
    sync_classes()
    sync_mappings()


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    ontology_master_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/import_ontology_deploy.py:ontology_master_flow",
    ).deploy(
        name="import_ontology_data_deploy",
        work_pool_name="default-agent-pool",
    )
