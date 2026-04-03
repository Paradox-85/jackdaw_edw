-- Migration: Update crs_comment_template.check_type to match granular domain
-- vocabulary used by _detect_comment_domain() in crs_tier3_llm_classifier.py.
--
-- New domain vocabulary (maps 1:1 to eis_registers seq-codes):
--   area, process_unit, tag, equipment, model_part, tag_connection,
--   purchase_order, tag_class_property, tag_property, equipment_property,
--   document, other
--
-- Source of truth: eis_registers dict in the import flow.
-- _build_categories_line() matches via: domain.lower() IN check_type.lower()
--
-- Run: psql -U postgres -d engineering_core -f migration_024_crs_check_type_domain_update.sql

BEGIN;

-- -------------------------------------------------------------------------
-- 1. Normalise existing loose values before applying new mapping
-- -------------------------------------------------------------------------
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag'
WHERE  check_type IN ('tagdata', 'tag_register')
  AND  object_status = 'Active';

UPDATE audit_core.crs_comment_template
SET    check_type = 'equipment'
WHERE  check_type IN ('equipment_register')
  AND  object_status = 'Active';

UPDATE audit_core.crs_comment_template
SET    check_type = 'document'
WHERE  check_type IN ('doc', 'docs', 'doc_ref')
  AND  object_status = 'Active';

-- -------------------------------------------------------------------------
-- 2. Apply new granular domain values by category code (source of truth)
-- -------------------------------------------------------------------------

-- model_part  (EIS 209 — Model Part Register, seq -005-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'model_part'
WHERE  category IN ('CRS-C26')           -- model part name blank
  AND  object_status = 'Active';

-- tag_connection  (EIS 212 — Tag Physical Connections, seq -006-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag_connection'
WHERE  category IN ('CRS-C39', 'CRS-C45')  -- duplicate connections; from/to not in MTR
  AND  object_status = 'Active';

-- purchase_order  (EIS 214 — Purchase Order, seq -008-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'purchase_order'
WHERE  category IN ('CRS-C36', 'CRS-C37', 'CRS-C38')
  AND  object_status = 'Active';

-- tag_class_property  (EIS 307 — Tag Class Properties schema, seq -009-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag_class_property'
WHERE  category IN ('CRS-C04')           -- tag class not in RDL
  AND  object_status = 'Active';

-- tag_property  (EIS 303 — Tag Property Values, seq -010-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'tag_property'
WHERE  category IN (
    'CRS-C17',   -- property tag not in MTR
    'CRS-C18',   -- UOM present when value is NA
    'CRS-C19',   -- property value is zero
    'CRS-C20',   -- property not in class scope
    'CRS-C21',   -- tag has no properties
    'CRS-C22',   -- mandatory property missing
    'CRS-C48'    -- property UOM not in RDL
  )
  AND  object_status = 'Active';

-- equipment_property  (EIS 301 — Equipment Property Values, seq -011-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'equipment_property'
WHERE  category IN (
    'CRS-C23',   -- equipment class not in RDL
    'CRS-C24',   -- equipment description blank
    'CRS-C25',   -- manufacturer serial number blank
    'CRS-C27',   -- manufacturer company blank
    'CRS-C28'    -- equipment tag not in MTR
  )
  AND  object_status = 'Active';

-- area  (EIS 203 — Area register, seq -001-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'area'
WHERE  category IN ('CRS-C06', 'CRS-C07')  -- area code blank / invalid
  AND  object_status = 'Active';

-- process_unit  (EIS 204 — ProcessUnit register, seq -002-)
UPDATE audit_core.crs_comment_template
SET    check_type = 'process_unit'
WHERE  category IN ('CRS-C08', 'CRS-C09')  -- process unit missing / placeholder
  AND  object_status = 'Active';

-- document  (EIS 408-414, 420 — all Doc cross-refs, seq -016- to -024-)
-- CRS-C30..C35, C40, C46, C47 — keep 'document' or update from stale values
UPDATE audit_core.crs_comment_template
SET    check_type = 'document'
WHERE  category IN (
    'CRS-C30',   -- document missing or NYI/CAN status
    'CRS-C31',   -- tag has no document reference
    'CRS-C32',   -- document in mapping not in DocMaster
    'CRS-C33',   -- tag in mapping not in MTR
    'CRS-C34',   -- document area code missing
    'CRS-C35',   -- document process unit missing
    'CRS-C40',   -- equipment has no document mapping
    'CRS-C46',   -- tag linked to inactive document
    'CRS-C47'    -- revision status inconsistent
  )
  AND  object_status = 'Active';

-- -------------------------------------------------------------------------
-- 3. Verify — show distribution after migration
-- -------------------------------------------------------------------------
SELECT check_type,
       COUNT(*)                                         AS template_count,
       STRING_AGG(category, ', ' ORDER BY category)    AS categories
FROM   audit_core.crs_comment_template
WHERE  object_status = 'Active'
GROUP  BY check_type
ORDER  BY check_type;

COMMIT;
