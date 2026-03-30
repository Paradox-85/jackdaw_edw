***
disable-model-invocation: true
***
Enter safe specification mode for task: $ARGUMENTS

## Phase1 — Explore (READ ONLY — make ZERO file changes in this phase)
1. Read all files relevant to the task using Read, Grep, Glob tools
2. If task involves schema: query pgedge MCP to get current DB state
3. If anything is ambiguous: use AskUserQuestion tool to ask me — do NOT assume
4. Do NOT create files, do NOT edit files, do NOT run Bash write commands

## Phase2 — Design
1. Write implementation plan to docs/plans/spec-$ARGUMENTS.md
2. Plan must contain ALL of these sections:
   - **Problem** (1-2 sentences)
   - **Files to modify** (exact paths, what changes in each)
   - **Files to create** (exact paths, what goes in each)
   - **SQL changes** (if any) — does schema.sql need updating? yes/no
   - **Implementation order** (numbered steps)
   - **Risks and edge cases**
   - **Verification** (how to confirm that the change worked)
3. Show me: complete plan
4. WAIT for me to type exactly "proceed" — do not start implementation until then

## Phase3 — Implement (ONLY after I type "proceed")
1. Execute the plan step by step
2. After each file change: report what changed and why
3. If any DB objects modified: run /schema-change
4. After any ETL file modified: run etl-reviewer subagent
5. Run verification steps from the plan
