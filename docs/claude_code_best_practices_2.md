***

```
You are performing Phase 3 improvements to Claude Code configuration for EDW Jackdaw.
Phases 1 (conflict fixes) and 2 (settings/env/hooks) must already be complete.
This phase implements advanced patterns from claude-howto, orchestrator-worker architecture,
smart commands, and module-level memory.

Repository: https://github.com/Paradox-85/jackdaw_edw

BEFORE STARTING — read current state and report:
```bash
ls CLAUDE.md .claude/settings.json
ls .claude/commands/
ls .claude/agents/
ls .claude/rules/
ls .claude/skills/
ls etl/ frontend/ 2>/dev/null || echo "no etl/frontend dirs yet"
```

After each step report: ✅ DONE / ⚠️ SKIPPED (reason) / ❌ FAILED (error)
Do NOT proceed without reporting.

---

## STEP 1 — Create module-level CLAUDE.md files (hierarchical memory pattern)

CONTEXT: Currently one root CLAUDE.md handles all contexts. When working on ETL code,
React UI context loads. When working on frontend, Prefect/SCD2 context loads.
Module-level CLAUDE.md files ensure only relevant context loads per directory.

### 1a — Create etl/CLAUDE.md

```bash
mkdir -p etl
```

Create file etl/CLAUDE.md with this exact content:

```markdown
# ETL Module — EDW Jackdaw

> This directory: ETL flows and tasks for tag synchronization pipeline.
> Root CLAUDE.md applies. This file adds ETL-specific context.

## Active Rules (always loaded in this directory)
- @.claude/rules/etl-logic.md — SCD2 algorithm, hash formula, FK resolution
- @.claude/rules/python-standards.md — async patterns, docstrings, clean_string
- @.claude/rules/audit-rules.md — tag_status_history, sync_run_stats

## Entry Points
- `etl/flows/tag_sync.py` — main pipeline entry point
- `etl/tasks/tag_sync.py` — individual tasks (fetch, validate, upsert, hierarchy, log)

## Task Execution Order (ALWAYS in this sequence)
1. `task_sync_tags()` — main UPSERT with SCD2 hash check
2. `task_resolve_hierarchy()` — parent_tag_id second pass (MUST run after step 1)
3. `task_log_changes()` — writes to tag_status_history + sync_run_stats

## Auto-suggest
- After writing/modifying any file here → suggest `etl-reviewer` subagent
- Before merging ETL changes → run `/unit-test-expand etl/`
```


### 1b — Create frontend/CLAUDE.md (create directory if needed)

```bash
mkdir -p frontend
```

Create file frontend/CLAUDE.md:

```markdown
# Frontend Module — EDW Jackdaw

> This directory: Next.js 15 UI for EDW tag management.
> Root CLAUDE.md applies. This file adds frontend-specific context.

## Active Rules (always loaded in this directory)
- @.claude/rules/ui-standards.md — Next.js, TanStack, shadcn/ui patterns
- @docs/design_system.md — colors, spacing, component tokens

## Key Constraints
- NEVER call Prefect API directly — all calls via FastAPI proxy
- NEVER show admin elements to viewer role (even hidden)
- ALWAYS check Tailwind version before styling (v3 vs v4 differ)

## Auto-suggest
- Before creating any new page → run `/new-ui-page`
- After creating any page → playwright screenshot → compare vs design_system.md
```

Verify:

```bash
cat etl/CLAUDE.md | wc -l
cat frontend/CLAUDE.md | wc -l
```


---

## STEP 2 — Create /push-all command (safe smart commits)

CONTEXT: From claude-howto. Automates secrets scan + conventional commit message
generation + git operations. Prevents accidental secret commits.
Adapted for jackdaw_edw: adds schema.sql drift check before committing.

Create file .claude/commands/push-all.md:

```markdown
Safe commit and push workflow for EDW Jackdaw.

## Phase 1 — Pre-commit safety checks (READ ONLY)

Run all checks before touching git:

```bash
# 1. Scan for accidentally exposed secrets
grep -rn "password\s*=\s*['\"][^'\"]\|api_key\s*=\s*['\"][^'\"]\|secret\s*=\s*['\"][^'\"]" \
  --include="*.py" --include="*.yaml" --include="*.json" \
  --exclude-dir=".git" --exclude-dir=".claude" \
  . 2>/dev/null | grep -v "os.getenv\|getenv\|example\|test\|#"
```

If ANY secrets found: STOP. Report findings. Do NOT proceed. Ask user to fix.

