# Jackdaw EDW Control Center — Architecture Decisions & Roadmap

## Context

Internal engineering tool for the Jackdaw offshore project (Plant JDA).
Audience: project data team (~5 people). Not a public-facing product.
Deployed: `jackdaw.adzv-pt.dev` via Caddy reverse proxy, PVE LXC 200.

---

## Accepted feedback from architect review (March 2026)

| # | Issue | Decision |
|---|---|---|
| 1 | `postgres_admin` used for all queries | ✅ Fixed: `edw_viewer` read-only role for viewer queries. Admin URL only for flow triggers. |
| 2 | No role separation in UI | ✅ Fixed: Viewer/Admin modes. Admin unlocked by password. Admin pages: ETL Import, EIS Export, Services. |
| 3 | Infra links (DbGate, Portainer) visible to all | ✅ Fixed: Infra links shown only in admin mode. |
| 4 | WIP features shown as fully functional | ✅ Fixed: Validation flows, CRS show `🚧 Under Construction`. |
| 5 | No dynamic report catalogue | ✅ Addressed: `audit_core.report_metadata` created by migration_006. 11 seed reports. |

## Rejected feedback (intentional design decisions)

| # | Issue | Rationale |
|---|---|---|
| 1 | "Streamlit wrong for EDW product" | Internal tool for ~5 engineers. Streamlit is correct choice for v1. |
| 2 | "Need 3-layer backend API" | Overengineering for a single-developer internal tool. Revisit at Phase 3. |
| 3 | "LLM chat dangerous without semantic layer" | Ollama is local, no internet. System prompt explicitly forbids SQL generation. |

---

## Current state — what is implemented in the repo

| Component | Status | Prefect deployment |
|---|---|---|
| Master sync flow | ✅ Live | `sequential-master-sync` |
| Tag register export | ✅ Live | `export-tag-register` |
| Equipment register export | ✅ Live | `export-equipment-register` |
| `audit_core.sync_run_stats` | ✅ Live | — |
| `audit_core.tag_status_history` | ✅ Live | — |
| `audit_core.validation_result` | ✅ Live | — |
| `audit_core.export_validation_rule` (69 rules) | ✅ Live | — |
| `audit_core.report_metadata` | 🔧 Migration_006 needed | — |
| `edw_viewer` DB role | 🔧 Migration_006 needed | — |
| Standalone sync-tag / sync-doc deployments | 🚧 Planned | `sync-tag-data` etc. |
| Validation flow deployments | 🚧 Planned | `validation-full-scan` etc. |
| CRS Assistant | 📋 Phase 2 | — |

---

## Phase roadmap

### Phase 1 — Current (v2)
**Goal:** Admin can trigger import/export. All users see reports and statistics.

- [x] Reports page: 4 master reports + dynamic catalogue from DB
- [x] Tag History viewer
- [x] Validation stats from `audit_core.validation_result`
- [x] ETL Import trigger (admin, `sequential-master-sync`)
- [x] EIS Export trigger (admin, `export-tag-register` + `export-equipment-register`)
- [x] `edw_viewer` read-only role
- [x] `audit_core.report_metadata` with 11 seed reports
- [ ] Run migration_006 on production DB

### Phase 2 — Next
**Goal:** More self-service for project team.

- [ ] Standalone flow deployments for sync-tag, sync-doc, seed-reference
- [ ] Validation flow deployments (`validation-full-scan`, `validation-basic-scan`)
- [ ] CRS Assistant (Ollama + XLSX export)
- [ ] Tag data viewer (tabular UI for `project_core.tag` with filters)
- [ ] Expand `report_metadata` catalogue (target: 30+ reports)

### Phase 3 — Future
**Goal:** Broader team access, basic governance.

- [ ] Replace password admin gate with OIDC/SSO (Authentik or Keycloak)
- [ ] Proper RBAC: `report_viewer` / `data_operator` / `platform_admin`
- [ ] Persistent audit log: who accessed which report, how many rows
- [ ] NL-to-DB chat: intent classification → template query (NOT raw SQL from LLM)
- [ ] Backend capability registry (replace hardcoded deployment names)
- [ ] Consider FastAPI thin backend if team grows beyond 10 users

---

## DB role policy

```
postgres_admin   — ETL flows, migrations, admin triggers (NOT exposed to browser)
edw_viewer       — SELECT only on project_core, reference_core, ontology_core,
                   mapping, audit_core. Used by Streamlit viewer queries.
```

**Rule:** The `DATABASE_URL` (admin) is used ONLY in `ui/common.py` for:
- `db_read(..., admin=True)` calls in admin-only pages (etl_import stats)
- Nothing else

All report queries, tag history, validation stats → `edw_viewer` via `DATABASE_VIEWER_URL`.

---

## Known tech debt

1. **Deployment name coupling** — Prefect deployment names are hardcoded strings.
   Fix in Phase 3: store in `audit_core.deployment_registry` with health checks.

2. **Admin password in env var** — Simple but not auditable.
   Fix in Phase 3: replace with OIDC tokens.

3. **No persistent audit of user actions** — `st.session_state` log is ephemeral.
   Fix in Phase 3: write to `audit_core.ui_action_log`.
