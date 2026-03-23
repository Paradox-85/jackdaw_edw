---
name: ui-react
description: React/Next.js UI patterns for Jackdaw EDW
license: project-internal
---

## Always
- Read @docs/design_system.md before any UI work
- Check @docs/ui-references/ for visual references
- Use shadcn/ui from @/components/ui/ — never build primitives from scratch
- All colors: CSS variables only — never inline hex
- All data: React Query v5 (staleTime: 60_000, gcTime: 300_000, retry: 1)
- TanStack Table v8 for all lists > 100 rows (server-side)
- Lucide React for all icons — no emoji

## Page structure (every page)
1. Page header: title (text-xl font-semibold) + caption (text-xs text-muted) + actions
2. Section dividers: 10px uppercase #8B949E + bottom border #21262D
3. Content area
4. AuthGuard wraps everything

## TanStack Table v8 (not v7)
Use: useReactTable(), getCoreRowModel(), getPaginationRowModel()
NOT: table.setPageSize() — that is v7 API

## Loading / empty states
Loading: <Skeleton> rows (not spinner)
Empty: centered ghost icon + "No records found"

## Sheet (slide-over) for row detail
Width: 600px, from right
Contains tabs: General | Documents | Properties
Data fetched on open (not preloaded)