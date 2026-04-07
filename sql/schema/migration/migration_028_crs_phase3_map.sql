/*
Purpose: CRS Phase 3 — Add query_type to crs_validation_query + create crs_template_query_map.
         Separates GROUP (batch ANY(:tag_names)) from INDIVIDUAL (ad-hoc per comment) queries.
         Baseline populates mapping via category = query_code (both in CRS-C### format).
Context: migration_027_crs_phase3_seed.sql seeded 229 GROUP queries; all get DEFAULT 'GROUP'.
         crs_comment_validation (INDIVIDUAL path) is not modified.
Date:    2026-04-07
*/

-- ============================================================
-- Step 1a: Add query_type column to crs_validation_query
-- ============================================================

ALTER TABLE audit_core.crs_validation_query
    ADD COLUMN IF NOT EXISTS query_type TEXT NOT NULL DEFAULT 'GROUP'
    CONSTRAINT chk_crs_vq_query_type CHECK (query_type IN ('GROUP', 'INDIVIDUAL'));

-- All 229 existing rows get DEFAULT 'GROUP' automatically — no UPDATE needed.

CREATE INDEX IF NOT EXISTS idx_crs_vq_query_type
    ON audit_core.crs_validation_query(query_type);

COMMENT ON COLUMN audit_core.crs_validation_query.query_type IS
    'GROUP: batch check via crs_template_query_map (ANY(:tag_names) pattern).
     INDIVIDUAL: ad-hoc query for a specific comment via crs_comment_validation.';

-- ============================================================
-- Step 1b: Create crs_template_query_map
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_core.crs_template_query_map (
    id            UUID      NOT NULL DEFAULT gen_random_uuid(),
    template_id   UUID      NOT NULL,
    query_id      UUID      NOT NULL,
    priority      SMALLINT  NOT NULL DEFAULT 1,
    object_status TEXT      NOT NULL DEFAULT 'Active',
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT crs_template_query_map_pkey PRIMARY KEY (id),
    CONSTRAINT crs_template_query_map_uq   UNIQUE (template_id, query_id),
    CONSTRAINT crs_tqmap_template_fkey FOREIGN KEY (template_id)
        REFERENCES audit_core.crs_comment_template(id) ON DELETE CASCADE,
    CONSTRAINT crs_tqmap_query_fkey FOREIGN KEY (query_id)
        REFERENCES audit_core.crs_validation_query(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_crs_tqmap_template
    ON audit_core.crs_template_query_map(template_id);

CREATE INDEX IF NOT EXISTS idx_crs_tqmap_query
    ON audit_core.crs_template_query_map(query_id);

COMMENT ON TABLE audit_core.crs_template_query_map IS
    'Maps comment templates to GROUP validation queries (one template → one or more queries).
     Populated by category match: ct.category = vq.query_code (both in CRS-C### format).
     INDIVIDUAL queries use crs_comment_validation directly — no row here.';

-- ============================================================
-- Step 1c: Baseline populate — category = query_code (Variant B)
-- ============================================================
-- ct.category and vq.query_code are both in 'CRS-C###' format (confirmed via schema exploration).
-- Only active templates and active GROUP queries are linked.

INSERT INTO audit_core.crs_template_query_map (template_id, query_id, priority)
SELECT ct.id, vq.id, 1
FROM audit_core.crs_comment_template ct
JOIN audit_core.crs_validation_query vq
  ON vq.query_code    = ct.category
 AND vq.query_type    = 'GROUP'
 AND vq.is_active     = true
 AND vq.object_status = 'Active'
 AND ct.object_status = 'Active'
ON CONFLICT (template_id, query_id) DO NOTHING;

-- ============================================================
-- Step 2: Create view v_template_queries
-- ============================================================

CREATE OR REPLACE VIEW audit_core.v_template_queries AS
SELECT
    ct.id                   AS template_id,
    ct.category             AS template_category,
    ct.check_type,
    ct.template_text,
    vq.id                   AS query_id,
    vq.query_code,
    vq.query_name,
    vq.query_type,
    vq.evaluation_strategy,
    vq.has_parameters,
    vq.parameter_names,
    vq.sql_query,
    vq.response_template,
    tqm.priority
FROM audit_core.crs_template_query_map tqm
JOIN audit_core.crs_comment_template   ct ON ct.id = tqm.template_id
JOIN audit_core.crs_validation_query   vq ON vq.id = tqm.query_id
WHERE tqm.object_status = 'Active'
  AND ct.object_status  = 'Active'
  AND vq.is_active      = true
  AND vq.query_type     = 'GROUP';

COMMENT ON VIEW audit_core.v_template_queries IS
    'GROUP queries per template. Used by batch validation flow:
     GROUP BY category → fetch all tag_names → ONE SQL call via ANY(:tag_names).
     INDIVIDUAL queries are looked up directly from crs_comment_validation.';

-- ============================================================
-- Verification queries (run after applying migration)
-- ============================================================
-- SELECT query_type, COUNT(*) FROM audit_core.crs_validation_query GROUP BY query_type;
-- SELECT COUNT(*) FROM audit_core.crs_template_query_map;
-- SELECT template_category, query_code, priority FROM audit_core.v_template_queries ORDER BY template_category LIMIT 10;
-- SELECT ct.category, COUNT(*) AS tmpl_count
--   FROM audit_core.crs_comment_template ct
--   LEFT JOIN audit_core.crs_template_query_map m ON m.template_id = ct.id
--  WHERE ct.object_status = 'Active' AND m.id IS NULL
--  GROUP BY ct.category ORDER BY tmpl_count DESC LIMIT 20;
