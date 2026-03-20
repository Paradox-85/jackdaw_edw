"""Prefect flow: seed reference_core layer from Master Reference Data Excel."""

import os
import re
import sys
from pathlib import Path

import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

# Setup paths
current_dir = Path(__file__).resolve().parent
script_root = current_dir.parent
if str(script_root) not in sys.path:
    sys.path.append(str(script_root))

from tasks.common import (
    load_config,
    get_db_engine_url,
    normalize_to_id_code,
    parse_bool,
    get_object_status,
)

# Load config
config = load_config()
DB_URL = get_db_engine_url(config)
FILE_PATH = config.get("storage", {}).get("master_reference_file")


# ---------------------------------------------------------------------------
# Normalization helpers (module-private)
# ---------------------------------------------------------------------------

def _nc(val: object) -> str | None:
    """Strict code normalization: alphanumeric + UPPER (no hyphens or underscores)."""
    # Delegates to normalize_to_id_code which strips [^A-Z0-9] and converts UPPER
    if pd.isna(val) or str(val).strip() == "":
        return None
    return normalize_to_id_code(str(val))


def _nn(val: object) -> str | None:
    """Light name/text normalize: UPPER + collapse multiple spaces + strip."""
    if pd.isna(val) or str(val).strip() == "":
        return None
    return re.sub(r" {2,}", " ", str(val).upper().strip()) or None


