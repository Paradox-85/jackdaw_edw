-- Migration: Add symbol_ascii column to ontology_core.uom
-- Purpose: Store ASCII-safe equivalents of Unicode symbols for EIS CSV export compatibility
-- Date: 2026-04-09
-- Dependencies: None (must run before 20260409_create_uom_alias.sql)

-- Add symbol_ascii column
ALTER TABLE ontology_core.uom
ADD COLUMN IF NOT EXISTS symbol_ascii TEXT;

-- Copy existing values from symbol to symbol_ascii
UPDATE ontology_core.uom
SET symbol_ascii = symbol
WHERE symbol_ascii IS NULL AND symbol IS NOT NULL;

-- Convert Unicode symbols to ASCII equivalents
UPDATE ontology_core.uom
SET symbol_ascii = REGEXP_REPLACE(
    REGEXP_REPLACE(
        REGEXP_REPLACE(
            REGEXP_REPLACE(symbol_ascii, '²', '2', 'g'),
            '³', '3', 'g'
        ),
        '°', 'deg', 'g'
    ),
    '[Μμµ]', 'u', 'g'
)
WHERE symbol IS NOT NULL;

-- Handle special cases: Ångstrom symbol
UPDATE ontology_core.uom
SET symbol_ascii = REGEXP_REPLACE(symbol_ascii, 'Å', 'A', 'g')
WHERE symbol LIKE '%Å%';

-- Remove any whitespace artifacts
UPDATE ontology_core.uom
SET symbol_ascii = REGEXP_REPLACE(symbol_ascii, '\s+', ' ', 'g');
UPDATE ontology_core.uom
SET symbol_ascii = TRIM(symbol_ascii);

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_uom_symbol_ascii_lower
ON ontology_core.uom (LOWER(symbol_ascii))
WHERE symbol_ascii IS NOT NULL;

-- Add comment
COMMENT ON COLUMN ontology_core.uom.symbol_ascii IS 'ASCII-safe version of symbol for CSV export (Unicode symbols converted: ²→2, ³→3, °→deg, μ→u, Å→A)';
