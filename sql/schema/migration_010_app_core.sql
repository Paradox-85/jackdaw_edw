/*
Purpose: Create app_core schema for application-level service data.
         Stores UI users (with bcrypt passwords + roles) and user feedback.
         Separate from audit_core which is reserved for ETL audit data.
Date:    2026-03-18
*/

CREATE SCHEMA IF NOT EXISTS app_core;

-- ── UI Users ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS app_core.ui_user (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    username      TEXT        NOT NULL UNIQUE,
    password_hash TEXT        NOT NULL,      -- bcrypt hash, never plaintext
    role          TEXT        NOT NULL DEFAULT 'viewer'
                              CHECK (role IN ('viewer', 'admin')),
    is_active     BOOLEAN     NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login    TIMESTAMPTZ
);

COMMENT ON TABLE  app_core.ui_user IS 'Jackdaw EDW UI users with bcrypt passwords and role-based access.';
COMMENT ON COLUMN app_core.ui_user.password_hash IS 'bcrypt hash (rounds=12). Never store plaintext.';
COMMENT ON COLUMN app_core.ui_user.role          IS 'viewer = read-only pages; admin = full access incl. ETL/EIS.';

-- ── User Feedback & Enhancement Requests ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS app_core.ui_feedback (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        REFERENCES app_core.ui_user(id) ON DELETE SET NULL,
    username      TEXT,                      -- denormalized for display after user deletion
    feedback_type TEXT        NOT NULL
                              CHECK (feedback_type IN ('Bug', 'Enhancement', 'Question')),
    title         TEXT        NOT NULL,
    body          TEXT        NOT NULL,
    status        TEXT        NOT NULL DEFAULT 'Open'
                              CHECK (status IN ('Open', 'In Progress', 'Done', 'Rejected')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE app_core.ui_feedback IS 'User-submitted feedback and enhancement requests from the UI.';

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_ui_feedback_status   ON app_core.ui_feedback (status);
CREATE INDEX IF NOT EXISTS idx_ui_feedback_created  ON app_core.ui_feedback (created_at DESC);

-- ── Seed: default admin user ──────────────────────────────────────────────────
-- Password: 'admin' (bcrypt rounds=12)
-- IMPORTANT: Change this password immediately after first login!
-- Regenerate hash: python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt(rounds=12)).decode())"
INSERT INTO app_core.ui_user (username, password_hash, role)
VALUES (
    'admin',
    '$2b$12$7Urgew0/laimtQ3ZlSPbZ.xESy2XqjO0uyqlmdKUgVaEQRljk7haG',
    'admin'
)
ON CONFLICT (username) DO NOTHING;

-- Grant read access to edw_viewer for feedback table (viewer can submit, admin reads all)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edw_viewer') THEN
        GRANT USAGE ON SCHEMA app_core TO edw_viewer;
        -- edw_viewer cannot INSERT/UPDATE — db_write() uses admin engine
    END IF;
END $$;
