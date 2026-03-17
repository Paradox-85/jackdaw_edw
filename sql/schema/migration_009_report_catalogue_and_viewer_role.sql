/*
migration_009_report_catalogue_and_viewer_role.sql

Purpose:
  1. Create audit_core.report_metadata — dynamic SQL report catalogue
     consumed by the EDW Control Center UI.
  2. Create edw_viewer PostgreSQL role — read-only access to
     project_core, reference_core, ontology_core, mapping, audit_core.
     Used by jackdaw-ui container in viewer mode.

Safety:
  All DDL uses IF NOT EXISTS / DO $$ guards — safe to re-run.

Changes:
  2026-03-17 — Initial implementation.
*/

-- =============================================================================
-- PART 1: audit_core.report_metadata
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_core.report_metadata (
    id            UUID      NOT NULL DEFAULT gen_random_uuid(),
    report_name   TEXT      NOT NULL,
    category      TEXT      NOT NULL DEFAULT 'General',
    description   TEXT      NULL,
    sql_query     TEXT      NOT NULL,
    author        TEXT      NULL      DEFAULT 'system',
    is_parametric BOOLEAN   NOT NULL  DEFAULT false,
    is_active     BOOLEAN   NOT NULL  DEFAULT true,
    created_at    TIMESTAMP NOT NULL  DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL  DEFAULT now(),
    CONSTRAINT report_metadata_pkey     PRIMARY KEY (id),
    CONSTRAINT report_metadata_name_key UNIQUE (report_name)
);

COMMENT ON TABLE audit_core.report_metadata IS
    'Dynamic SQL report catalogue. Each row is a named, categorised, '
    'on-demand SQL query executed by the EDW Control Center. '
    'Parametric reports use :placeholder syntax in sql_query.';

COMMENT ON COLUMN audit_core.report_metadata.is_parametric IS
    'True if sql_query contains :param placeholders. '
    'UI will render input widgets before execution.';

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION audit_core.set_report_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_report_metadata_updated_at ON audit_core.report_metadata;
CREATE TRIGGER trg_report_metadata_updated_at
    BEFORE UPDATE ON audit_core.report_metadata
    FOR EACH ROW EXECUTE FUNCTION audit_core.set_report_updated_at();

-- =============================================================================
-- PART 2: Seed initial reports
-- =============================================================================

INSERT INTO audit_core.report_metadata
    (report_name, category, description, sql_query, author, is_parametric)
VALUES

-- ── Master Data ──────────────────────────────────────────────────────────────
(
    'Tags by Discipline',
    'Master Data',
    'Count of active tags grouped by discipline code',
    $SQL$
    SELECT
        COALESCE(d.code, '—') AS "Discipline",
        COALESCE(d.name, '—') AS "Discipline Name",
        COUNT(*)              AS "Tag Count"
    FROM   project_core.tag t
    LEFT JOIN reference_core.discipline d ON d.id = t.discipline_id
    WHERE  t.object_status = 'Active'
    GROUP  BY d.code, d.name
    ORDER  BY COUNT(*) DESC
    $SQL$,
    'system', false
),
(
    'Tags by Class',
    'Master Data',
    'Count of active tags grouped by CFIHOS class',
    $SQL$
    SELECT
        COALESCE(c.code, '—') AS "Class Code",
        COALESCE(c.name, '—') AS "Class Name",
        COUNT(*)              AS "Tag Count"
    FROM   project_core.tag t
    LEFT JOIN ontology_core.class c ON c.id = t.class_id
    WHERE  t.object_status = 'Active'
    GROUP  BY c.code, c.name
    ORDER  BY COUNT(*) DESC
    $SQL$,
    'system', false
),
(
    'Tags by Area',
    'Master Data',
    'Active tag count per area code',
    $SQL$
    SELECT
        COALESCE(a.code, '—') AS "Area",
        COALESCE(pl.code,'—') AS "Plant",
        COUNT(*)              AS "Tag Count"
    FROM   project_core.tag t
    LEFT JOIN reference_core.area  a  ON a.id  = t.area_id
    LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
    WHERE  t.object_status = 'Active'
    GROUP  BY a.code, pl.code
    ORDER  BY COUNT(*) DESC
    $SQL$,
    'system', false
),
(
    'Tags by Tag Status',
    'Master Data',
    'Active tags broken down by tag_status value',
    $SQL$
    SELECT
        COALESCE(tag_status, '—') AS "Tag Status",
        COUNT(*)                  AS "Count"
    FROM   project_core.tag
    WHERE  object_status = 'Active'
    GROUP  BY tag_status
    ORDER  BY COUNT(*) DESC
    $SQL$,
    'system', false
),