def _float(val: object) -> float | None:
    """Convert to float, return None for blank/non-numeric values."""
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Shared utilities
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
        >>> df = read_sheet_smart(path, "site", "code")
    """
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    for i, row in df_raw.iterrows():
        if header_keyword in row.values:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=i)
            return df.loc[:, df.columns.notna()].copy()
    return pd.DataFrame()


def _get_id_map(conn: Connection, table: str) -> dict[str, str]:
    """
    Pre-load {code: id} dict from reference_core.{table} for FK resolution.

    Args:
        conn: Active SQLAlchemy connection.
        table: Table name within reference_core schema.

    Returns:
        Dict mapping normalized code to UUID string.
    """
    return {
        row[0]: row[1]
        for row in conn.execute(text(f"SELECT code, id FROM reference_core.{table}"))
    }


# ---------------------------------------------------------------------------
# Prefect tasks — load order follows FK dependency tree
# ---------------------------------------------------------------------------

@task(name="Seed Root Tables", cache_policy=NO_CACHE)
def seed_root_tables(engine: Engine) -> None:
    """
    Upsert root reference tables (no FK dependencies) from Master Reference Excel.

    Loads five independent tables in one transaction:
    site, company, sece, discipline, po_package.

    Returns:
        None. Logs row counts per table.
    """
    logger = get_run_logger()
    stats: dict[str, int] = {}

    df_site  = read_sheet_smart(FILE_PATH, "site",       "code")
    df_co    = read_sheet_smart(FILE_PATH, "company",    "code")
    df_sece  = read_sheet_smart(FILE_PATH, "sece",       "code")
    df_disc  = read_sheet_smart(FILE_PATH, "discipline", "code")
    df_pkg   = read_sheet_smart(FILE_PATH, "po_package", "code")

    with engine.begin() as conn:
        # site
        count = 0
        for _, r in df_site.dropna(subset=["code"]).iterrows():
            conn.execute(text("""
                INSERT INTO reference_core.site (code, name, object_status)
                VALUES (:c, :n, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    object_status = EXCLUDED.object_status
            """), {"c": _nc(r["code"]), "n": _nn(r["name"]),
                   "os": get_object_status(r.get("object_status"))})
            count += 1
        stats["site"] = count

        # company
        count = 0
        for _, r in df_co.dropna(subset=["code"]).iterrows():
            conn.execute(text("""
                INSERT INTO reference_core.company (
                    code, name, address, town_city, zip_code, country_code,
                    phone, email, website, contact_person,
                    is_manufacturer, is_supplier, object_status
                )
                VALUES (
                    :c, :n, :addr, :city, :zip, :ctry,
                    :ph, :em, :web, :cp,
                    :is_mfr, :is_sup, :os
                )
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    town_city = EXCLUDED.town_city,
                    zip_code = EXCLUDED.zip_code,
                    country_code = EXCLUDED.country_code,
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    website = EXCLUDED.website,
                    contact_person = EXCLUDED.contact_person,
                    is_manufacturer = EXCLUDED.is_manufacturer,
                    is_supplier = EXCLUDED.is_supplier,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]),
                "n": _nn(r["name"]),
                "addr": _nn(r.get("address")),
                "city": _nn(r.get("town_city")),
                "zip": _nn(r.get("zip_code")),
                "ctry": _nn(r.get("country_code")),
                "ph": _nn(r.get("phone")),
                "em": _nn(r.get("email")),
                "web": _nn(r.get("website")),
                "cp": _nn(r.get("contact_person")),
                "is_mfr": parse_bool(r.get("is_manufacturer")),
                "is_sup": parse_bool(r.get("is_supplier")),
                "os": get_object_status(r.get("object_status")),
            })
            count += 1
        stats["company"] = count

        # sece
        count = 0
        for _, r in df_sece.dropna(subset=["code"]).iterrows():
            conn.execute(text("""
                INSERT INTO reference_core.sece (code, name, object_status)
                VALUES (:c, :n, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    object_status = EXCLUDED.object_status
            """), {"c": _nc(r["code"]), "n": _nn(r["name"]),
                   "os": get_object_status(r.get("object_status"))})
            count += 1
        stats["sece"] = count

        # discipline
        count = 0
        for _, r in df_disc.dropna(subset=["code"]).iterrows():
            conn.execute(text("""
                INSERT INTO reference_core.discipline (code, name, code_internal, object_status)
                VALUES (:c, :n, :ci, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    code_internal = EXCLUDED.code_internal,
                    object_status = EXCLUDED.object_status
            """), {"c": _nc(r["code"]), "n": _nn(r["name"]),
                   "ci": _nn(r.get("code_internal")),
                   "os": get_object_status(r.get("object_status"))})
            count += 1
        stats["discipline"] = count

        # po_package
        count = 0
        for _, r in df_pkg.dropna(subset=["code"]).iterrows():
            conn.execute(text("""
                INSERT INTO reference_core.po_package (code, name, object_status)
                VALUES (:c, :n, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    object_status = EXCLUDED.object_status
            """), {"c": _nc(r["code"]), "n": _nn(r["name"]),
                   "os": get_object_status(r.get("object_status"))})
            count += 1
        stats["po_package"] = count

    logger.info(f"Root tables seeded: {stats}")


@task(name="Seed Plant and Project", cache_policy=NO_CACHE)
def seed_plant_project(engine: Engine) -> None:
    """
    Upsert plant and project records linked to site via site_code FK.

    Both sheets use 'site_code' column to resolve site_id.
    Stores site_code_raw for traceability.

    Returns:
        None. Logs row counts.
    """
    logger = get_run_logger()

    df_plant   = read_sheet_smart(FILE_PATH, "plant",   "code")
    df_project = read_sheet_smart(FILE_PATH, "project", "code")

    with engine.begin() as conn:
        site_map = _get_id_map(conn, "site")

        # plant
        plant_count = 0
        for _, r in df_plant.dropna(subset=["code"]).iterrows():
            site_code = _nc(r.get("site_code"))
            conn.execute(text("""
                INSERT INTO reference_core.plant (code, name, site_id, site_code_raw, object_status)
                VALUES (:c, :n, :sid, :scr, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    site_id = EXCLUDED.site_id,
                    site_code_raw = EXCLUDED.site_code_raw,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]), "n": _nn(r["name"]),
                "sid": site_map.get(site_code),
                "scr": site_code,
                "os": get_object_status(r.get("object_status")),
            })
            plant_count += 1

        # project
        project_count = 0
        for _, r in df_project.dropna(subset=["code"]).iterrows():
            site_code = _nc(r.get("site_code"))
            conn.execute(text("""
                INSERT INTO reference_core.project (code, name, site_id, site_code_raw, object_status)
                VALUES (:c, :n, :sid, :scr, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    site_id = EXCLUDED.site_id,
                    site_code_raw = EXCLUDED.site_code_raw,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]), "n": _nn(r["name"]),
                "sid": site_map.get(site_code),
                "scr": site_code,
                "os": get_object_status(r.get("object_status")),
            })
            project_count += 1

    logger.info(f"Plant seeded: {plant_count}, Project seeded: {project_count}")


