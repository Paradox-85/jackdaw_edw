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
