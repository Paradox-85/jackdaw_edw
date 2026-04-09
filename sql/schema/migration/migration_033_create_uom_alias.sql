-- Migration: Create ontology_core.uom_alias table and seed with common variants
-- Purpose: Store all known UoM spelling variants (barg, deg C, mm2) for resolution to canonical symbol_ascii
-- Date: 2026-04-09
-- Dependencies: 20260409_add_uom_symbol_ascii.sql (symbol_ascii column required)

-- Create uom_alias table
CREATE TABLE IF NOT EXISTS ontology_core.uom_alias (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uom_id        UUID NOT NULL REFERENCES ontology_core.uom(id) ON DELETE CASCADE,
    alias         TEXT NOT NULL,
    alias_lower   TEXT GENERATED ALWAYS AS (lower(alias)) STORED,
    source        TEXT,
    object_status TEXT NOT NULL DEFAULT 'Active',
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_uom_alias_uom_id ON ontology_core.uom_alias(uom_id);
CREATE INDEX IF NOT EXISTS idx_uom_alias_alias_lower ON ontology_core.uom_alias(alias_lower);
CREATE INDEX IF NOT EXISTS idx_uom_alias_status ON ontology_core.uom_alias(object_status);

-- Add comment
COMMENT ON TABLE ontology_core.uom_alias IS 'Stores common spelling variants of UoM symbols for resolution to canonical symbol_ascii';
COMMENT ON COLUMN ontology_core.uom_alias.alias IS 'Alternative spelling of the UoM symbol (e.g., "deg C", "bar(g)")';
COMMENT ON COLUMN ontology_core.uom_alias.alias_lower IS 'Generated column: lower(alias) for case-insensitive lookups';

-- Seed common UoM variants based on actual data in ontology_core.uom
-- Note: These INSERT statements use the actual UUIDs from the database

-- BAR variants
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'BAR', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR'
ON CONFLICT DO NOTHING;

-- BAR(A) variants
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'BAR(A)', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar(a)', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bara', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar absolute', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

-- BAR(G) variants
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'BAR(G)', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar(g)', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'barg', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar gauge', 'seed'
FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

-- Temperature variants (°C, °F)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, '°C', 'seed'
FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'degC', 'seed'
FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg C', 'seed'
FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg c', 'seed'
FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'celsius', 'seed'
FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, '°F', 'seed'
FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'degF', 'seed'
FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg F', 'seed'
FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg f', 'seed'
FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'fahrenheit', 'seed'
FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

-- Length variants (MM, IN, FT)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'MM', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) = 'mm'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'mm', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) = 'mm'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'millimeter', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) = 'mm'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'IN', 'seed'
FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'in', 'seed'
FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'inch', 'seed'
FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, '"', 'seed'
FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'foot', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, "'", 'seed'
FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

-- Area variants (MM², CM², FT², M²)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'MM²', 'seed'
FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'mm2', 'seed'
FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'mm^2', 'seed'
FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'sqmm', 'seed'
FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'CM²', 'seed'
FROM ontology_core.uom WHERE symbol = 'CM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cm2', 'seed'
FROM ontology_core.uom WHERE symbol = 'CM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'sqcm', 'seed'
FROM ontology_core.uom WHERE symbol = 'CM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT²', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft2', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'sqft', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT²'
ON CONFLICT DO NOTHING;

-- Volume variants (M³, FT³, CM³, L)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'M³', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm^3', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cbm', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'M³/H', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3/h', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3/hr', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cbm/h', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT³', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft3', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cf', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT³/H', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft3/h', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cf/h', 'seed'
FROM ontology_core.uom WHERE symbol = 'FT³/H'
ON CONFLICT DO NOTHING;

-- Power variants (kW, W, HP)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kW', 'seed'
FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'KW', 'seed'
FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'Kw', 'seed'
FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kilowatt', 'seed'
FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'HP', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) LIKE '%horse power%'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'hp', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) LIKE '%horse power%'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'horsepower', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) LIKE '%horse power%'
ON CONFLICT DO NOTHING;

-- Pressure variants (Pa, kPa, MPa)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'Pa', 'seed'
FROM ontology_core.uom WHERE symbol = 'Pa'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'pa', 'seed'
FROM ontology_core.uom WHERE symbol = 'Pa'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'pascal', 'seed'
FROM ontology_core.uom WHERE symbol = 'Pa'
ON CONFLICT DO NOTHING;

-- Mass variants (kg, g, t)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kg', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) = 'kg'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'KG', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) = 'kg'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kilogram', 'seed'
FROM ontology_core.uom WHERE LOWER(symbol) = 'kg'
ON CONFLICT DO NOTHING;

-- Flow rate variants (m3/s, L/min, GPM)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'M³/S', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³/S'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3/s', 'seed'
FROM ontology_core.uom WHERE symbol = 'M³/S'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'GPM', 'seed'
FROM ontology_core.uom WHERE symbol = 'GPM'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'gpm', 'seed'
FROM ontology_core.uom WHERE symbol = 'GPM'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'gal/min', 'seed'
FROM ontology_core.uom WHERE symbol = 'GPM'
ON CONFLICT DO NOTHING;

-- Verify seed data
SELECT 'uom_alias seeded' as status, COUNT(*) as count FROM ontology_core.uom_alias WHERE source = 'seed';
