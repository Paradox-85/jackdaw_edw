-- migration_023_naming_rules.sql
-- Unified naming rule table for CRS text generalizer.
-- Replaces hard-coded regex in crs_text_generalizer.py.
-- Domains: TAG (from JACK_namingRules_master.xlsx), DOC_VENDOR, DOC_DESIGN, DOC_EIS.
--
-- To apply:
--   psql -U jackdaw_admin -d jackdaw_edw -f migration_023_naming_rules.sql
-- Expected output: CREATE TABLE, 2 CREATE INDEX, ~21 INSERT rows.

-- ============================================================
-- 1. TABLE
-- ============================================================

CREATE TABLE audit_core.naming_rule (
    rule_id          SERIAL PRIMARY KEY,

    -- Classification
    domain           TEXT NOT NULL,          -- 'TAG' | 'DOC_VENDOR' | 'DOC_DESIGN' | 'DOC_EIS'
    category         TEXT,                   -- TAG:  ENS section label e.g. "5.2.1a MECHANICAL MAIN EQUIPMENT"
                                             -- DOC_EIS: 3-digit seq_num e.g. '016', '003'
    canonical_name   TEXT NOT NULL,          -- TAG:  human name e.g. "NR-5021 Instrument Tag"
                                             -- DOC:  official register name e.g. "412-Document_References_to_Tag"

    -- Identifiers (TAG domain only)
    nr_code          TEXT,                   -- NR-5021, NR-5182, ...
    ens_section_num  TEXT,                   -- "5.2.1a"

    -- Regex patterns
    regex_search     TEXT,                   -- Inline pattern (no anchors) for free-text matching.
                                             -- For DOC_EIS: also used as partial formal-number prefix.
    regex_full       TEXT,                   -- Anchored ^...$ for full-value validation
                                             -- (tag registers, formal document numbers).
    regex_aliases    TEXT[],                 -- Additional alias patterns for DOC rules:
                                             -- free-text abbreviations used by contractors (case-insensitive).

    -- Generalizer output
    mask             TEXT NOT NULL DEFAULT '<TAG>',   -- '<TAG>' or '<DOC>'

    -- Control
    sort_order       INTEGER NOT NULL DEFAULT 100,    -- Lower = applied first. DOC=10-37, TAG=50+
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    notes            TEXT,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Unique nr_code per TAG domain only
CREATE UNIQUE INDEX uq_naming_rule_nr_code
    ON audit_core.naming_rule (nr_code)
    WHERE domain = 'TAG' AND nr_code IS NOT NULL;

-- Fast filter by active domain
CREATE INDEX idx_naming_rule_domain
    ON audit_core.naming_rule (domain)
    WHERE is_active = TRUE;

COMMENT ON TABLE audit_core.naming_rule IS
    'Unified naming rules for CRS text generalizer (replaces hard-coded regex). '
    'Domains: TAG (from JACK_namingRules_master.xlsx), '
    'DOC_VENDOR / DOC_DESIGN / DOC_EIS (document number patterns). '
    'Edit rows directly to update matching rules — no code change required.';

COMMENT ON COLUMN audit_core.naming_rule.domain IS
    'TAG | DOC_VENDOR | DOC_DESIGN | DOC_EIS';
COMMENT ON COLUMN audit_core.naming_rule.category IS
    'For TAG: ENS section label. For DOC_EIS: 3-digit seq_num (016, 003, ...).';
COMMENT ON COLUMN audit_core.naming_rule.canonical_name IS
    'For TAG: human-readable rule name. For DOC: official register/document name.';
COMMENT ON COLUMN audit_core.naming_rule.regex_search IS
    'Pattern for inline matching in free text (no anchors, case-insensitive). '
    'For DOC_EIS: also serves as partial prefix to match formal document numbers.';
COMMENT ON COLUMN audit_core.naming_rule.regex_full IS
    'Anchored ^...$ pattern for full-value validation (tag fields, formal doc numbers).';
COMMENT ON COLUMN audit_core.naming_rule.regex_aliases IS
    'Array of additional alias patterns for DOC rules — '
    'free-text abbreviations used by contractors (e.g. Doc-ref-to-tag, MTR, Equip reg).';
COMMENT ON COLUMN audit_core.naming_rule.mask IS
    'Replacement token emitted by generalizer: <TAG> or <DOC>.';
COMMENT ON COLUMN audit_core.naming_rule.sort_order IS
    'Lower value = applied first in generalizer. '
    'DOC rules (10-37) must run before TAG rules (50+) to avoid partial overlap.';


-- ============================================================
-- 2. SEED — DOC_VENDOR
-- Example: JDAW-5410001-B01-00012
--   JDAW = fixed
--   5410001 = 7-digit document number
--   B01 = type code (letter + 2 digits)
--   00012 = 5-digit sequence
-- ============================================================

INSERT INTO audit_core.naming_rule
    (domain, canonical_name, regex_full, regex_aliases, mask, sort_order, notes)
VALUES (
    'DOC_VENDOR',
    'Vendor Document',
    'JDAW-\d{7}-[A-Z]\d{2}-\d{5}',
    ARRAY[
        'vendor[\s\-\.]*doc',
        'supplier[\s\-\.]*doc',
        'vdr[\s\-\.]*doc'
    ],
    '<DOC>', 10,
    'Vendor/supplier document. Fixed prefix JDAW + 7-digit num + type-code + 5-digit seq.'
);


-- ============================================================
-- 3. SEED — DOC_DESIGN
-- Example: JDAW-KVE-E-BA-6066-00226
--   JDAW-KVE- = fixed prefix for all design documents
--   E = discipline code
--   BA = document type code (2 letters)
--   6066 = 4-digit area/system code
--   00226 = 5-digit sequence
-- ============================================================

INSERT INTO audit_core.naming_rule
    (domain, canonical_name, regex_full, regex_aliases, mask, sort_order, notes)
VALUES (
    'DOC_DESIGN',
    'Design Document',
    'JDAW-KVE-[A-Z]-[A-Z]{2}-\d{4}-\d{5}',
    ARRAY[
        'design[\s\-\.]*doc',
        'engineering[\s\-\.]*doc',
        'kve[\s\-\.]*doc'
    ],
    '<DOC>', 11,
    'Design/engineering document. Fixed prefix JDAW-KVE-.'
);


-- ============================================================
-- 4. SEED — DOC_EIS (18 registers)
-- Base pattern: JDAW-KVE-E-JA-6944-00001-{seq}-{revision}.CSV
-- seq = 3-digit register sequence number (001, 002, 003, ...)
-- revision = alphanumeric revision code (A01, B02, etc.)
--
-- Alias conventions:
--   Document  -> Doc
--   Equipment -> Equip., Equi., Equip, Equi
--   Process Unit -> PU, Proc Unit
--   Plant Code -> Plant
--   Tag Physical Connection -> Tag-to-Tag, Tag-Tag, Tag-2-Tag
--   References -> Ref
-- ============================================================

INSERT INTO audit_core.naming_rule
    (domain, category, canonical_name, regex_full, regex_search, regex_aliases, mask, sort_order, notes)
VALUES

-- 001: Area Register (203-Area.xlsx)
('DOC_EIS', '001', '203-Area',
 'JDAW-KVE-E-JA-6944-00001-001-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-001-',
 ARRAY[
     '001[\s\-_]*area',
     '203[\s\-_]*area',
     'area[\s\-_]*reg(?:ister)?'
 ],
 '<DOC>', 20, '203-Area.xlsx'),

-- 002: Process Unit Register (204-ProcessUnit.xlsx)
('DOC_EIS', '002', '204-ProcessUnit',
 'JDAW-KVE-E-JA-6944-00001-002-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-002-',
 ARRAY[
     '002[\s\-_]*p[ru]',
     '204[\s\-_]*proc',
     'process[\s\-_]*unit[\s\-_]*reg(?:ister)?',
     'proc[\s\.\-]*unit[\s\-_]*reg(?:ister)?',
     '\bpu[\s\-_]*reg\b'
 ],
 '<DOC>', 21, '204-ProcessUnit.xlsx'),

-- 003: Tag Register (205-Tag-register.xlsx)
('DOC_EIS', '003', '205-Tag-register',
 'JDAW-KVE-E-JA-6944-00001-003-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-003-',
 ARRAY[
     '003[\s\-_]*tag',
     '205[\s\-_]*tag',
     'tag[\s\-_]*reg(?:ister)?',
     '\bmtr\b',
     'master[\s\-_]*tag[\s\-_]*reg(?:ister)?'
 ],
 '<DOC>', 22, '205-Tag-register.xlsx'),

-- 004: Equipment Register (206-Equipment-register.xlsx)
('DOC_EIS', '004', '206-Equipment-register',
 'JDAW-KVE-E-JA-6944-00001-004-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-004-',
 ARRAY[
     '004[\s\-_]*equip',
     '206[\s\-_]*equip',
     'equi[p]?[\s\-\.]*reg(?:ister)?',
     'equipment[\s\-_]*reg(?:ister)?'
 ],
 '<DOC>', 23, '206-Equipment-register.xlsx'),

-- 005: Model Part Register (209-Model-Part-register.xlsx)
('DOC_EIS', '005', '209-Model-Part-register',
 'JDAW-KVE-E-JA-6944-00001-005-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-005-',
 ARRAY[
     '005[\s\-_]*model',
     '209[\s\-_]*model',
     'model[\s\-_]*part[\s\-_]*reg(?:ister)?'
 ],
 '<DOC>', 24, '209-Model-Part-register.xlsx'),

-- 006: Tag Physical Connection (212-Tag Physical Connection.xlsx)
-- Aliases: Tag-to-Tag, Tag To Tag, Tag-Tag, Tag-2-Tag
('DOC_EIS', '006', '212-Tag-Physical-Connection',
 'JDAW-KVE-E-JA-6944-00001-006-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-006-',
 ARRAY[
     '006[\s\-_]*tag',
     '212[\s\-_]*tag',
     'tag[\s\-_]*phys(?:ical)?[\s\-_]*conn(?:ection)?',
     'tag[\s\-_]*to[\s\-_]*tag',
     'tag[\s\-_]*-[\s\-_]*tag',
     'tag[\s\-_]*2[\s\-_]*tag'
 ],
 '<DOC>', 25, '212-Tag Physical Connection.xlsx'),

-- 008: Purchase Order (214-Purchase-order.xlsx)
('DOC_EIS', '008', '214-Purchase-order',
 'JDAW-KVE-E-JA-6944-00001-008-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-008-',
 ARRAY[
     '008[\s\-_]*po',
     '008[\s\-_]*purch',
     '214[\s\-_]*po',
     'purchase[\s\-_]*order[\s\-_]*reg(?:ister)?',
     '\bpo[\s\-_]*reg\b'
 ],
 '<DOC>', 26, '214-Purchase-order.xlsx'),

-- 009: Tag Class Properties (307-Tag-class-properties.xlsx)
('DOC_EIS', '009', '307-Tag-class-properties',
 'JDAW-KVE-E-JA-6944-00001-009-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-009-',
 ARRAY[
     '009[\s\-_]*tag[\s\-_]*class',
     '307[\s\-_]*tag',
     'tag[\s\-_]*class[\s\-_]*prop(?:ert(?:y|ies))?'
 ],
 '<DOC>', 27, '307-Tag-class-properties.xlsx'),

-- 010: Tag Property Value (303-Tag-property-value.xlsx)
('DOC_EIS', '010', '303-Tag-property-value',
 'JDAW-KVE-E-JA-6944-00001-010-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-010-',
 ARRAY[
     '010[\s\-_]*tag',
     '303[\s\-_]*tag',
     'tag[\s\-_]*prop(?:ert(?:y|ies))?[\s\-_]*val(?:ue)?'
 ],
 '<DOC>', 28, '303-Tag-property-value.xlsx'),

-- 011: Equipment Property Value (301-Equipment-property-value.xlsx)
('DOC_EIS', '011', '301-Equipment-property-value',
 'JDAW-KVE-E-JA-6944-00001-011-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-011-',
 ARRAY[
     '011[\s\-_]*equip',
     '301[\s\-_]*equip',
     'equi[p]?[\s\-_]*prop(?:ert(?:y|ies))?[\s\-_]*val(?:ue)?'
 ],
 '<DOC>', 29, '301-Equipment-property-value.xlsx'),

-- 016: Document References to Tag (412-Document_References_to_Tag.xlsx)
('DOC_EIS', '016', '412-Document_References_to_Tag',
 'JDAW-KVE-E-JA-6944-00001-016-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-016-',
 ARRAY[
     '016[\s\-_]*doc',
     '412[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*tag',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*tag',
     'document[\s\-_]*ref(?:erence)?[s]?[\s\-_]*tag'
 ],
 '<DOC>', 30, '412-Document_References_to_Tag.xlsx'),

-- 017: Document References to Area (411-Document_References_to_Area.xlsx)
('DOC_EIS', '017', '411-Document_References_to_Area',
 'JDAW-KVE-E-JA-6944-00001-017-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-017-',
 ARRAY[
     '017[\s\-_]*doc',
     '411[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*area',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*area'
 ],
 '<DOC>', 31, '411-Document_References_to_Area.xlsx'),

-- 018: Document References to Process Unit (410-Document_References_to_ProcessUnit.xlsx)
('DOC_EIS', '018', '410-Document_References_to_ProcessUnit',
 'JDAW-KVE-E-JA-6944-00001-018-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-018-',
 ARRAY[
     '018[\s\-_]*doc',
     '410[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*p[ru]',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*proc(?:ess)?[\s\-_]*unit',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*process[\s\-_]*unit'
 ],
 '<DOC>', 32, '410-Document_References_to_ProcessUnit.xlsx'),

-- 019: Document References to Equipment (413-Document_References_to_Equipment.xlsx)
('DOC_EIS', '019', '413-Document_References_to_Equipment',
 'JDAW-KVE-E-JA-6944-00001-019-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-019-',
 ARRAY[
     '019[\s\-_]*doc',
     '413[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*equi[p]?',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*equi[p]?(?:ment)?'
 ],
 '<DOC>', 33, '413-Document_References_to_Equipment.xlsx'),

-- 020: Document References to Model Part (414-Document_References_to_ModelPart.xlsx)
('DOC_EIS', '020', '414-Document_References_to_ModelPart',
 'JDAW-KVE-E-JA-6944-00001-020-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-020-',
 ARRAY[
     '020[\s\-_]*doc',
     '414[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*model',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*model[\s\-_]*part'
 ],
 '<DOC>', 34, '414-Document_References_to_ModelPart.xlsx'),

-- 022: Document References to Purchase Order (420-Document_References_to_PurchaseOrder.xlsx)
('DOC_EIS', '022', '420-Document_References_to_PurchaseOrder',
 'JDAW-KVE-E-JA-6944-00001-022-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-022-',
 ARRAY[
     '022[\s\-_]*doc',
     '420[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*(?:po|purch)',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*purchase[\s\-_]*order'
 ],
 '<DOC>', 35, '420-Document_References_to_PurchaseOrder.xlsx'),

-- 023: Document References to Plant Code (409-Document_References_to_PlantCode.xlsx)
('DOC_EIS', '023', '409-Document_References_to_PlantCode',
 'JDAW-KVE-E-JA-6944-00001-023-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-023-',
 ARRAY[
     '023[\s\-_]*doc',
     '409[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*plant',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*plant[\s\-_]*code'
 ],
 '<DOC>', 36, '409-Document_References_to_PlantCode.xlsx'),

-- 024: Document References to Site (408-Document_References_to_Site.xlsx)
('DOC_EIS', '024', '408-Document_References_to_Site',
 'JDAW-KVE-E-JA-6944-00001-024-[A-Z0-9]+\.CSV',
 'JDAW-KVE-E-JA-6944-00001-024-',
 ARRAY[
     '024[\s\-_]*doc',
     '408[\s\-_]*doc',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*to[\s\-\.]*site',
     'doc[s]?[\s\-\.]*ref[s]?[\s\-\.]*site'
 ],
 '<DOC>', 37, '408-Document_References_to_Site.xlsx');


-- ============================================================
-- 5. VERIFY
-- ============================================================
-- Run after applying to confirm row counts:
--
-- SELECT domain, count(*) FROM audit_core.naming_rule GROUP BY domain ORDER BY domain;
-- Expected:
--   DOC_DESIGN | 1
--   DOC_EIS    | 18
--   DOC_VENDOR | 1
--
-- TAG rows are loaded separately from JACK_namingRules_master.xlsx
-- via migration_024_tag_naming_rules_seed.sql (pending xlsx export).
