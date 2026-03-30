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
- Inconsistent heading structure (some use ##, others ###)
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
```

Report: docs updated, broken links fixed, duplicates removed.