@task(name="Seed Area and Process Unit", cache_policy=NO_CACHE)
def seed_area_process_unit(engine: Engine) -> None:
    """
    Upsert area and process_unit records linked to plant via plant_code FK.

    Both sheets use 'plant_code' column to resolve plant_id.
    area additionally stores main_area_code and plant_code_raw.

    Returns:
        None. Logs row counts.
    """
    logger = get_run_logger()

    df_area = read_sheet_smart(FILE_PATH, "area",         "code")
    df_pu   = read_sheet_smart(FILE_PATH, "process_unit", "code")

    with engine.begin() as conn:
        plant_map = _get_id_map(conn, "plant")

        # area
        area_count = 0
        for _, r in df_area.dropna(subset=["code"]).iterrows():
            plant_code = _nc(r.get("plant_code"))
            conn.execute(text("""
                INSERT INTO reference_core.area (
                    code, name, plant_id, plant_code_raw, main_area_code, object_status
                )
                VALUES (:c, :n, :pid, :pcr, :mac, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    plant_id = EXCLUDED.plant_id,
                    plant_code_raw = EXCLUDED.plant_code_raw,
                    main_area_code = EXCLUDED.main_area_code,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]), "n": _nn(r["name"]),
                "pid": plant_map.get(plant_code),
                "pcr": plant_code,
                "mac": _nc(r.get("main_area_code")),
                "os": get_object_status(r.get("object_status")),
            })
            area_count += 1

        # process_unit
        pu_count = 0
        for _, r in df_pu.dropna(subset=["code"]).iterrows():
            plant_code = _nc(r.get("plant_code"))
            conn.execute(text("""
                INSERT INTO reference_core.process_unit (
                    code, name, plant_id, plant_code_raw, object_status
                )
                VALUES (:c, :n, :pid, :pcr, :os)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    plant_id = EXCLUDED.plant_id,
                    plant_code_raw = EXCLUDED.plant_code_raw,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]), "n": _nn(r["name"]),
                "pid": plant_map.get(plant_code),
                "pcr": plant_code,
                "os": get_object_status(r.get("object_status")),
            })
            pu_count += 1

    logger.info(f"Area seeded: {area_count}, Process unit seeded: {pu_count}")


