Set up CI/CD quality gates for EDW Jackdaw.

## Phase 1 — Check existing setup

```bash
ls .github/workflows/ 2>/dev/null || echo "No GitHub Actions yet"
cat .pre-commit-config.yaml 2>/dev/null || echo "No pre-commit config yet"
cat pyproject.toml 2>/dev/null | grep -A5 "\[tool\."
```

## Phase 2 — Create .pre-commit-config.yaml

If not exists, create:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        args: [--strict, --ignore-missing-imports]
        files: ^(etl|frontend)/.*\.py$

  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 3.0.0
    hooks:
      - id: sqlfluff-lint
        args: [--dialect, postgres]
        files: ^sql/.*\.sql$

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: detect-private-key
      - id: check-json
      - id: check-yaml
```

## Phase 3 — Create GitHub Actions workflow

Create .github/workflows/ci.yml:

```yaml
name: EDW Jackdaw CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install ruff mypy pytest pytest-cov sqlfluff

      - name: Lint with ruff
        run: ruff check .

      - name: Type check with mypy
        run: mypy etl/ --strict --ignore-missing-imports

      - name: SQL lint with sqlfluff
        run: sqlfluff lint sql/ --dialect postgres

      - name: Run tests
        run: |
          pytest tests/ -v --cov=etl --cov-report=xml --cov-fail-under=60

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
```

## Phase 4 — Install and verify

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Report: hooks installed, any failures found.
