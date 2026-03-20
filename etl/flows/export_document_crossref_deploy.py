"""Reverse ETL export flows: Document Cross-Reference Exports (EIS seq 408, 409, 410, 411, 412, 413, 414, 420)."""

import re
import sys
from pathlib import Path

import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Setup import path so tasks.* resolves from etl/
current_dir = Path(__file__).resolve().parent
script_root = current_dir.parent
if str(script_root) not in sys.path:
    sys.path.append(str(script_root))

from tasks.common import load_config, get_db_engine_url
from tasks.export_transforms import (
    transform_doc_to_site,
    transform_doc_to_plant,
    transform_doc_to_process_unit,
    transform_doc_to_area,
    transform_doc_to_tag,
    transform_doc_to_equipment,
    transform_doc_to_model_part,
    transform_doc_to_po,
)
from tasks.export_pipeline import run_export_pipeline

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# Common document filter fragment (reused across all SQL queries)
# ---------------------------------------------------------------------------
# Gate:  object_status='Active', mdr_flag=TRUE, status NOT NULL and NOT 'CAN'
_DOC_GATE = """
    d.object_status = 'Active'
    AND d.mdr_flag = TRUE
    AND d.status IS NOT NULL
    AND UPPER(COALESCE(d.status, '')) != 'CAN'
"""

# Common tag filter fragment (seq 410, 411, 412, 413, 414)
_TAG_GATE = """
    t.object_status = 'Active'
    AND UPPER(COALESCE(t.tag_status, '')) NOT IN ('VOID', '')
"""

# ---------------------------------------------------------------------------
# SQL: Seq 408 — Doc → Site
# ---------------------------------------------------------------------------

_DOC_TO_SITE_SQL = """
/*
Purpose: Document→Site cross-reference for EIS snapshot export (seq 408).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         Plant and site resolved via FK; empty string if unresolved (LEFT JOIN).
Changes: 2026-03-17 — Initial implementation.
*/
SELECT
    d.doc_number                            AS DOCUMENT_NUMBER,
    COALESCE(s.code, '')                    AS SITE_CODE,
    d.object_status
FROM project_core.document d
LEFT JOIN reference_core.plant pl   ON d.plant_id  = pl.id AND pl.object_status = 'Active'
LEFT JOIN reference_core.site  s    ON pl.site_id  = s.id  AND s.object_status  = 'Active'
WHERE d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
ORDER BY d.doc_number
"""

_FILE_408 = "JDAW-KVE-E-JA-6944-00001-024-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Seq 409 — Doc → Plant
# ---------------------------------------------------------------------------

_DOC_TO_PLANT_SQL = """
/*
Purpose: Document→Plant cross-reference for EIS snapshot export (seq 409).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         Plant resolved via FK; empty string if unresolved (LEFT JOIN).
Changes: 2026-03-17 — Initial implementation.
*/
SELECT
    d.doc_number                            AS DOCUMENT_NUMBER,
    COALESCE(pl.code, '')                   AS PLANT_CODE,
    d.object_status
FROM project_core.document d
LEFT JOIN reference_core.plant pl   ON d.plant_id = pl.id AND pl.object_status = 'Active'
WHERE d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
ORDER BY d.doc_number
"""

_FILE_409 = "JDAW-KVE-E-JA-6944-00001-023-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Seq 410 — Doc → Process Unit
# ---------------------------------------------------------------------------

