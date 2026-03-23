# Jackdaw EDW Design System

## Colors (exact hex — no deviations)
Background:        #0D1117
Surface / Card:    #161B22
Border:            #21262D
Border subtle:     #30363D
Text primary:      #E6EDF3
Text secondary:    #8B949E
Text muted:        #484F58

## Badge colors (exact mapping from common.py)
badge-success:     #3FB950   (Active, New, Completed)
badge-warning:     #D29922   (Reduced, Scheduled, Warning)
badge-danger:      #F85149   (Deleted, Failed, Critical)
badge-blue:        #1976D2   (Updated, Running, Info)
badge-muted:       #8B949E   (No Changes, Cancelled)

## Button / Interactive accent
Primary button:    #1976D2   (MUI Blue)
Link / Code text:  #58A6FF   (NOT used in badges)

## Typography
Font family:  Inter, system-ui, sans-serif
Body:         14px / line-height 1.5
Caption:      11px / uppercase / letter-spacing 0.06em / color #8B949E
Code / Hash:  12px / 'SF Mono', 'Fira Code', monospace / color #58A6FF

## Spacing (8px grid)
xs:4px  sm:8px  md:16px  lg:24px  xl:32px

## Sidebar
Width: 240px (collapsed: 56px)
Background: #0D1117
Nav item height: 36px
Active: background #161B22, left border 2px #1976D2

## Table (data-dense)
Row height: 36px
Header: 11px uppercase #8B949E, background #0D1117
Cell padding: 8px 12px
Hover row: background #161B22
Border: 1px solid #21262D

## Badge
height: 20px / padding: 2px 8px / border-radius: 10px / font: 11px weight 500

## Card
Background: #161B22 / Border: 1px solid #21262D / Border-radius: 6px / Padding: 16px

## Section Header
Font: 10px uppercase weight 600 / color #8B949E / border-bottom: 1px solid #21262D

## RBAC Display Rules
Viewer CANNOT see:
  - EIS Export, ETL Import triggers
  - Admin Links (DbGate, Portainer, Prefect direct)
  - Tech stack labels, Docker-compose download

Admin additionally sees:
  - ETL Import, EIS Export, Services pages
  - Detailed sync statistics per run

## Prohibited
- Emoji icons (Lucide React only)
- Purple / pink / orange gradients
- border-radius > 8px
- font-size < 11px
- Horizontal scroll on 1280px viewport
- Inline hex values (use CSS variables)
- #58A6FF in badge components