-- ── Documents ────────────────────────────────────────────────────────────────
(
    'Document Register',
    'Documents',
    'All active documents with revision and status',
    $SQL$
    SELECT
        doc.doc_number  AS "Doc Number",
        doc.title       AS "Title",
        doc.rev         AS "Rev",
        doc.status      AS "Status",
        doc.doc_type_code AS "Type",
        doc.rev_author  AS "Author",
        doc.rev_date    AS "Rev Date",
        COALESCE(c.name,'—') AS "Company"
    FROM   project_core.document doc
    LEFT JOIN reference_core.company c ON c.id = doc.company_id
    WHERE  doc.object_status = 'Active'
    ORDER  BY doc.doc_number
    $SQL$,
    'system', false
),
(
    'Documents without Tags',
    'Documents',
    'Active documents that have no tag mappings',
    $SQL$
    SELECT
        doc.doc_number AS "Doc Number",
        doc.title      AS "Title",
        doc.rev        AS "Rev",
        doc.status     AS "Status"
    FROM   project_core.document doc
    WHERE  doc.object_status = 'Active'
      AND  NOT EXISTS (
               SELECT 1 FROM mapping.tag_document m
               WHERE m.document_id = doc.id
                 AND m.mapping_status = 'Active'
           )
    ORDER  BY doc.doc_number
    $SQL$,
    'system', false
),

-- ── Quality ───────────────────────────────────────────────────────────────────
(
    'Tags without Class',
    'Data Quality',
    'Active tags where class_id is NULL — CFIHOS classification missing',
    $SQL$
    SELECT
        t.tag_name              AS "Tag Name",
        t.tag_status            AS "Tag Status",
        t.area_code_raw         AS "Area",
        t.discipline_code_raw   AS "Discipline",
        t.sync_status           AS "Sync Status"
    FROM   project_core.tag t
    WHERE  t.object_status = 'Active'
      AND  t.class_id IS NULL
    ORDER  BY t.tag_name
    $SQL$,
    'system', false
),
(
    'Tags without Area',
    'Data Quality',
    'Active tags where area_id is NULL',
    $SQL$
    SELECT
        t.tag_name            AS "Tag Name",
        t.tag_status          AS "Tag Status",
        t.area_code_raw       AS "Area Raw (unresolved)",
        t.discipline_code_raw AS "Discipline",
        t.sync_status         AS "Sync Status"
    FROM   project_core.tag t
    WHERE  t.object_status = 'Active'
      AND  t.area_id IS NULL
    ORDER  BY t.tag_name
    $SQL$,
    'system', false
),
(
    'Open Validation Violations (latest session)',
    'Data Quality',
    'Unresolved violations from the most recent validation run',
    $SQL$
    WITH latest AS (
        SELECT session_id FROM audit_core.validation_result
        ORDER BY run_time DESC LIMIT 1
    )
    SELECT
        COALESCE(vr.tier,'—')     AS "Tier",
        vr.severity               AS "Severity",
        vr.rule_code              AS "Rule",
        vr.object_name            AS "Object",
        vr.column_name            AS "Column",
        vr.violation_detail       AS "Detail"
    FROM   audit_core.validation_result vr
    JOIN   latest l ON l.session_id = vr.session_id
    WHERE  vr.is_resolved = false
    ORDER  BY vr.tier NULLS LAST, vr.severity, vr.rule_code
    $SQL$,
    'system', false
),

