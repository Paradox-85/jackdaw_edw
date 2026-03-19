# Jackdaw EDW — User Guide

> **Engineering Data Warehouse** for the JDA (Jackdaw) project.
> This system manages tag registers, document cross-references, validation, and EIS exports.

---

## Overview

Jackdaw EDW is the central data management platform for engineering data on the JDA project.
It ingests source EIS Excel files, stores structured data in PostgreSQL, and generates
validated EIS-compliant CSV export files.

**Key capabilities:**
- Tag register management (SCD Type 2 change tracking)
- Document cross-reference management (MDR integration)
- Data quality validation with configurable rules
- Automated EIS export generation (9 register types)
- AI-assisted data quality review (Ollama LLM) — Phase 3

---

## Navigation

| Page | Available to | Description |
|---|---|---|
| Home | All users | Dashboard with KPIs, sync status, service health, tag analytics, recent flow runs |
| Tag Register | All users | Master tag list with filtering, grouping, XLSX export, property and document panels |
| Reports | All users | Pre-built SQL reports with CSV/XLSX export |
| Tag History | All users | SCD audit trail — tag change history with Name Changed detection |
| Validation | All users | Data quality violations grouped by rule and tier |
| EIS Export | Admin only | Generate EIS data packages with revision control |
| Help | All users | This page |
| Feedback | All users | Submit bug reports and enhancement requests |

> **Quick access:** Use the ❓ and 💬 buttons in the top-right corner to jump directly to Help or Feedback from any page.

---

## Pages Detail

### 🏠 Home
Dashboard showing:
- **Active Tags** — total tags with `object_status = 'Active'`
- **Documents** — total documents in MDR
- **Last Sync** — timestamp of most recent ETL run
- **Open Violations** — unresolved validation issues (last 7 days)
- **Service Health** — PostgreSQL, Prefect, Ollama connectivity
- **Recent Flow Runs** — last 10 Prefect flow executions
- **Tag Analytics** — breakdown by Tag Status, Design Company, Sync Status
- **Tag Growth Timeline** — historical chart of New / Updated / Deleted tags
- **Tag Name Changes** — alerts for tags whose names changed in the last 30 days

**Admin-only sections:**
- **Quick Sync** — trigger `sequential-master-sync` flow or view last 5 sync runs
- **Download docker-compose.yml** — download current infrastructure config

### 🗂 Tag Register
Master tag list. Loads automatically on open.

- **Filter** — text search across all columns simultaneously
- **Group By** — sort by any column (Area, Class, Tag Status, etc.)
- **XLSX Export** — download filtered view as Excel
- **Row Selection** — click any row to open detail panels:
  - **Property Values** — Functional / Physical / Functional Physical properties
  - **Connected Documents** — MDR documents linked to this tag (mdr_flag=true)

### 📊 Reports
Built-in SQL reports for data analysis:

| Report | Description |
|--------|-------------|
| **Tag Register** | Full active tag list with all attributes |
| **Tag–Document Mapping** | Cross-reference between tags and MDR documents |
| **SCD Change Delta** | Tag changes since last sync (New / Updated / Deleted) |
| **Validation Summary** | Data quality violations grouped by rule |

**How to use:**
1. Select a report from the list
2. Fill in any filter parameters (date, tag name, etc.)
3. Click **▶ Generate**
4. Download as CSV or XLSX using the export buttons

### 📋 Tag History
SCD Type 2 audit trail — every change to every tag since system inception.

- **Timeline chart** — bar chart of activity by date and sync status
- Filter by date range, tag name, or change type
- **Name Changed** column — flags rows where the tag name has changed (highlighted red)
- Export filtered results to XLSX
- **Tag Drill-Down** — enter exact tag name to see full chronological history with JSONB snapshots

### ✅ Validation
Data quality monitoring:

- **Summary** — violation counts by severity (Critical / Warning / Info)
- **By Tier** — L0 (Foundation) through L4 (Semantics)
- **Session History** — results from previous full-scan runs
- **Rule Catalogue** — all 69+ active validation rules with descriptions

---

## EIS Export (Admin)

### Supported Export Types

| Seq | Name | Description |
|-----|------|-------------|
| 003 | Tag Register | Full active tag list (primary EIS output) |
| 004 | Equipment Register | Equipment assets linked to tags |
| 010 | Tag Property Values | EAV properties (Functional concept) |
| 011 | Equipment Property Values | EAV properties (Physical concept) |
| 203 | Area Register | Spatial hierarchy |
| 204 | Process Unit Register | Process unit breakdown |
| 214 | Purchase Order Register | PO master list |
| 209 | Model Part Register | Component catalog |
| 307 | Tag Class Properties | CFIHOS ontology schema |

### Revision Naming
Revision codes must follow the pattern `^[A-Z]\d{2}$`:
- Valid: `A35`, `B01`, `C12`
- Invalid: `a35`, `AB1`, `35A`

### Export Modes
- **Server-side (Prefect flow)** — triggers full pipeline with validation, logging, and file storage on server
- **Direct download** — generates CSV in browser without Prefect (no server-side audit log)

---

## Tag Status Color Coding

| Status | Color | Meaning |
|--------|-------|---------|
| ACTIVE | 🔵 Blue | Tag is active in the register |
| VOID | 🔴 Red | Tag has been voided |
| FUTURE | ⚫ Gray | Planned tag, not yet active |
| ASB, AFC | 🟢 Green | Other active statuses |

---

## Sync / ETL

Data is synchronized automatically via Prefect flows. Admin users can trigger a manual sync
from the **Home** page → **Quick Sync** section.

### Flow Execution Order (sequential-master-sync)
1. Seed reference data (ontology, areas, companies, POs)
2. Sync document data (MDR)
3. Sync tag data (SCD2 UPSERT)
4. Resolve tag hierarchy (parent_tag_id second pass)
5. Sync property values

Run history is visible in **Home → Last Sync Run Statistics** and in Prefect UI.

---

## FAQ

**Q: Why does the tag count show fewer rows than the source EIS file?**
A: The system only counts `object_status = 'Active'` tags. Void, deleted, and inactive tags are excluded from counts but remain in the database.

**Q: Why is a validation violation showing for tags I've already fixed?**
A: Validation results are stored per-session. Re-run a full validation scan to update results.

**Q: The Reports page shows "No rows" — is the data missing?**
A: Check that migrations 001–009 have been applied and that the `edw_viewer` database role has been created. Contact your admin if the issue persists.

**Q: How do I trigger a manual sync?**
A: Admin users can use the **▶ Sync Tag Data** button on the Home page. The sync is dispatched as a Prefect flow run and can be monitored in the Recent Flow Runs section or in Prefect UI.

**Q: How do I add a new user?**
A: Run the following SQL as `postgres_admin`:
```sql
INSERT INTO app_core.ui_user (username, password_hash, role)
VALUES (
    'newuser',
    -- Generate hash: python -c "import bcrypt; print(bcrypt.hashpw(b'password', bcrypt.gensalt(12)).decode())"
    '<BCRYPT_HASH>',
    'viewer'  -- or 'admin'
);
```

**Q: How do I change my password?**
A: Currently requires admin SQL access. Self-service password change is planned for Phase 2.

---

## Support

Use the **💬 Feedback** page to submit bug reports, enhancement requests, or questions.

For urgent issues, check:
- Prefect UI: [https://pve.prefect.adzv-pt.dev](https://pve.prefect.adzv-pt.dev)
- DbGate: [https://pve.dbgate.adzv-pt.dev](https://pve.dbgate.adzv-pt.dev)
