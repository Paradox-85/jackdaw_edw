
***

```
You are performing a complete audit and improvement of Claude Code configuration for EDW Jackdaw.
Repository: https://github.com/Paradox-85/jackdaw_edw

BEFORE STARTING — read these files and report current state:
- CLAUDE.md (show line count)
- .claude/settings.json (show full contents)
- .claude/rules/ (list all files)
- .claude/skills/ (list all directories)
- .claude/agents/ (list all files)
- .claude/commands/ (list all files)

Then execute each step sequentially.
After each step report: ✅ DONE / ⚠️ SKIPPED (reason) / ❌ FAILED (error)
Do NOT proceed to the next step without reporting the result.

---

## STEP 1 — Rewrite CLAUDE.md to remove duplication and fix broken sections

PROBLEM: CLAUDE.md contains full code blocks (Python, Pandas, SQL, SCD2 hash, Prefect flows)
that are already present in .claude/rules/ files. This causes context bloat every session.
The UI/UX section is also truncated/broken with a stray fragment at the bottom.

Rewrite CLAUDE.md keeping ONLY these sections:

1. Header block (Stack, MCP, GitHub, References) — unchanged
2. ## 🔴 CRITICAL RULES — all 6 rules, unchanged
3. ## 📚 Context on Demand — NEW section, exact text provided below
4. ## 🗂️ Available Commands & Agents — trigger table, add 2 new rows (see below)
5. ## MCP Usage — table, unchanged
6. ## Database Access Rules — unchanged
7. ## Model Selection + Session Management — unchanged, add 1 new line (see below)
8. ## File Layout — keep the directory tree, remove inline Russian comments from each line
9. ## Code Review Checklist — unchanged

REMOVE these sections entirely:
- ## Code Standards (Python, Pandas, SQL, FK resolution — all code blocks)
- ## Domain Logic — SCD Type 2 (entire section: Hash Computation, Tag History Pattern, Audit Logging, Tag Hierarchy Resolution with all code examples)
- ## UI/UX STANDARDS (broken/truncated section)
- The stray fragment "### 2.7 .gitignore — add" at the bottom

ADD this as new ## 📚 Context on Demand section (place it right after ## 🔴 CRITICAL RULES):

```


## 📚 Context on Demand

Rules load automatically when keywords match — do NOT duplicate their content here.


| Keywords in conversation | Rule auto-loaded |
| :-- | :-- |
| hash, SCD, sync_status, upsert, tag_history | `rules/etl-logic.md` |
| python, async, docstring, clean_string, type hint | `rules/python-standards.md` |
| SQL, schema, UPSERT, CREATE TABLE, FK | `rules/sql-standards.md` |
| audit, log_entry, tag_status_history | `rules/audit-rules.md` |
| EIS, export, seq, sequence | `rules/export-eis.md` |
| component, tsx, React, TanStack, shadcn, Tailwind | `rules/ui-standards.md` |

```

ADD these 2 rows to the existing ## 🗂️ Available Commands & Agents trigger table:
```

| After writing or modifying any ETL task/flow file | suggest running `etl-reviewer` subagent |
| Context approaching 70% | suggest `/compact-edw` |

```

ADD this line to the Session Management block under ## Model Selection:
```

- `/compact-edw` — Compact with EDW-specific state preservation (task, files, DB, SCD2 state)

