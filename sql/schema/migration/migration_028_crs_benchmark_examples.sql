-- Migration 028: Benchmark examples table for Tier 2.5 matcher
-- Curated from A36 dry-run misclassification analysis (2026-04-07)

CREATE TABLE IF NOT EXISTS audit_core.crs_benchmark_example (
    id              SERIAL PRIMARY KEY,
    comment_pattern TEXT         NOT NULL,
    category        VARCHAR(20)  NOT NULL,
    assigned_status VARCHAR(30)  NOT NULL,
    confidence      NUMERIC(3,2) NOT NULL DEFAULT 0.95,
    rationale       TEXT,
    object_status   VARCHAR(20)  NOT NULL DEFAULT 'Active',
    created_by      VARCHAR(100) DEFAULT 'system',
    created_at      TIMESTAMPTZ  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_benchmark_active
    ON audit_core.crs_benchmark_example (object_status);

-- Seed: A36 dry-run confirmed misclassifications
INSERT INTO audit_core.crs_benchmark_example
    (comment_pattern, category, assigned_status, confidence, rationale)
VALUES
    -- Pattern 1: 1ooN notation question combined with parent tag suggestion
    (
      'parent tag can be considered from tag description wherever possible, and what is 1oo% in tag description ?',
      'OTHER', 'NEEDS_NEW_CATEGORY', 0.30,
      'Two unrelated topics: (1) suggestion about parent tag derivation, (2) question about 1ooN voting logic notation. Multi-topic: neither alone nor combined maps to a single CRS category.'
    ),
    -- Pattern 2: TNC applicability question for Control Panel
    (
      'control panel''s tnc used for switch?',
      'OTHER', 'NEEDS_NEW_CATEGORY', 0.30,
      'Question about whether Control Panel TNC applies to Switch tags. Advisory/informational — no explicit data error stated.'
    ),
    -- Pattern 3: TNC + speciality item check
    (
      'check filter tnc, speciality item considered?',
      'OTHER', 'NEEDS_NEW_CATEGORY', 0.30,
      'Question asking whether filter TNC and speciality item classification have been considered. Advisory, multi-topic with short description issue (CRS-C190) but whole comment is a question.'
    ),
    -- Pattern 4: NRV tag classification question
    (
      'this is nrv tag? check and confirm',
      'OTHER', 'NEEDS_NEW_CATEGORY', 0.30,
      'Question asking to confirm tag classification as NRV. Informational/advisory, not a data error.'
    ),
    -- Pattern 5: Valve TNC inconsistency with SP
    (
      'why valve tnc has sp - speciality piping when we have valve tnc separately available',
      'CRS-C201', 'DEFERRED', 0.55,
      'Question about TNC inconsistency (CRS-C201: TNC non-compliance question). Not a clear data error but relates to naming convention. Confidence 0.55 = partial match.'
    ),
    -- Pattern 6: TNC mismatch with Acoustic Hood
    (
      'tnc very different from acoustic hood%',
      'CRS-C202', 'DEFERRED', 0.55,
      'Comment about TNC inconsistency with equipment class description. Partial match to CRS-C202.'
    );
