---
description: UI standards — Next.js 15, React, TanStack Table v8, shadcn/ui, Tailwind CSS
---
# UI/UX Standards (React Frontend)

## Stack
Framework: Next.js 15 App Router + TypeScript + shadcn/ui + Tailwind CSS
Tables: TanStack Table v8 — `useReactTable()` API, server-side pagination
Data: React Query v5 — `staleTime:60_000, gcTime:300_000, retry:1`
Icons: Lucide React only

## Always
- Read `@docs/design_system.md` before any UI work
- Use `/new-ui-page` command for new pages
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
