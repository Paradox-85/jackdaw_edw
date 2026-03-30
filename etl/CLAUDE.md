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