@task(name="Seed Model Part", cache_policy=NO_CACHE)
def seed_model_part(engine: Engine) -> None:
    """
    Upsert model_part records linked to company via manuf_company_raw FK.

    Unique constraint is (manuf_company_raw, code) — not just code alone,
    since the same part code may exist across different manufacturers.

    Returns:
        None. Logs row count.
    """
    logger = get_run_logger()

    df_mp = read_sheet_smart(FILE_PATH, "model_part", "code")

    with engine.begin() as conn:
        company_map = _get_id_map(conn, "company")

        count = 0
        for _, r in df_mp.dropna(subset=["code"]).iterrows():
            manuf_raw = _nc(r.get("manuf_company_raw"))
            conn.execute(text("""
                INSERT INTO reference_core.model_part (
                    code, name, definition, manufacturer_id, manuf_company_raw, object_status
                )
                VALUES (:c, :n, :def, :mid, :mcr, :os)
                ON CONFLICT (manuf_company_raw, code) DO UPDATE SET
                    name = EXCLUDED.name,
                    definition = EXCLUDED.definition,
                    manufacturer_id = EXCLUDED.manufacturer_id,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]),
                "n": _nn(r["name"]),
                "def": _nn(r.get("definition")),
                "mid": company_map.get(manuf_raw),
                "mcr": manuf_raw,
                "os": get_object_status(r.get("object_status")),
            })
            count += 1

    logger.info(f"Model part seeded: {count}")


@task(name="Seed Purchase Order", cache_policy=NO_CACHE)
def seed_purchase_order(engine: Engine) -> None:
    """
    Upsert purchase_order records linked to po_package and company (issuer + receiver).

    Raw FK columns in Excel: package_code_raw, issuer_company_raw, receiver_company_raw.
    Resolves UUID FKs via pre-loaded po_package and company maps.

    Returns:
        None. Logs row count.
    """
    logger = get_run_logger()

    df_po = read_sheet_smart(FILE_PATH, "purchase_order", "code")

    with engine.begin() as conn:
        pkg_map     = _get_id_map(conn, "po_package")
        company_map = _get_id_map(conn, "company")

        count = 0
        for _, r in df_po.dropna(subset=["code"]).iterrows():
            pkg_raw      = _nc(r.get("package_code_raw"))
            issuer_raw   = _nc(r.get("issuer_company_raw"))
            receiver_raw = _nc(r.get("receiver_company_raw"))
            conn.execute(text("""
                INSERT INTO reference_core.purchase_order (
                    code, name, definition, po_date,
                    package_id, issuer_id, receiver_id,
                    package_code_raw, issuer_company_raw, receiver_company_raw,
                    object_status
                )
                VALUES (
                    :c, :n, :def, :dt,
                    :pkid, :isid, :rcid,
                    :pkr, :isr, :rcr,
                    :os
                )
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    definition = EXCLUDED.definition,
                    po_date = EXCLUDED.po_date,
                    package_id = EXCLUDED.package_id,
                    issuer_id = EXCLUDED.issuer_id,
                    receiver_id = EXCLUDED.receiver_id,
                    package_code_raw = EXCLUDED.package_code_raw,
                    issuer_company_raw = EXCLUDED.issuer_company_raw,
                    receiver_company_raw = EXCLUDED.receiver_company_raw,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]),
                "n": _nn(r["name"]),
                "def": _nn(r.get("definition")),
                "dt": _nn(r.get("po_date")),
                "pkid": pkg_map.get(pkg_raw),
                "isid": company_map.get(issuer_raw),
                "rcid": company_map.get(receiver_raw),
                "pkr": pkg_raw,
                "isr": issuer_raw,
                "rcr": receiver_raw,
                "os": get_object_status(r.get("object_status")),
            })
            count += 1

    logger.info(f"Purchase order seeded: {count}")