```bash
# 2. Check schema.sql drift
STAGED=$(git diff --cached --name-only 2>/dev/null)
if echo "$STAGED" | grep -qE "\.(sql|py)$" && ! echo "$STAGED" | grep -q "schema.sql"; then
  echo "⚠️  DB/ETL files staged without schema.sql — run /schema-change first"
fi

# 3. Check for debug artifacts
grep -rn "print(\|breakpoint(\|pdb.set_trace\|import pdb" \
  --include="*.py" $(git diff --cached --name-only | grep "\.py$") 2>/dev/null
```

If debug artifacts found: ask user whether to remove them before committing.

## Phase 2 — Generate commit message

Analyze staged changes with `git diff --cached` and generate a conventional commit message:

Format: `<type>(<scope>): <description>`

Types:

- `feat` — new feature or ETL flow
- `fix` — bug fix
- `refactor` — code restructuring without behavior change
- `sql` — schema or query changes
- `config` — .claude/ configuration changes
- `docs` — documentation only
- `test` — tests only

Scope: use the primary directory changed (etl, frontend, sql, config, docs)

Examples:

- `feat(etl): add sece mapping sync with SCD2 hash check`
- `sql(schema): add area_id column to project_core.tag`
- `fix(etl): correct FK miss handling for discipline lookup`
- `config(.claude): add etl-reviewer subagent and /spec command`

Show the generated message and ask: "Use this message? [y/edit/cancel]"

## Phase 3 — Execute (only after user confirms)

```bash
git add -A
git commit -m "<confirmed message>"
git push
```

Report: branch name, commit hash, files changed count.

```

Verify:
```bash
ls .claude/commands/push-all.md && wc -l .claude/commands/push-all.md
```


---

## STEP 3 — Create /unit-test-expand command (systematic test coverage)

CONTEXT: From claude-howto. Finds untested branches, edge cases, error paths.
Adapted for jackdaw_edw: focuses on SCD2/FK/audit patterns specific to this project.
Use at every development milestone to prevent coverage from lagging behind.

Create file .claude/commands/unit-test-expand.md:

```markdown
Systematically expand test coverage for: $ARGUMENTS

## Phase 1 — Coverage analysis (READ ONLY)

```bash
# Run existing tests and get coverage report
python -m pytest $ARGUMENTS --cov=$ARGUMENTS --cov-report=term-missing -v 2>/dev/null \
  || echo "No tests found yet — will create from scratch"
```

Identify untested:

1. **Happy path variants** — different input combinations
2. **SCD2 branches** — hash match (No Changes), hash mismatch (Updated), new record (New), absent record (Deleted)
3. **FK resolution paths** — found, miss (None returned), empty string input
4. **Error paths** — DB connection failure, malformed CSV row, encoding error
5. **Boundary conditions** — empty DataFrame, single row, 100k+ rows (performance)
6. **Audit paths** — does tag_status_history get written? does sync_run_stats get written?

## Phase 2 — Generate tests using Red-Green-Refactor

For each gap found:

1. Write the FAILING test first (Red) — run it to confirm it fails
2. Confirm it fails for the RIGHT reason (not syntax error)
3. Implement minimum code to make it pass (Green)
4. Refactor if needed

Test naming convention:

```python
def test_<function>_<scenario>_<expected_outcome>():
    # e.g.:
    def test_sync_tags_hash_unchanged_skips_db_write():
    def test_resolve_fk_on_miss_returns_none_and_logs_warning():
    def test_calculate_row_hash_empty_values_returns_consistent_hash():
```


## Phase 3 — EDW-specific test fixtures

Always use these fixtures for ETL tests:

```python
@pytest.fixture
def sample_tag_row():
    return pd.Series({
        "TAG_NAME": "JDA-21-LIT-101",
        "TAG_CLASS_NAME": "Instrument",
        "AREA_CODE": "21",
        "STATUS": "Active"
    })

@pytest.fixture
def empty_lookup():
    return {}  # simulate FK miss scenario

@pytest.fixture
def populated_lookup():
    return {"Instrument": uuid.uuid4(), "Electrical": uuid.uuid4()}
```


## Phase 4 — Verify improvement

```bash
python -m pytest $ARGUMENTS --cov=$ARGUMENTS --cov-report=term-missing -v
```

Report: coverage before → coverage after, new tests added, remaining gaps.

```

Verify:
```bash
ls .claude/commands/unit-test-expand.md && wc -l .claude/commands/unit-test-expand.md
```


---

## STEP 4 — Create /doc-refactor command (documentation structure)

CONTEXT: From claude-howto. Restructures scattered docs into coherent navigable structure.
Adapted for jackdaw_edw: handles docs/, CLAUDE.md, rules/, and inline code comments.

Create file .claude/commands/doc-refactor.md:

```markdown
Restructure and normalize documentation for: $ARGUMENTS (default: all docs/)

