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
  echo "WARNING: DB/ETL files staged without schema.sql — run /schema-change first"
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