_DOC_TO_PROCESS_UNIT_SQL = """
/*
Purpose: Document→ProcessUnit cross-reference for EIS snapshot export (seq 410).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         tag: object_status='Active', tag_status NOT VOID/empty.
         DISTINCT: remove duplicate (doc, process_unit) pairs from multi-tag joins.
Source:  mapping.tag_document → tag.process_unit_id → process_unit.
Changes: 2026-03-17 — Initial implementation.
*/
SELECT DISTINCT
    d.doc_number                              AS DOCUMENT_NUMBER,
    COALESCE(pu.code, '')                     AS PROCESS_UNIT_CODE,
    d.object_status
FROM mapping.tag_document m
INNER JOIN project_core.document       d   ON m.document_id      = d.id
INNER JOIN project_core.tag            t   ON m.tag_id            = t.id
LEFT  JOIN reference_core.process_unit pu  ON t.process_unit_id  = pu.id
               AND pu.object_status = 'Active'
WHERE m.mapping_status = 'Active'
  AND d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
  AND t.object_status = 'Active'
  AND UPPER(COALESCE(t.tag_status, '')) NOT IN ('VOID', '')
  AND t.process_unit_id IS NOT NULL
ORDER BY d.doc_number, pu.code
"""

_FILE_410 = "JDAW-KVE-E-JA-6944-00001-018-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Seq 411 — Doc → Area
# ---------------------------------------------------------------------------

_DOC_TO_AREA_SQL = """
/*
Purpose: Document→Area cross-reference for EIS snapshot export (seq 411).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         tag: object_status='Active', tag_status NOT VOID/empty.
         DISTINCT: remove duplicate (doc, area) pairs from multi-tag joins.
Source:  mapping.tag_document → tag.area_id → area.
Changes: 2026-03-17 — Initial implementation.
*/
SELECT DISTINCT
    d.doc_number                            AS DOCUMENT_NUMBER,
    COALESCE(a.code, '')                    AS AREA_CODE,
    d.object_status
FROM mapping.tag_document m
INNER JOIN project_core.document  d  ON m.document_id = d.id
INNER JOIN project_core.tag       t  ON m.tag_id      = t.id
LEFT  JOIN reference_core.area    a  ON t.area_id     = a.id
               AND a.object_status = 'Active'
WHERE m.mapping_status = 'Active'
  AND d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
  AND t.object_status = 'Active'
  AND UPPER(COALESCE(t.tag_status, '')) NOT IN ('VOID', '')
  AND t.area_id IS NOT NULL
ORDER BY d.doc_number, a.code
"""

_FILE_411 = "JDAW-KVE-E-JA-6944-00001-017-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Seq 412 — Doc → Tag
# ---------------------------------------------------------------------------

_DOC_TO_TAG_SQL = """
/*
Purpose: Document→Tag cross-reference for EIS snapshot export (seq 412).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         mapping: mapping_status='Active'.
         tag: object_status='Active', tag_status NOT VOID/empty.
Source:  mapping.tag_document.
Changes: 2026-03-17 — Initial implementation.
*/
SELECT
    d.doc_number                            AS DOCUMENT_NUMBER,
    COALESCE(pl.code, '')                   AS PLANT_CODE,
    t.tag_name                              AS TAG_NAME,
    d.object_status
FROM mapping.tag_document m
INNER JOIN project_core.document d   ON m.document_id = d.id
INNER JOIN project_core.tag      t   ON m.tag_id      = t.id
LEFT  JOIN reference_core.plant  pl  ON t.plant_id    = pl.id AND pl.object_status = 'Active'
WHERE m.mapping_status = 'Active'
  AND d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
  AND t.object_status = 'Active'
  AND UPPER(COALESCE(t.tag_status, '')) NOT IN ('VOID', '')
ORDER BY d.doc_number, t.tag_name
"""

_FILE_412 = "JDAW-KVE-E-JA-6944-00001-016-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Seq 413 — Doc → Equipment
# ---------------------------------------------------------------------------