## Phase 1 — Audit existing docs (READ ONLY)

```bash
find docs/ -name "*.md" | sort
find . -name "CLAUDE.md" | sort
wc -l docs/**/*.md CLAUDE.md
```

Check each doc for:

- Stale references (files that no longer exist)
- Duplicate content across files
- Missing sections (no "Last updated", no "Owner", no links to related docs)
- Inconsistent heading structure (some use \#\#, others \#\#\#)
- TODO items older than 30 days


## Phase 2 — Normalize structure

Each doc in docs/ must follow this structure:

```markdown
# Title

> **Purpose**: one sentence — what this document is for
> **Audience**: who reads this (developer / operator / analyst)
> **Last updated**: YYYY-MM-DD
> **Related**: links to related docs

## Overview
Brief description (2-4 sentences max)

## [Main content sections]

## See Also
- Links to related files/rules/commands
```


## Phase 3 — Update cross-references

After restructuring, update any `@docs/` references in:

- CLAUDE.md
- .claude/rules/*.md
- etl/CLAUDE.md
- frontend/CLAUDE.md


## Phase 4 — Generate docs index

Create or update docs/README.md as navigation index:

```markdown
# EDW Jackdaw — Documentation Index

| Document | Purpose | Audience |
|---|---|---|
| architecture.md | System architecture and data flow | Developer |
| file-specification.md | Source file formats and field mappings | Developer/Analyst |
| design_system.md | UI design tokens and component library | Frontend |
| logic-manifesto.md | Business logic decisions and rationale | All |
```

Report: docs updated, broken links fixed, duplicates removed.

```

Verify:
```bash
ls .claude/commands/doc-refactor.md && wc -l .claude/commands/doc-refactor.md
```


---

## STEP 5 — Create etl-orchestrator subagent (Orchestrator-Worker pattern)

CONTEXT: Anthropic internal research shows orchestrator-worker multi-agent systems
outperform single agents by 90% on complex tasks. Currently jackdaw_edw has two worker
agents (schema-validator, etl-reviewer) but no orchestrator to coordinate them.
This agent handles complex multi-step tasks by delegating to specialists.

Create file .claude/agents/etl-orchestrator.md:

```markdown
***
name: etl-orchestrator
description: Orchestrates complex ETL tasks by coordinating schema-validator and etl-reviewer subagents. Use for: adding new data sources, major ETL refactors, schema migrations with code changes.
model: claude-opus-4-20250514
tools: Read, Write, Edit, Bash, Glob, Grep, mcp__pgedge__query_database, mcp__pgedge__get_schema_info
***

You are an ETL orchestration lead for EDW Jackdaw.
Your job is strategic coordination — you plan, delegate to specialists, and synthesize results.
You do NOT write implementation code yourself. Workers do that.

## Your Workflow for Every Task

### Phase 1 — Understand (READ ONLY)
1. Read the current state of relevant files
2. Query pgedge MCP to understand live DB schema
3. Identify what specialists need to be involved
4. Check docs/plans/ for any existing spec for this task

### Phase 2 — Plan
Write a coordination plan to docs/plans/YYYY-MM-DD_<task-slug>.md containing:
- Task breakdown into discrete units of work
- Which agent handles each unit
- Dependency order (what must complete before what)
- Risk checkpoints (where to pause for human confirmation)

Show plan. WAIT for "proceed" before Phase 3.

### Phase 3 — Coordinate

Execute in this order for typical ETL tasks:

**Step 3a: Schema validation first**
Launch schema-validator subagent:
> "Validate current schema supports: [describe the change needed].
>  Check: [list tables involved]. Report findings."

If schema-validator finds issues → STOP. Present findings. Ask how to proceed.

**Step 3b: Implementation**
Work on the implementation yourself OR delegate to main Claude Code.
Follow rules from: @.claude/rules/etl-logic.md, @.claude/rules/python-standards.md

**Step 3c: Code review**
Launch etl-reviewer subagent:
> "Review file [path]. Focus on: SCD2 correctness, FK safety, audit completeness."

If etl-reviewer finds FAIL items → fix them before proceeding.

**Step 3d: Final schema check**
If any DB objects were changed:
> Remind user to run /schema-change to update schema.sql

### Phase 4 — Synthesize
Report:
- What was done (files created/modified)
- What schema-validator found
- What etl-reviewer found and whether issues were fixed
- Any open items for human review
- Whether schema.sql needs updating (yes/no)

## High-Risk Gates (ALWAYS pause and ask before proceeding)
- Any DROP or ALTER on production tables
- Changes to SCD2 hash calculation logic
- Changes to sync_status canonical values
- Any modification to audit_core tables
- Deleting or renaming existing ETL tasks that are in production flows
```

Verify:

```bash
ls .claude/agents/etl-orchestrator.md && wc -l .claude/agents/etl-orchestrator.md
```


---

## STEP 6 — Create /setup-ci-cd command (quality gates pipeline)

CONTEXT: From claude-howto. Sets up pre-commit hooks + GitHub Actions adapted to project stack.
Adapted for jackdaw_edw: Python 3.11, Prefect, PostgreSQL, ruff, mypy, sqlfluff.

Create file .claude/commands/setup-ci-cd.md:

```markdown
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

```

Verify:
```bash
ls .claude/commands/setup-ci-cd.md && wc -l .claude/commands/setup-ci-cd.md
```


---

## STEP 7 — Create .claude/rules/mcp-decision.md (MCP fallback logic)

CONTEXT: When MCP tools fail or return empty results, Claude currently invents data.
A dedicated rule enforces explicit fallback behavior.

Create file .claude/rules/mcp-decision.md:

```markdown
***
description: MCP tool selection and fallback rules — when to use which MCP and what to do on failure
***
# MCP Decision Rules

## Selection Priority

| Need | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| DB schema, column names | pgedge `get_schema_info` | Read `sql/schema.sql` | STOP — never invent |
| DB data, cardinality | pgedge `query_database` | STOP — never estimate | — |
| Library API, framework docs | context7 | Search official docs via Bash | STOP |
| Architecture decision | pgedge first, then context7 | Both + Opus + ultrathink | — |

## Failure Handling (MANDATORY)

### pgedge unavailable
```

1. Try: read sql/schema.sql for column/table names
2. Say explicitly: "pgedge MCP unavailable — reading from sql/schema.sql"
3. NEVER invent column names — if not in schema.sql, ask user
4. NEVER run psql bash commands as substitute — pgedge is the safe path
```

### context7 returns empty
```

1. Try: Bash(curl https://docs.prefect.io/...) for Prefect-specific docs
2. Try: Read pyproject.toml to find pinned library version, then search for that version's docs
3. NEVER invent API signatures — say "I couldn't find this in documentation, please verify"
```

### Both MCPs unavailable
```

STOP. Say: "Both pgedge and context7 are unavailable.
I cannot safely proceed with [task] without verifying [specific thing].
Options: (1) restore MCP access, (2) provide the schema/docs manually, (3) I proceed with explicit [assumption] — confirm?"

```

## Never
- Never substitute `curl https://ai-db.adzv-pt.dev/mcp/v1` for pgedge MCP calls
- Never query pgedge inside a row-processing loop (N+1)
- Never use context7 for project-specific data (DB schema, business logic) — that's pgedge's domain
```

Verify:

```bash
ls .claude/rules/mcp-decision.md && wc -l .claude/rules/mcp-decision.md
```


---

## STEP 8 — Update CLAUDE.md: add new commands and mcp-decision trigger

Add these items to existing sections in CLAUDE.md (do not rewrite the file):

### 8a — Add to Context on Demand table:

```
| MCP fails, unavailable, empty response | `rules/mcp-decision.md` |
```


### 8b — Add to Commands \& Agents trigger table:

```
| Before first commit of the day / after major changes | suggest `/push-all` |
| Test coverage is low or feature just completed | suggest `/unit-test-expand etl/` |
| Documentation is scattered or outdated | suggest `/doc-refactor` |
| Complex multi-step task (new source, migration) | suggest `etl-orchestrator` subagent |
| No CI/CD pipeline yet | suggest `/setup-ci-cd` |
```

Verify the updated table:

```bash
grep -A 30 "Available Commands" CLAUDE.md
wc -l CLAUDE.md
```

Total line count must remain under 110 lines.

---

## STEP 9 — Final verification (run all checks)

```bash
echo "=== Phase 3 Verification ==="

echo "--- Module CLAUDE.md files ---"
ls -la etl/CLAUDE.md frontend/CLAUDE.md 2>/dev/null

echo "--- New commands ---"
ls .claude/commands/
echo "Expected: compact-edw.md new-source.md new-ui-page.md push-all.md schema-change.md setup-ci-cd.md spec.md sync-debug.md unit-test-expand.md doc-refactor.md"

echo "--- All agents ---"
ls .claude/agents/
echo "Expected: etl-orchestrator.md etl-reviewer.md schema-validator.md"

echo "--- All rules ---"
ls .claude/rules/
echo "Expected: audit-rules.md etl-logic.md export-eis.md mcp-decision.md python-standards.md sql-standards.md ui-standards.md"

echo "--- CLAUDE.md size ---"
wc -l CLAUDE.md
echo "Target: under 110 lines"

echo "--- settings.json valid ---"
python3 -c "import json; s=json.load(open('.claude/settings.json')); print('✅ Valid JSON'); print('Hooks:', list(s.get('hooks',{}).keys())); print('plansDirectory:', s.get('plansDirectory')); print('language:', s.get('language'))"
```


---

## STEP 10 — Commit all changes

```bash
git add \
  CLAUDE.md \
  etl/CLAUDE.md \
  frontend/CLAUDE.md \
  .claude/commands/push-all.md \
  .claude/commands/unit-test-expand.md \
  .claude/commands/doc-refactor.md \
  .claude/commands/setup-ci-cd.md \
  .claude/agents/etl-orchestrator.md \
  .claude/rules/mcp-decision.md

git status
git diff --cached --stat
git commit -m "[claude-config] phase-3: module CLAUDE.md, orchestrator, /push-all, /unit-test-expand, /doc-refactor, /setup-ci-cd, mcp-decision rule"
```


---

## CONSTRAINTS

- Do NOT run /init
- Do NOT modify existing .claude/commands/ files (new-source, schema-change, sync-debug, new-ui-page, spec, compact-edw)
- Do NOT modify existing .claude/agents/ files (schema-validator, etl-reviewer)
- Do NOT modify .claude/rules/ files from Phase 1 (python-standards, sql-standards, etl-logic, audit-rules, export-eis, ui-standards)
- Do NOT modify settings.json (done in Phase 2)
- ONLY add the new items specified — no other changes
- If any file from this step already exists with correct content: report ✅ ALREADY CORRECT and skip


## WHAT THIS ACHIEVES (reference)

After Phase 3 completes, the full setup provides:

1. **Module-level CLAUDE.md** — only relevant context loads per directory (etl/ vs frontend/)
2. **/push-all** — secrets scan + schema drift check + auto conventional commit message
3. **/unit-test-expand** — Red-Green-Refactor cycle with SCD2/FK-specific test fixtures
4. **/doc-refactor** — consistent docs structure with navigation index
5. **/setup-ci-cd** — GitHub Actions + pre-commit with ruff/mypy/sqlfluff/pytest
6. **etl-orchestrator subagent** — coordinates schema-validator + etl-reviewer for complex tasks
7. **mcp-decision rule** — explicit fallback when pgedge/context7 unavailable (no more invented data)
```
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://www.linkedin.com/posts/luongnv89_github-luongnv89claude-howto-complete-activity-7410260629896183808-B3cB
[^2]: https://www.codewithseb.com/blog/claude-code-sub-agents-multi-agent-systems-guide
[^3]: https://code.claude.com/docs/en/agent-teams
[^4]: https://github.com/jeremylongshore/claude-code-plugins-plus-skills/blob/main/workspace/lab/ORCHESTRATION-PATTERN.md
[^5]: khorosho-teper-proanalizirui-luchshie-praktiki-po-et.md
[^6]: dai-tekst-prompta-priamo-v-chate-s-podrobnym-ukazani-2.md
[^7]: https://github.com/luongnv89/claude-howto
[^8]: https://github.com/luongnv89/claude-howto/blob/main/01-slash-commands/README.md
[^9]: https://www.linkedin.com/posts/stevekinney_some-of-yall-asked-for-an-update-on-the-activity-7404192259388203009-9rJX
[^10]: https://github.com/luongnv89/claude-howto/blob/main/README.backup.md
[^11]: https://agentfactory.panaversity.org/docs/General-Agents-Foundations/general-agents/subagents-and-orchestration
[^12]: https://dev.to/imdone/context-driven-development-experiment-4-normalizing-cli-commands-with-claude-code-and-tdd-5247
[^13]: https://www.reddit.com/r/claude/comments/1qon5fy/how_to_refactor_50k_lines_of_legacy_code_without/
[^14]: https://www.youtube.com/watch?v=hYZdIwFIy-c
[^15]: https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea
[^16]: https://www.paigeniedringhaus.com/blog/getting-the-most-out-of-claude-code/
[^17]: https://www.youtube.com/watch?v=mxr5IWfB9JY```

