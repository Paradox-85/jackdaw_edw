"""
etl/flows/export_eis_data_deploy.py — EIS Full Package Export

Sequential pipeline that runs all 11 EIS export flows in order.
Mirrors the pattern of import_master_sync_deploy.py.

Deployment name: export-eis-package-deployment
Parameters:
    doc_revision: EIS revision code, e.g. "A35" (pattern [A-Z]\\d{2})
                  Each sub-flow uses its own output path from config.
"""
import re
import sys
from pathlib import Path

from prefect import flow, get_run_logger

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from flows.export_tag_register_deploy import export_tag_register_flow
    from flows.export_equipment_register_deploy import export_equipment_register_flow
    from flows.export_model_part_deploy import export_model_part_flow
    from flows.export_tag_connections_deploy import export_tag_connections_flow
    from flows.export_purchase_order_deploy import export_purchase_order_flow
    from flows.export_area_register_deploy import export_area_register_flow
    from flows.export_process_unit_deploy import export_process_unit_flow
    from flows.export_tag_properties_deploy import export_tag_properties_flow
    from flows.export_equipment_properties_deploy import export_equipment_properties_flow
    from flows.export_tag_class_properties_deploy import export_tag_class_properties_flow
    from flows.export_document_crossref_deploy import export_document_crossref_flow
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import flow modules. Details: {e}")
    sys.exit(0)


@flow(name="export_eis_package_data", log_prints=True, description="SEQUENTIAL PIPELINE: all 11 EIS export flows — registers, properties, connections, doc cross-refs.")
def export_eis_package_flow(doc_revision: str = "A35") -> dict[str, dict]:
    """
    Run all EIS export flows sequentially to produce a complete EIS data package.

    Sub-flows are executed in dependency order: registers first, then derived
    tables (properties, connections), then document cross-references last.

    Args:
        doc_revision: EIS revision code, e.g. "A35". Must match [A-Z]\\d{2}.

    Returns:
        Dict mapping flow name to its result dict (exported row count + violations).

    Raises:
        ValueError: If doc_revision format is invalid.
    """
    logger = get_run_logger()

    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. Expected format: [A-Z]\\d{{2}} (e.g. 'A35')."
        )

    logger.info(f"Starting EIS Full Package Export | revision={doc_revision}")

    steps = [
        # Core registers
        ("tag_register",          export_tag_register_flow),           # seq 003
        ("equipment_register",    export_equipment_register_flow),      # seq 004
        ("model_part",            export_model_part_flow),              # seq 209
        ("tag_connections",       export_tag_connections_flow),         # seq 212
        ("purchase_order",        export_purchase_order_flow),          # seq 214
        ("area_register",         export_area_register_flow),           # seq 203
        ("process_unit",          export_process_unit_flow),            # seq 204
        # Property value exports
        ("tag_properties",        export_tag_properties_flow),          # seq 303
        ("equipment_properties",  export_equipment_properties_flow),    # seq 301
        # Ontology
        ("tag_class_properties",  export_tag_class_properties_flow),    # seq 307
        # Document cross-references (runs 8 sub-flows internally)
        ("document_crossref",     export_document_crossref_flow),       # seq 408-420
    ]

    results: dict[str, dict] = {}
    for name, fn in steps:
        logger.info(f">>> Step: {name}")
        results[name] = fn(doc_revision=doc_revision)

    logger.info(f"EIS Full Package Export completed | revision={doc_revision}")
    return results


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_eis_package_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_eis_data_deploy.py:export_eis_package_flow",
    ).deploy(
        name="export_eis_package_data_deploy",
        work_pool_name="default-agent-pool",
        tags=["production", "eis-export", "full-package"],
    )