_DOC_TO_EQUIPMENT_SQL = """
/*
Purpose: Document→Equipment cross-reference for EIS snapshot export (seq 413).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         tag: object_status='Active', tag_status NOT VOID/empty.
         class: concept ILIKE '%Physical%' — excludes pure Functional classes
                (e.g. instrument loops, signals).
         tag.equip_no IS NOT NULL and non-empty.
Source:  mapping.tag_document → tag (Physical class only) → tag.equip_no.
Changes: 2026-03-17 — Initial implementation.
*/
SELECT
    d.doc_number                            AS DOCUMENT_NUMBER,
    COALESCE(pl.code, '')                   AS PLANT_CODE,
    COALESCE(t.equip_no, '')                AS EQUIPMENT_NUMBER,
    d.object_status
FROM mapping.tag_document m
INNER JOIN project_core.document  d    ON m.document_id = d.id
INNER JOIN project_core.tag       t    ON m.tag_id      = t.id
INNER JOIN ontology_core.class    cls  ON t.class_id    = cls.id
LEFT  JOIN reference_core.plant   pl   ON t.plant_id    = pl.id AND pl.object_status = 'Active'
WHERE m.mapping_status = 'Active'
  AND d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
  AND t.object_status = 'Active'
  AND UPPER(COALESCE(t.tag_status, '')) NOT IN ('VOID', '')
  AND cls.concept ILIKE '%Physical%'
  AND t.equip_no IS NOT NULL
  AND t.equip_no != ''
ORDER BY d.doc_number, t.equip_no
"""

_FILE_413 = "JDAW-KVE-E-JA-6944-00001-019-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Seq 414 — Doc → Model Part
# ---------------------------------------------------------------------------

_DOC_TO_MODEL_PART_SQL = """
/*
Purpose: Document→ModelPart cross-reference for EIS snapshot export (seq 414).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         tag: object_status='Active', tag_status NOT VOID/empty.
         DISTINCT: remove duplicate (doc, model_part) pairs from multi-tag joins.
Source:  mapping.tag_document → tag.model_id → model_part.
Changes: 2026-03-17 — Initial implementation.
*/
SELECT DISTINCT
    d.doc_number                            AS DOCUMENT_NUMBER,
    COALESCE(pl.code, '')                   AS PLANT_CODE,
    COALESCE(mp.code, '')                   AS MODEL_PART_CODE,
    d.object_status
FROM mapping.tag_document m
INNER JOIN project_core.document      d   ON m.document_id = d.id
INNER JOIN project_core.tag           t   ON m.tag_id      = t.id
INNER JOIN reference_core.model_part  mp  ON t.model_id    = mp.id
LEFT  JOIN reference_core.plant       pl  ON t.plant_id    = pl.id AND pl.object_status = 'Active'
WHERE m.mapping_status = 'Active'
  AND d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
  AND t.object_status = 'Active'
  AND UPPER(COALESCE(t.tag_status, '')) NOT IN ('VOID', '')
ORDER BY d.doc_number, mp.code
"""

_FILE_414 = "JDAW-KVE-E-JA-6944-00001-020-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Seq 420 — Doc → Purchase Order
# ---------------------------------------------------------------------------

_DOC_TO_PO_SQL = """
/*
Purpose: Document→PurchaseOrder cross-reference for EIS snapshot export (seq 420).
Gate:    document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
         mapping: mapping_status='Active'.
         purchase_order: object_status='Active'.
Source:  mapping.document_po.
Changes: 2026-03-17 — Initial implementation.
*/
SELECT
    d.doc_number                            AS DOCUMENT_NUMBER,
    COALESCE(pl.code, '')                   AS PLANT_CODE,
    COALESCE(po.code, '')                   AS PO_CODE,
    d.object_status
FROM mapping.document_po m
INNER JOIN project_core.document         d   ON m.document_id = d.id
INNER JOIN reference_core.purchase_order po  ON m.po_id       = po.id
LEFT  JOIN reference_core.plant          pl  ON d.plant_id    = pl.id AND pl.object_status = 'Active'
WHERE m.mapping_status = 'Active'
  AND d.object_status = 'Active'
  AND d.mdr_flag = TRUE
  AND d.status IS NOT NULL
  AND UPPER(COALESCE(d.status, '')) != 'CAN'
  AND po.object_status = 'Active'
ORDER BY d.doc_number, po.code
"""

_FILE_420 = "JDAW-KVE-E-JA-6944-00001-022-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks (one per export)
# ---------------------------------------------------------------------------

