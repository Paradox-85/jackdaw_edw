---
disable-model-invocation: true
---
Enter safe specification mode for task: $ARGUMENTS

## Phase 0 — Generate plan filename

Determine the plan filename BEFORE starting exploration:

```bash
PLAN_DATE=$(date +%Y.%m.%d)
```

If $ARGUMENTS is NOT empty:
  PLAN_SLUG=$(echo "$ARGUMENTS" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)
  PLAN_FILE="docs/plans/cc_${PLAN_DATE}_${PLAN_SLUG}.md"

If $ARGUMENTS IS empty:
  Analyze the user's LAST message in conversation to extract 3-5 keywords describing the task.
  Generate PLAN_SLUG from those keywords in kebab-case (lowercase, hyphens, no spaces, max 40 chars).
  PLAN_FILE="docs/plans/cc_${PLAN_DATE}_${PLAN_SLUG}.md"

Examples of auto-generated names:
  "add EIS export sequence mapping"   → cc_2026.04.06_eis-export-sequence-mapping.md
  "fix FK miss on discipline lookup"  → cc_2026.04.06_fix-fk-miss-discipline-lookup.md
  "refactor tag sync SCD2 hash"       → cc_2026.04.06_tag-sync-scd2-hash-refactor.md

Check for collision:
```bash
ls docs/plans/ | grep "cc_${PLAN_DATE}_${PLAN_SLUG}" 2>/dev/null && echo "collision" || echo "ok"
```
If collision exists: append -2, -3 etc. to PLAN_SLUG.

Report chosen filename to user BEFORE Phase 1:
"📋 Plan will be saved to: docs/plans/cc_YYYY.MM.DD_slug.md"

## Phase 1 — Explore (READ ONLY — make ZERO file changes in this phase)
1. Read all files relevant to the task using Read, Grep, Glob tools
2. If task involves schema: query pgedge MCP to get current DB state
3. If anything is ambiguous: use AskUserQuestion tool to ask me — do NOT assume
4. Do NOT create files, do NOT edit files, do NOT run Bash write commands

## Phase 2 — Design
1. Write implementation plan to $PLAN_FILE (determined in Phase 0)
2. Plan must contain ALL of these sections:
   - **Problem** (1-2 sentences)
   - **Files to modify** (exact paths, what changes in each)
   - **Files to create** (exact paths, what goes in each)
   - **SQL changes** (if any) — does schema.sql need updating? yes/no
   - **Implementation order** (numbered steps)
   - **Risks and edge cases**
   - **Verification** (how to confirm the change worked)
3. Show me the complete plan
4. WAIT for me to type exactly "proceed" — do not start implementation until then

## Phase 3 — Implement (ONLY after I type "proceed")
1. Execute the plan step by step
2. After each file change: report what changed and why
3. If any DB objects modified: run /schema-change
4. After any ETL file modified: run etl-reviewer subagent
5. Run verification steps from the plan

Then commit:
git add .claude/commands/spec.md
git commit -m "[config] spec command: auto-generate plan filename cc_YYYY.MM.DD_slug.md"