-- ── Audit ─────────────────────────────────────────────────────────────────────
(
    'Sync Run History',
    'Audit',
    'All import sync runs with row counts and durations',
    $SQL$
    SELECT
        run_id::text                                             AS "Run ID",
        target_table                                             AS "Table",
        TO_CHAR(start_time,'YYYY-MM-DD HH24:MI:SS')             AS "Started",
        ROUND(EXTRACT(EPOCH FROM (end_time - start_time)))::text||'s' AS "Duration",
        count_created   AS "New",
        count_updated   AS "Updated",
        count_unchanged AS "Unchanged",
        count_deleted   AS "Deleted",
        count_errors    AS "Errors"
    FROM   audit_core.sync_run_stats
    ORDER  BY start_time DESC
    LIMIT  100
    $SQL$,
    'system', false
),
(
    'Tag Change Timeline (parametric)',
    'Audit',
    'Tag changes between two dates. Provide :date_from and :date_to.',
    $SQL$
    SELECT
        TO_CHAR(h.sync_timestamp,'YYYY-MM-DD HH24:MI:SS') AS "Timestamp",
        h.sync_status   AS "Status",
        h.tag_name      AS "Tag Name",
        h.source_id     AS "Source ID"
    FROM   audit_core.tag_status_history h
    WHERE  h.sync_timestamp BETWEEN :date_from AND :date_to
      AND  h.sync_status != 'No Changes'
    ORDER  BY h.sync_timestamp DESC
    $SQL$,
    'system', true
)

ON CONFLICT (report_name) DO NOTHING;


-- =============================================================================
-- PART 3: edw_viewer — read-only PostgreSQL role
-- =============================================================================

DO $$
BEGIN
    -- Create role if not exists
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = 'edw_viewer'
    ) THEN
        CREATE ROLE edw_viewer LOGIN PASSWORD 'edw_viewer_change_me';
        RAISE NOTICE 'Role edw_viewer created. CHANGE the password immediately.';
    ELSE
        RAISE NOTICE 'Role edw_viewer already exists — skipping CREATE ROLE.';
    END IF;
END;
$$;

-- Grant CONNECT on database
GRANT CONNECT ON DATABASE engineering_core TO edw_viewer;

-- Grant USAGE on all relevant schemas
GRANT USAGE ON SCHEMA
    project_core,
    reference_core,
    ontology_core,
    mapping,
    audit_core
TO edw_viewer;

-- Grant SELECT on all current tables in those schemas
GRANT SELECT ON ALL TABLES IN SCHEMA
    project_core,
    reference_core,
    ontology_core,
    mapping,
    audit_core
TO edw_viewer;

-- Ensure SELECT applies to future tables too (ALTER DEFAULT PRIVILEGES)
ALTER DEFAULT PRIVILEGES IN SCHEMA project_core
    GRANT SELECT ON TABLES TO edw_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA reference_core
    GRANT SELECT ON TABLES TO edw_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA ontology_core
    GRANT SELECT ON TABLES TO edw_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA mapping
    GRANT SELECT ON TABLES TO edw_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit_core
    GRANT SELECT ON TABLES TO edw_viewer;

-- Explicitly DENY write access (belt-and-suspenders)
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA
    project_core,
    reference_core,
    ontology_core,
    mapping,
    audit_core
FROM edw_viewer;


-- =============================================================================
-- PART 4: Verification queries (run manually to confirm)
-- =============================================================================
/*
-- Check table created:
SELECT COUNT(*) FROM audit_core.report_metadata;

-- Check seed data:
SELECT report_name, category, is_parametric FROM audit_core.report_metadata ORDER BY category;

-- Check role permissions:
SELECT grantee, table_schema, table_name, privilege_type
FROM   information_schema.role_table_grants
WHERE  grantee = 'edw_viewer'
ORDER  BY table_schema, table_name;

-- Test viewer connection (run as edw_viewer):
-- psql -U edw_viewer -d engineering_core -c "SELECT COUNT(*) FROM project_core.tag;"
-- psql -U edw_viewer -d engineering_core -c "INSERT INTO project_core.tag (tag_name, source_id) VALUES ('X','X');"
-- ↑ must FAIL with permission denied
*/