```

After rewriting, verify:
```bash
wc -l CLAUDE.md
```

Target: under 80 lines. If over 80 — identify which section is still bloated and trim further.

---

## STEP 2 — Fix hash formula conflict (DATA INTEGRITY RISK)

PROBLEM: Two different hash formulas exist and produce different results for the same row.

CURRENT in .claude/skills/scd2-rules/skill.md:
`md5(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()`

CANONICAL in .claude/rules/etl-logic.md:
`hashlib.md5("|".join(str(v) for v in row.values).encode()).hexdigest()`

In file .claude/skills/scd2-rules/skill.md make 3 changes:

1. Replace the hash formula line with:
**Hash:** `hashlib.md5("|".join(str(v) for v in row.values).encode()).hexdigest()`
2. Replace the status values line with:
**Status values:** `New | Updated | No Changes | Deleted`
(reason: "No Changes" exists in sql-standards.md but was missing from this skill)
3. Add this note after the \#\# Rules section:
```
> ⚠️ Hash formula must match `rules/etl-logic.md` exactly.
> Never use json.dumps for hashing — field order differs between implementations.
```

Verify:

```bash
grep "Hash:" .claude/skills/scd2-rules/skill.md
grep "Status values" .claude/skills/scd2-rules/skill.md
```


---

## STEP 3 — Fix TIMESTAMP vs TIMESTAMPTZ conflict in sql-standards.md

PROBLEM: Direct contradiction between two authoritative sources.

- .claude/rules/sql-standards.md says: `TIMESTAMP DEFAULT now()` (not TIMESTAMPTZ unless needed)
- CLAUDE.md says: `timestamps as TIMESTAMP WITH TIME ZONE`
TIMESTAMPTZ is correct for production systems.

In file .claude/rules/sql-standards.md find the line:
`**Timestamps**: `TIMESTAMP DEFAULT now()` (not TIMESTAMPTZ unless explicitly needed)`

Replace with:
`**Timestamps**: `TIMESTAMP WITH TIME ZONE DEFAULT now()` — always TIMESTAMPTZ, never naive TIMESTAMP`

Verify:

```bash
grep -n "TIMESTAMP" .claude/rules/sql-standards.md | head -5
```

Should show TIMESTAMPTZ only — no bare TIMESTAMP for column definitions.

---

## STEP 4 — Create .claude/rules/ui-standards.md

The UI/UX content was removed from CLAUDE.md in Step 1. It needs a proper rule file.

Create file .claude/rules/ui-standards.md with this exact content:

```markdown
***
description: UI standards — Next.js 15, React, TanStack Table v8, shadcn/ui, Tailwind CSS
***
# UI/UX Standards (React Frontend)

## Stack
Framework: Next.js 15 App Router + TypeScript + shadcn/ui + Tailwind CSS
Tables: TanStack Table v8 — useReactTable() API, server-side pagination
Data: React Query v5 — staleTime:60_000, gcTime:300_000, retry:1
Icons: Lucide React only

## Always
- Read @docs/design_system.md before any UI work
- Use /new-ui-page command for new pages
- After every new page: playwright screenshot → compare vs design_system.md → fix deviations

## Never
- Call Prefect API from React — FastAPI proxies all backend calls
- Show admin elements to viewer role (even hidden with CSS)
- Use inline hex colors — CSS variables only
- Use any icon library other than Lucide React

## Tailwind Version Check (REQUIRED before styling)
- v3: `tailwind.config.ts` present — use standard config
- v4: `@theme inline` block in `globals.css` — add design_system.md colors as CSS variables in @theme block

## Role-based rendering
```typescript
// CORRECT — check role before rendering
if (user.role === 'admin') return <AdminPanel />

// WRONG — hidden but accessible in DOM
<AdminPanel className="hidden" />
```

```

Verify:
```bash
ls -la .claude/rules/ui-standards.md
head -5 .claude/rules/ui-standards.md
```


---

## STEP 5 — Harden settings.json: DDL protection + schema drift hook

PROBLEM 1: DDL operations (DROP, ALTER, TRUNCATE via psql) are not in the ask array.
Claude can silently alter DB schema without confirmation.

PROBLEM 2: Rule \#3 ("update schema.sql in same commit") is advisory only.
A hook on git commit makes it deterministic.

In .claude/settings.json make these TWO changes:

CHANGE 1 — Add to the existing "ask" array:

```json
"Bash(psql * DROP *)",
"Bash(psql * ALTER *)",
"Bash(psql * TRUNCATE *)",
"Bash(psql * DELETE FROM *)"
```

CHANGE 2 — Add a second entry to the existing "PostToolUse" hooks array:

```json
{
  "matcher": "Bash(git commit*)",
  "hooks": [{
    "type": "command",
    "command": "bash -c 'CHANGED=$(git diff --cached --name-only 2>/dev/null); if echo \"$CHANGED\" | grep -qE \"\\.(sql|py)$\" && ! echo \"$CHANGED\" | grep -q \"schema.sql\"; then echo \"\\n⚠️  WARNING: SQL/Python files staged but sql/schema.sql NOT staged.\"; echo \"Run /schema-change workflow before committing DB changes.\"; fi'",
    "timeout": 5,
    "statusMessage": "Checking schema.sql drift..."
  }]
}
```

Verify:

```bash
python3 -c "import json; json.load(open('.claude/settings.json')); print('✅ Valid JSON')"
```


---

## STEP 6 — Add plansDirectory and env settings to settings.json

PROBLEM: Plans save to ~/.claude/plans — outside repo, not in git, lost between workstations.
MCP tools (pgedge, context7, perplexity) load ALL their tools at session start — wastes context.

In .claude/settings.json add these top-level fields (merge with existing, do not replace):

```json
"plansDirectory": "./docs/plans",
"autoUpdatesChannel": "stable",
"cleanupPeriodDays": 14,
"language": "russian",
"attribution": {
  "commit": "Co-Authored-By: Claude <noreply@anthropic.com>",
  "pr": ""
}
```

Add or merge "env" block:

```json
"env": {
  "ENABLE_TOOL_SEARCH": "auto:5",
  "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "80",
  "MAX_MCP_OUTPUT_TOKENS": "30000",
  "CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-4-20250514"
}
```

Explanation:

- plansDirectory → plans saved in repo under docs/plans/, reviewable by team
- language:russian → no need to type "отвечай на русском" every session (code still in English per CRITICAL RULES)
- ENABLE_TOOL_SEARCH auto:5 → lazy-load MCP tools, saves ~50-80k context tokens at startup
- CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 80 → compact at 80% not 90% → less context lost per compaction
- MAX_MCP_OUTPUT_TOKENS 30000 → prevent pgedge large query responses from flooding context window
- CLAUDE_CODE_SUBAGENT_MODEL → subagents use Sonnet (cheaper), main session stays on Opus

Create the plans directory:

```bash
mkdir -p docs/plans
echo "# Plans\nClaude Code plan files — auto-generated during planning sessions" > docs/plans/README.md
```

Add to .gitignore:

```
# Claude Code plans (auto-generated)
docs/plans/*.md
!docs/plans/README.md
```

Verify:

```bash
python3 -c "
import json
s = json.load(open('.claude/settings.json'))
print('plansDirectory:', s.get('plansDirectory'))
print('language:', s.get('language'))
print('env:', json.dumps(s.get('env', {}), indent=2))
"
```


---

## STEP 7 — Add PreCompact hook to preserve EDW critical context

PROBLEM: When Claude auto-compacts, it loses: current task goal, modified files list,
DB state, pending SCD2/FK decisions. The PreCompact hook injects a reminder before summary.

Add "PreCompact" to the "hooks" section in .claude/settings.json:

```json
"PreCompact": [{
  "hooks": [{
    "type": "command",
    "command": "echo 'CRITICAL — PRESERVE IN COMPACTION SUMMARY: (1) current task goal in one sentence, (2) exact list of all files modified this session, (3) schema.sql status — changed or not, (4) hash formula in use, (5) sync_status values involved, (6) unresolved FK/SCD2 decisions, (7) last pgedge query result if relevant, (8) exact next step after context reset'",
    "timeout": 3,
    "statusMessage": "Preparing EDW context for compaction..."
  }]
}]
```

Verify hooks list:

```bash
python3 -c "
import json
s = json.load(open('.claude/settings.json'))
print('Hook events:', list(s.get('hooks', {}).keys()))
"
```

Should show: PostToolUse, SessionStart, PreCompact

---

## STEP 8 — Create /compact-edw slash command

PROBLEM: When context compacts mid-task, critical EDW state (DB changes, SCD2 state,
pending decisions) is lost. A dedicated command forces structured preservation.

Create file .claude/commands/compact-edw.md with this exact content:

```markdown
Compact context while preserving EDW-critical state.

Before compacting, produce a structured snapshot:

1. **Current task** — one sentence: what were we doing?
2. **Modified files** — list every file edited this session (exact paths)
3. **DB state** — schema changes made, tables affected, schema.sql updated? (yes/no)
4. **SCD2 state** — hash formula confirmed in use, which sync_status values were involved
5. **Pending decisions** — unresolved questions, TODOs, FK misses discovered
6. **Blockers** — anything that was failing or unclear
7. **Next step** — the EXACT first action to take after context reset

Save snapshot to docs/plans/session-snapshot.md (overwrite each time).
Then run /compact using this snapshot as the compaction instruction.
```

Verify:

```bash
ls .claude/commands/compact-edw.md && cat .claude/commands/compact-edw.md | wc -l
```


---

## STEP 9 — Create /spec slash command (safe planning without Plan Mode bug)

PROBLEM: Plan Mode has a known bug — pressing "Yes" to confirm a plan triggers auto-accept mode,
causing Claude to make file edits without further confirmation.
A /spec command implements the same plan-before-execute workflow via files, avoiding the bug entirely.

Create file .claude/commands/spec.md with this exact content:

```markdown
***
disable-model-invocation: true
***
Enter safe specification mode for task: $ARGUMENTS

## Phase 1 — Explore (READ ONLY — make ZERO file changes in this phase)
1. Read all files relevant to the task using Read, Grep, Glob tools
2. If task involves schema: query pgedge MCP to get current DB state
3. If anything is ambiguous: use AskUserQuestion tool to ask me — do NOT assume
4. Do NOT create files, do NOT edit files, do NOT run Bash write commands

## Phase 2 — Design
1. Write implementation plan to docs/plans/spec-$ARGUMENTS.md
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
```

Verify:

```bash
ls .claude/commands/spec.md && head -5 .claude/commands/spec.md
```


---

## STEP 10 — Create etl-reviewer subagent

PROBLEM: After writing ETL code, Claude reviews its own output — bias toward approving it.
A dedicated subagent reviews from a clean context with no memory of writing the code.

Create file .claude/agents/etl-reviewer.md with this exact content:

```markdown
***
name: etl-reviewer
description: Reviews ETL Python code for SCD2 correctness, FK safety, audit completeness, schema safety
tools: Read, Grep, Glob
model: claude-opus-4-20250514
***
You are a senior data engineer performing a code review for EDW Jackdaw.
You have NO memory of writing this code. Review it purely on its merits.

Review the file(s) specified in the task. Check each category below.
Report ✅ PASS or ❌ FAIL for each, with line numbers and suggested fixes for every failure.

***

## Category 1: SCD2 Correctness
- [ ] Hash formula is exactly: `hashlib.md5("|".join(str(v) for v in row.values).encode()).hexdigest()`
- [ ] DB write happens ONLY when new_hash != existing_hash (no unconditional upserts)
- [ ] tag_history INSERT happens for EVERY update with old_value JSONB + new_value JSONB
- [ ] sync_status uses ONLY these 4 values: New | Updated | No Changes | Deleted
- [ ] Hierarchy resolution (parent_tag_id) runs AFTER main tag sync — separate Prefect task, same flow
- [ ] Lookup caches loaded ONCE before row loop (no SELECT inside the loop — N+1 prevention)

## Category 2: FK Safety
- [ ] All FK lookups use `.get()` — never direct dict[key] that raises KeyError on miss
- [ ] FK miss → stores NULL in the FK column, does NOT raise exception
- [ ] Raw source value preserved in `_raw_*` column on every FK miss
- [ ] Warning logged (`logger.warning(...)`) for every FK miss

## Category 3: Audit Completeness
- [ ] Every INSERT/UPDATE writes to `audit_core.log_entry`
- [ ] log_entry includes: operation, table_name, rows_affected, success, error_message, created_at
- [ ] No bare `except: pass` or `except Exception: pass` without logging
- [ ] No `print()` statements — only `get_run_logger()` from Prefect

## Category 4: Schema Safety
- [ ] Every table reference is schema-prefixed: project_core., audit_core., ontology_core., reference_core., mapping.
- [ ] No `DELETE FROM project_core.*` (soft deletes only: object_status = 'Inactive')
- [ ] No invented column names — all columns must exist in sql/schema.sql
- [ ] No string concatenation for SQL — only bound parameters (:param style)

## Category 5: Pandas Safety
- [ ] All `read_csv` / `read_excel` calls use `dtype=str, na_filter=False`
- [ ] NaT and None values converted before DB insert (not inserted as string 'NaT')
- [ ] `clean_string()` used for all raw source values before lookup/insert

## Category 6: Async Correctness
- [ ] No blocking calls inside async functions (no time.sleep, no sync DB calls)
- [ ] SQLAlchemy DML uses `engine.begin()` context manager (atomic)
- [ ] SQLAlchemy reads use `engine.connect()` context manager
- [ ] Type hints present on all functions

***
Output format:
For each category: ✅ PASS (all checks pass) or ❌ FAIL with:
- Exact line number
- What rule is violated
- Suggested fix (code snippet preferred)
```

Verify:

```bash
ls .claude/agents/etl-reviewer.md && wc -l .claude/agents/etl-reviewer.md
```


---

## STEP 11 — Final verification (run all checks, report every result)

```bash
echo "========================================="
echo "1. CLAUDE.md line count (target: <80)"
wc -l CLAUDE.md

echo "========================================="
echo "2. No code blocks in CLAUDE.md"
grep -n "json.dumps\|hashlib\|md5\|async def\|pd.read_csv\|@flow\|@task" CLAUDE.md \
  && echo "❌ Code still in CLAUDE.md" || echo "✅ No code blocks"

echo "========================================="
echo "3. No broken UI section in CLAUDE.md"
grep -n "shadcn\|TanStack\|2\.7 .gitignore" CLAUDE.md \
  && echo "❌ Broken sections remain" || echo "✅ Cleaned"

echo "========================================="
echo "4. Context on Demand table exists"
grep -c "Context on Demand" CLAUDE.md

echo "========================================="
echo "5. etl-reviewer trigger in CLAUDE.md"
grep "etl-reviewer" CLAUDE.md && echo "✅ Found" || echo "❌ Missing"

echo "========================================="
echo "6. Hash formula in scd2-rules skill"
grep "Hash:" .claude/skills/scd2-rules/skill.md

echo "========================================="
echo "7. Status values in scd2-rules (must show No Changes)"
grep "Status values" .claude/skills/scd2-rules/skill.md

echo "========================================="
echo "8. TIMESTAMP fix in sql-standards"
grep "Timestamps" .claude/rules/sql-standards.md

echo "========================================="
echo "9. All rule files"
ls -la .claude/rules/

echo "========================================="
echo "10. All skill directories"
ls -la .claude/skills/

echo "========================================="
echo "11. All agents"
ls -la .claude/agents/

echo "========================================="
echo "12. All commands"
ls -la .claude/commands/

echo "========================================="
echo "13. settings.json full validation"
python3 -c "
import json, sys
try:
    s = json.load(open('.claude/settings.json'))
    print('✅ Valid JSON')
    ask = s.get('permissions', {}).get('ask', [])
    ddl = [x for x in ask if 'DROP' in x or 'ALTER' in x]
    hooks = list(s.get('hooks', {}).keys())
    env = s.get('env', {})
    print(f'DDL protection: {len(ddl)} entries → {ddl}')
    print(f'Hook events: {hooks}')
    print(f'plansDirectory: {s.get(\"plansDirectory\")}')
    print(f'language: {s.get(\"language\")}')
    print(f'ENABLE_TOOL_SEARCH: {env.get(\"ENABLE_TOOL_SEARCH\")}')
    print(f'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: {env.get(\"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE\")}')
    print(f'MAX_MCP_OUTPUT_TOKENS: {env.get(\"MAX_MCP_OUTPUT_TOKENS\")}')
except json.JSONDecodeError as e:
    print(f'❌ JSON Error: {e}')
    sys.exit(1)
"

echo "========================================="
echo "14. plans directory"
ls -la docs/plans/

echo "========================================="
echo "15. .gitignore has plans entry"
grep "plans" .gitignore && echo "✅ Found" || echo "❌ Missing"
```


---

## STEP 12 — Commit all changes

```bash
git add CLAUDE.md \
        .claude/settings.json \
        .claude/rules/ \
        .claude/skills/ \
        .claude/agents/ \
        .claude/commands/ \
        docs/plans/ \
        .gitignore

git status
git diff --cached --stat
git commit -m "[claude-config] full audit: dedup CLAUDE.md, fix hash/TIMESTAMP conflicts, DDL hooks, /spec, /compact-edw, etl-reviewer, plansDirectory, ENABLE_TOOL_SEARCH"
```


---

## COMPLETE CONSTRAINTS — read before starting any step

- Do NOT run /init or regenerate CLAUDE.md from scratch
- Do NOT add AI-generated intro paragraphs ("This is an EDW project that...")
- Do NOT copy content from .claude/rules/ back into CLAUDE.md
- Do NOT modify .claude/agents/schema-validator.md — it is already correct
- Do NOT modify .claude/commands/new-source.md, schema-change.md, sync-debug.md, new-ui-page.md — they are correct
- MERGE new fields into settings.json — do NOT replace the entire file
- Each step must complete and be verified before moving to the next
- If a step finds the feature already correctly in place: report ✅ ALREADY CORRECT and skip


## WHAT THIS ACHIEVES (for reference)

After all 12 steps complete:

1. CLAUDE.md < 80 lines — stops context bloat every session (~80-120k tokens saved)
2. Hash formula unified — eliminates data integrity risk from diverging SCD2 implementations
3. TIMESTAMPTZ consistent — no more timezone-naive timestamps in production schema
4. ui-standards.md rule — UI context loads only when needed (not every session)
5. DDL protection — DROP/ALTER/TRUNCATE require explicit confirmation
6. schema.sql drift hook — fires warning on git commit when DB files change without schema.sql
7. plansDirectory — plans tracked in git, reviewable, not lost between workstations
8. ENABLE_TOOL_SEARCH — lazy MCP tool loading saves ~50-80k tokens at session startup
9. CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 80 — compacts earlier, loses less context per compaction
10. PreCompact hook — structured EDW state preserved before every compaction
11. /compact-edw command — on-demand structured snapshot with DB/SCD2 state
12. /spec command — safe plan-before-execute without Plan Mode auto-accept bug
13. etl-reviewer subagent — unbiased ETL code review from fresh context after every implementation
14. language:russian — eliminates need to write "отвечай на русском" every session
```
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: khorosho-teper-proanalizirui-luchshie-praktiki-po-et.md
[^2]: dai-tekst-prompta-priamo-v-chate-s-podrobnym-ukazani-2.md
[^3]: CLAUDE.md
[^4]: CLAUDE-1.md
[^5]: image.jpg
[^6]: README-1.md
[^7]: CLAUDE-2-2.md
[^8]: README-1.md
[^9]: CLAUDE.md
[^10]: CLAUDE.md
[^11]: schema-change-3.md
[^12]: new-source-2.md
[^13]: sync-debug-4.md
[^14]: schema-validator-5.md
[^15]: skill-6.md
[^16]: skill-7.md
[^17]: skill-8.md```

