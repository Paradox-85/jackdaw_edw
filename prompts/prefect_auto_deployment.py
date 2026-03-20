import subprocess
import ast
from pathlib import Path

ETL_DIR = Path("/mnt/shared-data/ram-user/Jackdaw/EDW-repository/etl/flows")

def has_deploy_call(path: Path) -> bool:
    """Проверяет наличие .deploy( вызова через AST без исполнения файла."""
    try:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # Ищем паттерн: что-то.deploy(...)
                if isinstance(func, ast.Attribute) and func.attr == "deploy":
                    return True
    except SyntaxError as e:
        print(f"[SYNTAX ERROR] {path.name}: {e}")
    return False

if __name__ == "__main__":
    failed = []
    skipped = []

    for script in sorted(ETL_DIR.glob("*.py")):
        if not has_deploy_call(script):
            print(f"[SKIP] {script.name} — no .deploy() call found")
            skipped.append(script.name)
            continue

        print(f"[DEPLOY] Registering {script.name}...")
        result = subprocess.run(
            ["python", str(script)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"[ERROR] {script.name}:\n{result.stderr}")
            failed.append(script.name)
        else:
            print(f"[OK] {script.name}")

    if skipped:
        print(f"\n[WARN] Skipped (no deploy): {', '.join(skipped)}")
    if failed:
        print(f"[WARN] Failed: {', '.join(failed)}")
    else:
        print("\n[DONE] All deployments registered.")