@task(name="extract-doc-to-site", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_site(engine: Engine) -> pd.DataFrame:
    """Run Doc→Site SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_SITE_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→site rows")
    return df


@task(name="extract-doc-to-plant", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_plant(engine: Engine) -> pd.DataFrame:
    """Run Doc→Plant SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_PLANT_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→plant rows")
    return df


@task(name="extract-doc-to-process-unit", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_process_unit(engine: Engine) -> pd.DataFrame:
    """Run Doc→ProcessUnit SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_PROCESS_UNIT_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→process_unit rows")
    return df


@task(name="extract-doc-to-area", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_area(engine: Engine) -> pd.DataFrame:
    """Run Doc→Area SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_AREA_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→area rows")
    return df


@task(name="extract-doc-to-tag", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_tag(engine: Engine) -> pd.DataFrame:
    """Run Doc→Tag SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_TAG_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→tag rows")
    return df


@task(name="extract-doc-to-equipment", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_equipment(engine: Engine) -> pd.DataFrame:
    """Run Doc→Equipment SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_EQUIPMENT_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→equipment rows")
    return df


@task(name="extract-doc-to-model-part", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_model_part(engine: Engine) -> pd.DataFrame:
    """Run Doc→ModelPart SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_MODEL_PART_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→model_part rows")
    return df


@task(name="extract-doc-to-po", retries=1, cache_policy=NO_CACHE)
def extract_doc_to_po(engine: Engine) -> pd.DataFrame:
    """Run Doc→PurchaseOrder SQL query and return raw DataFrame."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_DOC_TO_PO_SQL), conn)
    logger.info(f"Extracted {len(df)} doc→po rows")
    return df


# ---------------------------------------------------------------------------
# Helper: revision validation
# ---------------------------------------------------------------------------

def _validate_revision(doc_revision: str) -> None:
    """Raise ValueError if doc_revision does not match [A-Z]\\d{2}."""
    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. "
            f"Expected format: [A-Z]\\d{{2}} (e.g. 'A35')."
        )


# ---------------------------------------------------------------------------
# Prefect flows (one per EIS sequence)
# ---------------------------------------------------------------------------

@flow(name="export-doc-to-site", log_prints=True)
def export_doc_to_site_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→Site cross-reference to EIS CSV snapshot (seq 408).

    Output file: JDAW-KVE-E-JA-6944-00001-024-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_408.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_site,
        transform_fn=transform_doc_to_site,
        output_path=output_path,
        report_name="doc_to_site",
        logger=logger,
    )


@flow(name="export-doc-to-plant", log_prints=True)
def export_doc_to_plant_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→Plant cross-reference to EIS CSV snapshot (seq 409).

    Output file: JDAW-KVE-E-JA-6944-00001-023-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_409.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_plant,
        transform_fn=transform_doc_to_plant,
        output_path=output_path,
        report_name="doc_to_plant",
        logger=logger,
    )


@flow(name="export-doc-to-process-unit", log_prints=True)
def export_doc_to_process_unit_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→ProcessUnit cross-reference to EIS CSV snapshot (seq 410).

    Output file: JDAW-KVE-E-JA-6944-00001-018-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
                 tag: object_status='Active', tag_status NOT VOID/empty.
    Dedup:       DISTINCT on (doc, process_unit) — prevents repeated pairs.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_410.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_process_unit,
        transform_fn=transform_doc_to_process_unit,
        output_path=output_path,
        report_name="doc_to_process_unit",
        logger=logger,
    )


@flow(name="export-doc-to-area", log_prints=True)
def export_doc_to_area_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→Area cross-reference to EIS CSV snapshot (seq 411).

    Output file: JDAW-KVE-E-JA-6944-00001-017-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
                 tag: object_status='Active', tag_status NOT VOID/empty.
    Dedup:       DISTINCT on (doc, area) — prevents repeated pairs.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_411.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_area,
        transform_fn=transform_doc_to_area,
        output_path=output_path,
        report_name="doc_to_area",
        logger=logger,
    )