@task(name="Seed Article", cache_policy=NO_CACHE)
def seed_article(engine: Engine) -> None:
    """
    Upsert article records linked to company (manufacturer) and model_part.

    Raw FK columns in Excel: manufacturer_company_name_raw, model_part_code_raw.
    Numeric fields: cable_cross_sectional_area, cable_outer_diameter (float, nullable).

    Returns:
        None. Logs row count.
    """
    logger = get_run_logger()

    df_art = read_sheet_smart(FILE_PATH, "article", "code")

    with engine.begin() as conn:
        company_map    = _get_id_map(conn, "company")
        model_part_map = _get_id_map(conn, "model_part")

        count = 0
        for _, r in df_art.dropna(subset=["code"]).iterrows():
            mfr_raw = _nc(r.get("manufacturer_company_name_raw"))
            mp_raw  = _nc(r.get("model_part_code_raw"))
            conn.execute(text("""
                INSERT INTO reference_core.article (
                    code, name, definition, article_type, basic_construction,
                    cable_cross_sectional_area, cable_outer_diameter,
                    commodity_code,
                    manufacturer_id, manufacturer_el_number, manufacturer_material,
                    manufacturer_sap_code, product_family,
                    model_part_id,
                    manufacturer_company_name_raw, model_part_code_raw,
                    object_status
                )
                VALUES (
                    :c, :n, :def, :at, :bc,
                    :ccs, :cod,
                    :cc,
                    :mid, :mel, :mmt,
                    :msc, :pf,
                    :mpid,
                    :mcnr, :mpcr,
                    :os
                )
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    definition = EXCLUDED.definition,
                    article_type = EXCLUDED.article_type,
                    basic_construction = EXCLUDED.basic_construction,
                    cable_cross_sectional_area = EXCLUDED.cable_cross_sectional_area,
                    cable_outer_diameter = EXCLUDED.cable_outer_diameter,
                    commodity_code = EXCLUDED.commodity_code,
                    manufacturer_id = EXCLUDED.manufacturer_id,
                    manufacturer_el_number = EXCLUDED.manufacturer_el_number,
                    manufacturer_material = EXCLUDED.manufacturer_material,
                    manufacturer_sap_code = EXCLUDED.manufacturer_sap_code,
                    product_family = EXCLUDED.product_family,
                    model_part_id = EXCLUDED.model_part_id,
                    manufacturer_company_name_raw = EXCLUDED.manufacturer_company_name_raw,
                    model_part_code_raw = EXCLUDED.model_part_code_raw,
                    object_status = EXCLUDED.object_status
            """), {
                "c": _nc(r["code"]),
                "n": _nn(r["name"]),
                "def": _nn(r.get("definition")),
                "at": _nn(r.get("article_type")),
                "bc": _nn(r.get("basic_construction")),
                "ccs": _float(r.get("cable_cross_sectional_area")),
                "cod": _float(r.get("cable_outer_diameter")),
                "cc": _nc(r.get("commodity_code")),
                "mid": company_map.get(mfr_raw),
                "mel": _nn(r.get("manufacturer_el_number")),
                "mmt": _nn(r.get("manufacturer_material")),
                "msc": _nn(r.get("manufacturer_sap_code")),
                "pf": _nn(r.get("product_family")),
                "mpid": model_part_map.get(mp_raw),
                "mcnr": mfr_raw,
                "mpcr": mp_raw,
                "os": get_object_status(r.get("object_status")),
            })
            count += 1

    logger.info(f"Article seeded: {count}")


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="Reference Data Seed", log_prints=True)
def seed_reference_flow() -> None:
    """
    Full reference_core seed pipeline from Master Reference Data Excel.

    Execution order follows FK dependency tree:
    1. seed_root_tables     — site, company, sece, discipline, po_package (no FKs)
    2. seed_plant_project   — plant, project (→ site)
    3. seed_area_process_unit — area, process_unit (→ plant)
    4. seed_model_part      — model_part (→ company)
    5. seed_purchase_order  — purchase_order (→ po_package + company)
    6. seed_article         — article (→ company + model_part)

    Returns:
        None.

    Raises:
        SystemExit: If master_reference_file is not found at configured path.

    Example:
        >>> seed_reference_flow()
    """
    logger = get_run_logger()

    if FILE_PATH is None or not os.path.exists(FILE_PATH):
        logger.error(f"Master reference file not found at '{FILE_PATH}' — aborting")
        return

    engine = create_engine(DB_URL)

    seed_root_tables(engine)
    seed_plant_project(engine)
    seed_area_process_unit(engine)
    seed_model_part(engine)
    seed_purchase_order(engine)
    seed_article(engine)


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    seed_reference_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/import_reference_deploy.py:seed_reference_flow",
    ).deploy(
        name="reference-data-seeder",
        work_pool_name="default-agent-pool",
    )
