"""
scripts/deploy_all.py — Register all *_deploy.py Prefect flows.

Discovers every *_deploy.py file in etl/flows/, runs it as a subprocess
(each script registers itself via __main__ block), and reports results.

Registered deployments:
  - import_*_deploy.py  — all ETL import flows
  - export_eis_data_deploy.py — master EIS export (runs all 11 sub-flows sequentially)

Individual export_*_deploy.py flows are intentionally excluded — they are
orchestrated by export_eis_data_deploy.py and do not need their own deployments.

Usage:
    python scripts/deploy_all.py

Requires: Prefect worker is running and PREFECT_API_URL is set.
"""
import re
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_FLOWS_DIR = _HERE.parent.parent / "etl" / "flows"

# Exclude individual export flows — they are sub-flows of export_eis_data_deploy.py.
# export_eis_data_deploy.py itself is kept (negative lookahead: eis_data is allowed).
_SKIP = re.compile(r"^export_(?!eis_data)")


def main() -> None:
    all_scripts = sorted(_FLOWS_DIR.glob("*_deploy.py"))
    scripts = [s for s in all_scripts if not _SKIP.match(s.name)]
    if not scripts:
        print(f"[WARN] No *_deploy.py files found in {_FLOWS_DIR}")
        return

    failed = []
    for script in scripts:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
        )
        status = "OK " if result.returncode == 0 else "ERR"
        print(f"[{status}] {script.name}")
        if result.returncode != 0:
            print(result.stderr.strip())
            failed.append(script.name)

    print()
    if failed:
        print(f"[WARN] Completed with errors. Failed scripts: {', '.join(failed)}")
    else:
        print(f"[DONE] All {len(scripts)} deployments registered successfully.")

if __name__ == "__main__":
    main()