@flow(name="export-doc-to-tag", log_prints=True)
def export_doc_to_tag_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→Tag cross-reference to EIS CSV snapshot (seq 412).

    Output file: JDAW-KVE-E-JA-6944-00001-016-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
                 mapping: mapping_status='Active'.
                 tag: object_status='Active', tag_status NOT VOID/empty.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_412.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_tag,
        transform_fn=transform_doc_to_tag,
        output_path=output_path,
        report_name="doc_to_tag",
        logger=logger,
    )


@flow(name="export-doc-to-equipment", log_prints=True)
def export_doc_to_equipment_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→Equipment cross-reference to EIS CSV snapshot (seq 413).

    Output file: JDAW-KVE-E-JA-6944-00001-019-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
                 tag: object_status='Active', tag_status NOT VOID/empty.
                 class: concept ILIKE '%Physical%' (excludes pure Functional classes).
                 tag.equip_no IS NOT NULL and non-empty.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_413.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_equipment,
        transform_fn=transform_doc_to_equipment,
        output_path=output_path,
        report_name="doc_to_equipment",
        logger=logger,
    )


@flow(name="export-doc-to-model-part", log_prints=True)
def export_doc_to_model_part_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→ModelPart cross-reference to EIS CSV snapshot (seq 414).

    Output file: JDAW-KVE-E-JA-6944-00001-020-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
                 tag: object_status='Active', tag_status NOT VOID/empty.
    Dedup:       DISTINCT on (doc, model_part) — prevents repeated pairs.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_414.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_model_part,
        transform_fn=transform_doc_to_model_part,
        output_path=output_path,
        report_name="doc_to_model_part",
        logger=logger,
    )


@flow(name="export-doc-to-po", log_prints=True)
def export_doc_to_po_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Document→PurchaseOrder cross-reference to EIS CSV snapshot (seq 420).

    Output file: JDAW-KVE-E-JA-6944-00001-022-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: document: object_status='Active', mdr_flag=TRUE, status NOT NULL/CAN.
                 mapping: mapping_status='Active'.
                 purchase_order: object_status='Active'.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    logger = get_run_logger()
    _validate_revision(doc_revision)
    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_420.format(revision=doc_revision)
    return run_export_pipeline(
        engine=engine,
        scope="doc_crossref",
        extract_fn=extract_doc_to_po,
        transform_fn=transform_doc_to_po,
        output_path=output_path,
        report_name="doc_to_po",
        logger=logger,
    )


# ---------------------------------------------------------------------------
# Master flow — runs all 8 exports in sequence
# ---------------------------------------------------------------------------

@flow(name="export-document-crossref", log_prints=True)
def export_document_crossref_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, dict[str, int]]:
    """
    Export all Document Cross-Reference registers to EIS CSV snapshots (seq 408–420).

    Runs all 8 sub-flows in sequence:
      408 DocToSite, 409 DocToPlant, 410 DocToProcessUnit, 411 DocToArea,
      412 DocToTag, 413 DocToEquipment, 414 DocToModelPart, 420 DocToPO.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict mapping register name → {"exported": N, "violations": M}.

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.
    """
    _validate_revision(doc_revision)
    kwargs = {"doc_revision": doc_revision, "output_dir": output_dir}
    return {
        "doc_to_site":         export_doc_to_site_flow(**kwargs),
        "doc_to_plant":        export_doc_to_plant_flow(**kwargs),
        "doc_to_process_unit": export_doc_to_process_unit_flow(**kwargs),
        "doc_to_area":         export_doc_to_area_flow(**kwargs),
        "doc_to_tag":          export_doc_to_tag_flow(**kwargs),
        "doc_to_equipment":    export_doc_to_equipment_flow(**kwargs),
        "doc_to_model_part":   export_doc_to_model_part_flow(**kwargs),
        "doc_to_po":           export_doc_to_po_flow(**kwargs),
    }


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_document_crossref_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_document_crossref_deploy.py:export_document_crossref_flow",
    ).deploy(
        name="export-document-crossref-deployment",
        work_pool_name="default-agent-pool",
    )
