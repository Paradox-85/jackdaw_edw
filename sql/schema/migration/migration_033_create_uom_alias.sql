-- =============================================================================
-- Migration: migration_035_uom_alias_seed.sql
-- Purpose:   Seed common UoM spelling variants into ontology_core.uom_alias
-- Depends:   migration_032 (symbol_ascii), migration_033 (uom_alias table)
-- Safe:      All INSERTs use ON CONFLICT DO NOTHING — idempotent
-- NOTE:      No BEGIN/COMMIT — autocommit mode
--
-- FIXES vs previous version:
--   Line ~185: '"'  (double-quote as inch alias) → e'\"' / $$ style
--   Line ~195: "'"  (single-quote as foot alias)  → '''  (doubled quote)
--   Removed CREATE TABLE block (already in migration_033)
-- =============================================================================

-- BAR variants
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'BAR', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR'
ON CONFLICT DO NOTHING;

-- BAR(A) variants
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'BAR(A)', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar(a)', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bara', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar absolute', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(A)'
ON CONFLICT DO NOTHING;

-- BAR(G) variants
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'BAR(G)', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar(g)', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'barg', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'bar gauge', 'seed' FROM ontology_core.uom WHERE symbol = 'BAR(G)'
ON CONFLICT DO NOTHING;

-- Temperature: °C
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, '°C', 'seed' FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'degC', 'seed' FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg C', 'seed' FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg c', 'seed' FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'celsius', 'seed' FROM ontology_core.uom WHERE symbol = '°C'
ON CONFLICT DO NOTHING;

-- Temperature: °F
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, '°F', 'seed' FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'degF', 'seed' FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg F', 'seed' FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'deg f', 'seed' FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'fahrenheit', 'seed' FROM ontology_core.uom WHERE symbol = '°F'
ON CONFLICT DO NOTHING;

-- Length: MM
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'MM', 'seed' FROM ontology_core.uom WHERE lower(symbol) = 'mm'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'mm', 'seed' FROM ontology_core.uom WHERE lower(symbol) = 'mm'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'millimeter', 'seed' FROM ontology_core.uom WHERE lower(symbol) = 'mm'
ON CONFLICT DO NOTHING;

-- Length: IN (inch)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'IN', 'seed' FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'in', 'seed' FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'inch', 'seed' FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

-- FIX: double-quote (") as inch symbol — use e-string to escape
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, e'\"', 'seed' FROM ontology_core.uom WHERE symbol = 'IN'
ON CONFLICT DO NOTHING;

-- Length: FT (foot)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT', 'seed' FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft', 'seed' FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'foot', 'seed' FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

-- FIX: single-quote (') as foot symbol — doubled single-quote inside string literal
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, '''', 'seed' FROM ontology_core.uom WHERE symbol = 'FT'
ON CONFLICT DO NOTHING;

-- Area: MM²
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'MM²', 'seed' FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'mm2', 'seed' FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'mm^2', 'seed' FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'sqmm', 'seed' FROM ontology_core.uom WHERE symbol = 'MM²'
ON CONFLICT DO NOTHING;

-- Area: CM²
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'CM²', 'seed' FROM ontology_core.uom WHERE symbol = 'CM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cm2', 'seed' FROM ontology_core.uom WHERE symbol = 'CM²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'sqcm', 'seed' FROM ontology_core.uom WHERE symbol = 'CM²'
ON CONFLICT DO NOTHING;

-- Area: FT²
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT²', 'seed' FROM ontology_core.uom WHERE symbol = 'FT²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft2', 'seed' FROM ontology_core.uom WHERE symbol = 'FT²'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'sqft', 'seed' FROM ontology_core.uom WHERE symbol = 'FT²'
ON CONFLICT DO NOTHING;

-- Volume: M³
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'M³', 'seed' FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3', 'seed' FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm^3', 'seed' FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cbm', 'seed' FROM ontology_core.uom WHERE symbol = 'M³'
ON CONFLICT DO NOTHING;

-- Volume: M³/H
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'M³/H', 'seed' FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3/h', 'seed' FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3/hr', 'seed' FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cbm/h', 'seed' FROM ontology_core.uom WHERE symbol = 'M³/H'
ON CONFLICT DO NOTHING;

-- Volume: FT³
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT³', 'seed' FROM ontology_core.uom WHERE symbol = 'FT³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft3', 'seed' FROM ontology_core.uom WHERE symbol = 'FT³'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cf', 'seed' FROM ontology_core.uom WHERE symbol = 'FT³'
ON CONFLICT DO NOTHING;

-- Volume: FT³/H
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'FT³/H', 'seed' FROM ontology_core.uom WHERE symbol = 'FT³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'ft3/h', 'seed' FROM ontology_core.uom WHERE symbol = 'FT³/H'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'cf/h', 'seed' FROM ontology_core.uom WHERE symbol = 'FT³/H'
ON CONFLICT DO NOTHING;

-- Power: kW
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kW', 'seed' FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'KW', 'seed' FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'Kw', 'seed' FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kilowatt', 'seed' FROM ontology_core.uom WHERE symbol = 'kW'
ON CONFLICT DO NOTHING;

-- Power: HP (horsepower — matched by name, symbol varies)
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'HP', 'seed' FROM ontology_core.uom WHERE lower(name) LIKE '%horsepower%'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'hp', 'seed' FROM ontology_core.uom WHERE lower(name) LIKE '%horsepower%'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'horsepower', 'seed' FROM ontology_core.uom WHERE lower(name) LIKE '%horsepower%'
ON CONFLICT DO NOTHING;

-- Pressure: Pa
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'Pa', 'seed' FROM ontology_core.uom WHERE symbol = 'Pa'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'pa', 'seed' FROM ontology_core.uom WHERE symbol = 'Pa'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'pascal', 'seed' FROM ontology_core.uom WHERE symbol = 'Pa'
ON CONFLICT DO NOTHING;

-- Mass: kg
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kg', 'seed' FROM ontology_core.uom WHERE lower(symbol) = 'kg'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'KG', 'seed' FROM ontology_core.uom WHERE lower(symbol) = 'kg'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'kilogram', 'seed' FROM ontology_core.uom WHERE lower(symbol) = 'kg'
ON CONFLICT DO NOTHING;

-- Flow: M³/S
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'M³/S', 'seed' FROM ontology_core.uom WHERE symbol = 'M³/S'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'm3/s', 'seed' FROM ontology_core.uom WHERE symbol = 'M³/S'
ON CONFLICT DO NOTHING;

-- Flow: GPM
INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'GPM', 'seed' FROM ontology_core.uom WHERE symbol = 'GPM'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'gpm', 'seed' FROM ontology_core.uom WHERE symbol = 'GPM'
ON CONFLICT DO NOTHING;

INSERT INTO ontology_core.uom_alias (uom_id, alias, source)
SELECT id, 'gal/min', 'seed' FROM ontology_core.uom WHERE symbol = 'GPM'
ON CONFLICT DO NOTHING;

-- Verify
SELECT 'uom_alias seeded' AS status, COUNT(*) AS count
FROM ontology_core.uom_alias
WHERE source = 'seed';