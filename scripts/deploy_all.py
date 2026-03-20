"""
scripts/deploy_all.py — Register all *_deploy.py Prefect flows.

Discovers every *_deploy.py file in etl/flows/, runs it as a subprocess
(each script registers itself via __main__ block), and reports results.

Usage:
    python scripts/deploy_all.py

Requires: Prefect worker is running and PREFECT_API_URL is set.
"""
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_FLOWS_DIR = _HERE.parent.parent / "etl" / "flows"


def main() -> None:
    scripts = sorted(_FLOWS_DIR.glob("*_deploy.py"))
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
        print(f"[WARN] Failed ({len(failed)}): {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"[DONE] All {len(scripts)} deployments registered successfully.")


if __name__ == "__main__":
    main()
