-- =============================================================================
-- CRS Phase 3 — Validation Queries per Category
-- Source: crs_comment_template (229 categories), schema.sql
-- Generated: 2026-04-07 — fixed SQL bugs vs original draft
--
-- BUGS FIXED vs original:
--   1. CRS-C050: added missing ) to close CTE before SELECT DISTINCT
--   2. CRS-C185: corrected NOT LIKE '% %' → NOT LIKE '%  %' (double space)
--   3. CRS-C037/C038/C140: renamed param to :po_codes
--
-- Контракт вывода для ВСЕХ запросов:
--   object_key   TEXT — идентификатор объекта
--   check_field  TEXT — проверяемое поле
--   actual_value TEXT — фактическое значение (NULL если пусто)
--   is_resolved  BOOL — TRUE = требование выполнено
--
-- Параметры (передаются через SQLAlchemy bindparam):
--   :tag_names       TEXT[] — для tag/equipment/connection домена
--   :doc_numbers     TEXT[] — для document домена
--   :po_codes        TEXT[] — для purchase_order домена
--
-- check_type справочник:
--   NOT_NULL    — actual_value IS NOT NULL AND != ''
--   FK_RESOLVED — FK найден (id IS NOT NULL)
--   VALUE_MATCH — actual_value == expected_result
--   REGEX       — re.match(expected_result, actual_value)
--   AGGREGATE   — COUNT запрос, параметры не нужны
--   COUNT_ZERO  — is_resolved = (count == 0)
--   SEMANTIC    — требует LLM verdict
--   DEFERRED    — нет данных в EDW, пропускать
-- =============================================================================

-- =============================================================================
-- DOMAIN: tag
-- =============================================================================

-- CRS-C001: missing required fields (general)
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'mandatory_fields_composite' AS check_field,
  CONCAT_WS('; ',
    CASE WHEN t.class_id IS NULL THEN 'class_id=NULL' END,
    CASE WHEN t.description IS NULL OR t.description = '' THEN 'description=NULL' END,
    CASE WHEN t.process_unit_id IS NULL THEN 'process_unit_id=NULL' END,
    CASE WHEN t.safety_critical_item IS NULL OR t.safety_critical_item = '' THEN 'safety_critical_item=NULL' END
  ) AS actual_value,
  (t.class_id IS NOT NULL
    AND t.description IS NOT NULL AND t.description != ''
    AND t.process_unit_id IS NOT NULL
    AND t.safety_critical_item IS NOT NULL AND t.safety_critical_item != ''
  ) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C001

-- CRS-C002 / CRS-C182: tag description blank
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'description' AS check_field,
  t.description AS actual_value,
  (t.description IS NOT NULL AND TRIM(t.description) != '') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C002, CRS-C182

-- CRS-C003 / CRS-C184: description too long (> 255 chars)
-- check_type: REGEX, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'description_length' AS check_field,
  LENGTH(t.description)::TEXT AS actual_value,
  (t.description IS NULL OR LENGTH(t.description) <= 255) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C003, CRS-C184

-- CRS-C004 / CRS-C178 / CRS-C180: tag class not in ISM / class blank / not in RDL
-- check_type: FK_RESOLVED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'class_id' AS check_field,
  COALESCE(c.name, t.tag_class_raw, 'NULL') AS actual_value,
  (t.class_id IS NOT NULL AND c.id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id AND c.object_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C004, CRS-C178, CRS-C180

-- CRS-C005 / CRS-C202: TNC non-compliance (tag name must start with JDA-)
-- check_type: REGEX, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'tag_name_pattern' AS check_field,
  t.tag_name AS actual_value,
  (t.tag_name LIKE 'JDA-%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C005, CRS-C202

-- CRS-C006 / CRS-C176: area code blank
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'area_id' AS check_field,
  COALESCE(a.code, t.area_code_raw, 'NULL') AS actual_value,
  (t.area_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.area a ON a.id = t.area_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C006, CRS-C176

-- CRS-C007 / CRS-C051 / CRS-C052 / CRS-C177: area code invalid / duplicated / is NA
-- check_type: FK_RESOLVED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'area_code_raw' AS check_field,
  COALESCE(t.area_code_raw, 'NULL') AS actual_value,
  (t.area_id IS NOT NULL
    AND t.area_code_raw IS NOT NULL
    AND UPPER(TRIM(t.area_code_raw)) != 'NA'
    AND t.area_code_raw NOT LIKE '%,%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C007, CRS-C051, CRS-C052, CRS-C177

-- CRS-C008 / CRS-C198: process unit code missing (blank)
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'process_unit_id' AS check_field,
  COALESCE(pu.code, t.process_unit_raw, 'NULL') AS actual_value,
  (t.process_unit_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C008, CRS-C198

-- CRS-C009 / CRS-C197 / CRS-C199: process unit not in register / is NA
-- check_type: FK_RESOLVED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'process_unit_raw' AS check_field,
  COALESCE(t.process_unit_raw, 'NULL') AS actual_value,
  (t.process_unit_id IS NOT NULL
    AND t.process_unit_raw IS NOT NULL
    AND UPPER(TRIM(t.process_unit_raw)) != 'NA') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C009, CRS-C197, CRS-C199

-- CRS-C010 / CRS-C163: parent tag missing for physical tag
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'parent_tag_id' AS check_field,
  COALESCE(p.tag_name, t.parent_tag_raw, 'NULL') AS actual_value,
  (t.parent_tag_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN project_core.tag p ON p.id = t.parent_tag_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C010, CRS-C163

-- CRS-C011 / CRS-C164: parent tag not in MTR (raw set but FK NULL)
-- check_type: FK_RESOLVED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'parent_tag_raw' AS check_field,
  COALESCE(t.parent_tag_raw, 'NULL') AS actual_value,
  (t.parent_tag_raw IS NULL
    OR t.parent_tag_raw = ''
    OR t.parent_tag_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C011, CRS-C164

-- CRS-C012 / CRS-C166: pipe parent is also pipe
-- check_type: VALUE_MATCH, check_domain: tag
SELECT
  child.tag_name AS object_key,
  'parent_class_name' AS check_field,
  COALESCE(pc.name, 'NULL') AS actual_value,
  NOT (cc.name ILIKE '%pipe%' AND pc.name ILIKE '%pipe%') AS is_resolved
FROM project_core.tag child
LEFT JOIN project_core.tag parent ON parent.id = child.parent_tag_id
LEFT JOIN ontology_core.class cc ON cc.id = child.class_id
LEFT JOIN ontology_core.class pc ON pc.id = parent.class_id
WHERE child.object_status = 'Active'
  AND child.tag_name = ANY(:tag_names);
-- category: CRS-C012, CRS-C166

-- CRS-C013 / CRS-C171: safety critical item blank or invalid
-- check_type: VALUE_MATCH, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'safety_critical_item' AS check_field,
  COALESCE(t.safety_critical_item, 'NULL') AS actual_value,
  (t.safety_critical_item IS NOT NULL
    AND UPPER(TRIM(t.safety_critical_item)) IN ('YES','NO','Y','N')) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C013, CRS-C171

-- CRS-C014 / CRS-C174: safety critical reason missing (for SECE/YES tags)
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'safety_critical_item_reason_awarded' AS check_field,
  COALESCE(t.safety_critical_item_reason_awarded, 'NULL') AS actual_value,
  (UPPER(TRIM(COALESCE(t.safety_critical_item,''))) NOT IN ('YES','Y')
    OR (t.safety_critical_item_reason_awarded IS NOT NULL
        AND TRIM(t.safety_critical_item_reason_awarded) != '')) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C014, CRS-C174

-- CRS-C015 / CRS-C170: production critical item blank
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'production_critical_item' AS check_field,
  COALESCE(t.production_critical_item, 'NULL') AS actual_value,
  (t.production_critical_item IS NOT NULL
    AND TRIM(t.production_critical_item) != '') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C015, CRS-C170

-- CRS-C016: duplicate tags (AGGREGATE — no :tag_names param needed)
-- check_type: COUNT_ZERO, check_domain: tag
SELECT
  tag_name AS object_key,
  'tag_name_uniqueness' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.tag
WHERE object_status = 'Active'
GROUP BY tag_name
HAVING COUNT(*) > 1;
-- category: CRS-C016

-- CRS-C029 / CRS-C196: plant code invalid / prefix mismatch
-- check_type: FK_RESOLVED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'plant_id' AS check_field,
  COALESCE(pl.code, t.plant_raw, 'NULL') AS actual_value,
  (t.plant_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C029, CRS-C196

-- CRS-C041: EX class or IP grade missing (for instrument/E&I tags)
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'ex_class_ip_grade' AS check_field,
  CONCAT_WS('; ',
    CASE WHEN t.ex_class IS NULL THEN 'ex_class=NULL' END,
    CASE WHEN t.ip_grade IS NULL THEN 'ip_grade=NULL' END
  ) AS actual_value,
  (t.ex_class IS NOT NULL AND t.ip_grade IS NOT NULL) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C041

-- CRS-C042: MC package code missing
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'mc_package_code' AS check_field,
  COALESCE(t.mc_package_code, 'NULL') AS actual_value,
  (t.mc_package_code IS NOT NULL AND TRIM(t.mc_package_code) != '') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C042

-- CRS-C043 / CRS-C044: heat tracing / insulation type missing (tech_id field)
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'tech_id' AS check_field,
  COALESCE(t.tech_id, 'NULL') AS actual_value,
  (t.tech_id IS NOT NULL AND TRIM(t.tech_id) != '') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C043, CRS-C044

-- CRS-C050: circular parent hierarchy (AGGREGATE — no params)
-- check_type: COUNT_ZERO, check_domain: tag
-- FIX: added missing ) to close CTE before SELECT DISTINCT
WITH RECURSIVE tag_hierarchy AS (
  SELECT id, tag_name, parent_tag_id, 1 AS depth,
         ARRAY[id] AS path, FALSE AS is_cycle
  FROM project_core.tag
  WHERE object_status = 'Active' AND parent_tag_id IS NOT NULL
  UNION ALL
  SELECT t.id, t.tag_name, t.parent_tag_id, th.depth + 1,
         th.path || t.id, t.id = ANY(th.path)
  FROM project_core.tag t
  JOIN tag_hierarchy th ON t.id = th.parent_tag_id
  WHERE NOT th.is_cycle AND th.depth < 10
)
SELECT DISTINCT
  tag_name AS object_key,
  'parent_tag_cycle' AS check_field,
  depth::TEXT AS actual_value,
  FALSE AS is_resolved
FROM tag_hierarchy
WHERE is_cycle = TRUE;
-- category: CRS-C050

-- CRS-C142: abstract tag class used (is_abstract = true)
-- check_type: VALUE_MATCH, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'class_is_abstract' AS check_field,
  COALESCE(c.name || ' (abstract=' || c.is_abstract::TEXT || ')', 'NULL') AS actual_value,
  (c.is_abstract IS NULL OR c.is_abstract = FALSE) AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C142

-- CRS-C143: better alternative tag class available — DEFERRED
-- check_type: DEFERRED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'class_alternative' AS check_field,
  COALESCE(c.name, t.tag_class_raw, 'NULL') AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C143, check_type: DEFERRED

-- CRS-C144: comma instead of point in tag name
-- check_type: REGEX, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'tag_name_comma' AS check_field,
  t.tag_name AS actual_value,
  (t.tag_name NOT LIKE '%,%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C144

-- CRS-C145 / CRS-C146 / CRS-C147 / CRS-C148 / CRS-C149 / CRS-C152: company fields
-- check_type: FK_RESOLVED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'design_company' AS check_field,
  COALESCE(co.name, t.design_company_name_raw, 'NULL') AS actual_value,
  (t.design_company_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.design_company_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C145, CRS-C146, CRS-C147, CRS-C148, CRS-C149, CRS-C152

-- CRS-C150: control panel CP in TNC
-- check_type: REGEX, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'tag_name_cp_pattern' AS check_field,
  t.tag_name AS actual_value,
  (t.tag_name NOT SIMILAR TO '%-(CP|cp)-%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C150

-- CRS-C151 / CRS-C153 / CRS-C155 / CRS-C156 / CRS-C159 / CRS-C160 / CRS-C169: informational/process
-- check_type: DEFERRED
SELECT
  t.tag_name AS object_key,
  'no_check' AS check_field,
  'DEFERRED' AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C151, CRS-C153, CRS-C155, CRS-C156, CRS-C159, CRS-C160, CRS-C169, check_type: DEFERRED

-- CRS-C154 / CRS-C157 / CRS-C172 / CRS-C173: SECE classification — EXISTS check
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'sece_mapping' AS check_field,
  (SELECT STRING_AGG(s.code, '; ')
   FROM mapping.tag_sece ts
   JOIN reference_core.sece s ON s.id = ts.sece_id
   WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_sece ts
    WHERE ts.tag_id = t.id AND ts.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND UPPER(TRIM(COALESCE(t.safety_critical_item,''))) IN ('YES','Y')
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C154, CRS-C157, CRS-C172, CRS-C173

-- CRS-C158: multiple SECE groups — COUNT check
-- check_type: VALUE_MATCH, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'sece_count' AS check_field,
  COUNT(ts.id)::TEXT AS actual_value,
  (COUNT(ts.id) <= 1) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_sece ts ON ts.tag_id = t.id AND ts.mapping_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.tag_name;
-- category: CRS-C158

-- CRS-C161 / CRS-C162 / CRS-C165: parent tag advisory — DEFERRED
-- check_type: DEFERRED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'parent_advisory' AS check_field,
  COALESCE(p.tag_name, t.parent_tag_raw, 'NULL') AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag t
LEFT JOIN project_core.tag p ON p.id = t.parent_tag_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C161, CRS-C162, CRS-C165, check_type: DEFERRED

-- CRS-C167: pipe tag description missing from-to
-- check_type: REGEX, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'description_from_to' AS check_field,
  LEFT(COALESCE(t.description,''), 100) AS actual_value,
  (t.description ILIKE '%from%' OR t.description ILIKE '%to%'
   OR t.description ILIKE '%-%') AS is_resolved
FROM project_core.tag t
JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND c.name ILIKE '%pipe%'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C167

-- CRS-C168: PO code missing on tag
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'po_id' AS check_field,
  COALESCE(po.code, t.po_code_raw, 'NULL') AS actual_value,
  (t.po_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C168

-- CRS-C175: supplier company name not in register
-- check_type: FK_RESOLVED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'vendor_company' AS check_field,
  COALESCE(co.name, t.vendor_company_raw, 'NULL') AS actual_value,
  (t.vendor_id IS NOT NULL OR t.vendor_company_raw IS NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.vendor_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C175

-- CRS-C179: soft tag class on physical item — DEFERRED
-- check_type: DEFERRED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'class_concept' AS check_field,
  COALESCE(c.concept, 'NULL') AS actual_value,
  (c.concept ILIKE '%Physical%') AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C179, check_type: DEFERRED

-- CRS-C181 / CRS-C192: class vs description mismatch — SEMANTIC
-- check_type: SEMANTIC, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'class_description_match' AS check_field,
  CONCAT(COALESCE(c.name,'?'), ' | ', LEFT(COALESCE(t.description,''),80)) AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C181, CRS-C192, check_type: SEMANTIC

-- CRS-C183 / CRS-C189 / CRS-C191 / CRS-C194: description format issues
-- check_type: REGEX, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'description_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NOT NULL
    AND NOT TRIM(t.description) ~ '^-'
    AND NOT TRIM(t.description) ~ '-$'
    AND NOT t.description ILIKE '%, NA'
    AND t.tag_name NOT LIKE '%-') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C183, CRS-C189, CRS-C191, CRS-C194

-- CRS-C185: description has extra double spaces
-- check_type: REGEX, check_domain: tag
-- FIX: was NOT LIKE '% %' (single space) — corrected to double space detection
SELECT
  t.tag_name AS object_key,
  'description_spaces' AS check_field,
  LEFT(COALESCE(t.description,''), 80) AS actual_value,
  (t.description IS NULL OR t.description NOT LIKE '%  %') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C185

-- CRS-C186 / CRS-C187 / CRS-C188 / CRS-C190: semantic description issues
-- check_type: SEMANTIC, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'description_quality' AS check_field,
  LEFT(COALESCE(t.description,''), 255) AS actual_value,
  (t.description IS NOT NULL AND LENGTH(t.description) >= 20) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C186, CRS-C187, CRS-C188, CRS-C190, check_type: SEMANTIC

-- CRS-C193: tag is own parent
-- check_type: VALUE_MATCH, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'self_parent' AS check_field,
  COALESCE(t.parent_tag_raw, 'NULL') AS actual_value,
  (t.parent_tag_id IS NULL OR t.parent_tag_id != t.id) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C193

-- CRS-C195: tag number incomplete reference in description — SEMANTIC
-- check_type: SEMANTIC, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'description_tag_ref' AS check_field,
  LEFT(COALESCE(t.description,''), 100) AS actual_value,
  (t.description IS NULL
   OR t.description NOT SIMILAR TO '.*JDA-[A-Z0-9]+-[A-Z0-9]+.*') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C195

-- CRS-C200: tags not matched with doc-tag reference
-- check_type: NOT_NULL, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'doc_tag_mapping_exists' AS check_field,
  COALESCE(STRING_AGG(d.doc_number, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.tag_name;
-- category: CRS-C200

-- CRS-C201: TNC inconsistent with similar tags — DEFERRED
-- check_type: DEFERRED, check_domain: tag
SELECT
  t.tag_name AS object_key,
  'tnc_consistency' AS check_field,
  t.tag_name AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C201, check_type: DEFERRED

-- =============================================================================
-- DOMAIN: tag_property
-- =============================================================================

-- CRS-C017 / CRS-C221: property tag not in MTR (orphan property records)
-- check_type: FK_RESOLVED, check_domain: tag_property
SELECT
  pv.tag_name_raw AS object_key,
  'tag_exists_in_mtr' AS check_field,
  COALESCE(t.tag_name, 'NOT_IN_MTR') AS actual_value,
  (t.id IS NOT NULL AND t.object_status = 'Active') AS is_resolved
FROM project_core.property_value pv
LEFT JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C017, CRS-C221

-- CRS-C018 / CRS-C229: UOM present when property value is NA
-- check_type: VALUE_MATCH, check_domain: tag_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'uom_when_na' AS check_field,
  COALESCE(pv.property_value,'') || ' | ' || COALESCE(pv.property_uom_raw,'') AS actual_value,
  NOT (UPPER(TRIM(COALESCE(pv.property_value,''))) IN ('NA','N/A','')
       AND pv.property_uom_raw IS NOT NULL
       AND TRIM(pv.property_uom_raw) != '') AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C018, CRS-C229

-- CRS-C019 / CRS-C227: property value is zero
-- check_type: VALUE_MATCH, check_domain: tag_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'property_value_zero' AS check_field,
  COALESCE(pv.property_value,'NULL') AS actual_value,
  (TRIM(COALESCE(pv.property_value,'')) != '0') AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C019, CRS-C227

-- CRS-C020 / CRS-C223: property not in class scope / class mapping mismatch
-- check_type: FK_RESOLVED, check_domain: tag_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'property_in_class_scope' AS check_field,
  COALESCE(pv.property_code_raw,'NULL') AS actual_value,
  (pv.property_id IS NOT NULL AND pv.mapping_id IS NOT NULL) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C020, CRS-C223

-- CRS-C021 / CRS-C224: tag has no properties
-- check_type: COUNT_ZERO, check_domain: tag_property
SELECT
  t.tag_name AS object_key,
  'has_any_property' AS check_field,
  COUNT(pv.id)::TEXT AS actual_value,
  EXISTS (
    SELECT 1 FROM project_core.property_value pv2
    WHERE pv2.tag_id = t.id AND pv2.object_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN project_core.property_value pv ON pv.tag_id = t.id AND pv.object_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.tag_name;
-- category: CRS-C021, CRS-C224

-- CRS-C022 / CRS-C222: mandatory property missing (by ISM class_property mapping_presence)
-- check_type: NOT_NULL, check_domain: tag_property
SELECT
  t.tag_name || '.' || p.code AS object_key,
  'mandatory_property_present' AS check_field,
  COALESCE(pv.property_value, 'MISSING') AS actual_value,
  (pv.id IS NOT NULL AND pv.property_value IS NOT NULL
   AND TRIM(pv.property_value) != '') AS is_resolved
FROM project_core.tag t
JOIN ontology_core.class c ON c.id = t.class_id
JOIN ontology_core.class_property cp
  ON cp.class_id = c.id
  AND cp.mapping_presence = 'Mandatory'
  AND cp.mapping_status = 'Active'
JOIN ontology_core.property p ON p.id = cp.property_id
LEFT JOIN project_core.property_value pv
  ON pv.tag_id = t.id
  AND pv.property_code_raw = p.code
  AND pv.object_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C022, CRS-C222

-- CRS-C048: property UOM not in RDL (ontology_core.uom)
-- check_type: FK_RESOLVED, check_domain: tag_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'uom_in_rdl' AS check_field,
  COALESCE(pv.property_uom_raw, 'NULL') AS actual_value,
  (pv.property_uom_raw IS NULL
   OR EXISTS (
     SELECT 1 FROM ontology_core.uom u
     WHERE UPPER(u.code) = UPPER(pv.property_uom_raw)
        OR UPPER(u.symbol) = UPPER(pv.property_uom_raw)
   )) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names)
  AND pv.property_uom_raw IS NOT NULL
  AND pv.property_uom_raw != '';
-- category: CRS-C048

-- CRS-C215 / CRS-C218: format/encoding issues in property value
-- check_type: REGEX, check_domain: tag_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'property_value_format' AS check_field,
  COALESCE(pv.property_value,'NULL') AS actual_value,
  (pv.property_value IS NULL
   OR (pv.property_value NOT SIMILAR TO '.*[0-9]+G[0-9]+.*'
       AND pv.property_value NOT SIMILAR TO '.*\s{2,}.*')) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C215, CRS-C218

-- CRS-C216 / CRS-C219 / CRS-C220 / CRS-C225: structural/header issues — DEFERRED
-- check_type: DEFERRED, check_domain: tag_property
SELECT
  pv.tag_name_raw AS object_key,
  'structural' AS check_field,
  'DEFERRED' AS actual_value,
  TRUE AS is_resolved
FROM project_core.property_value pv
WHERE pv.tag_name_raw = ANY(:tag_names)
  AND pv.object_status = 'Active';
-- category: CRS-C216, CRS-C219, CRS-C220, CRS-C225, check_type: DEFERRED

-- CRS-C217: duplicate tag property entries (AGGREGATE)
-- check_type: COUNT_ZERO, check_domain: tag_property
SELECT
  tag_name_raw || '.' || property_code_raw AS object_key,
  'property_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.property_value
WHERE object_status = 'Active'
GROUP BY tag_name_raw, property_code_raw
HAVING COUNT(*) > 1;
-- category: CRS-C217

-- CRS-C226: property value blank
-- check_type: NOT_NULL, check_domain: tag_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'property_value_blank' AS check_field,
  COALESCE(pv.property_value, 'NULL') AS actual_value,
  (pv.property_value IS NOT NULL AND TRIM(pv.property_value) != '') AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C226

-- CRS-C228: UOM missing for numeric property value
-- check_type: NOT_NULL, check_domain: tag_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'uom_for_numeric' AS check_field,
  COALESCE(pv.property_uom_raw, 'NULL') AS actual_value,
  (pv.property_value IS NULL
   OR NOT pv.property_value ~ '^[0-9]'
   OR (pv.property_uom_raw IS NOT NULL AND TRIM(pv.property_uom_raw) != '')) AS is_resolved
FROM project_core.property_value pv
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C228

-- =============================================================================
-- DOMAIN: equipment
-- =============================================================================

-- CRS-C023 / CRS-C091 / CRS-C092: equipment class blank/not in ISM
-- check_type: FK_RESOLVED, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'equipment_class_id' AS check_field,
  COALESCE(c.name, t.tag_class_raw, 'NULL') AS actual_value,
  (t.class_id IS NOT NULL AND c.id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id AND c.object_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C023, CRS-C091, CRS-C092

-- CRS-C024 / CRS-C096: equipment description blank/missing
-- check_type: NOT_NULL, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'equipment_description' AS check_field,
  COALESCE(t.description, 'NULL') AS actual_value,
  (t.description IS NOT NULL AND TRIM(t.description) != '') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C024, CRS-C096

-- CRS-C025 / CRS-C110: manufacturer serial number blank
-- check_type: NOT_NULL, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'serial_no' AS check_field,
  COALESCE(t.serial_no, 'NULL') AS actual_value,
  (t.serial_no IS NOT NULL AND TRIM(t.serial_no) != ''
   AND UPPER(TRIM(t.serial_no)) != 'NA') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C025, CRS-C110

-- CRS-C026 / CRS-C126 / CRS-C127: model part missing/not defined
-- check_type: FK_RESOLVED, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'model_part_id' AS check_field,
  COALESCE(mp.name, t.model_part_raw, 'NULL') AS actual_value,
  (t.model_id IS NOT NULL AND mp.id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.model_part mp ON mp.id = t.model_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C026, CRS-C126, CRS-C127

-- CRS-C027 / CRS-C112: manufacturer company blank
-- check_type: NOT_NULL, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'manufacturer_company' AS check_field,
  COALESCE(co.name, t.manufacturer_company_raw, 'NULL') AS actual_value,
  (t.manufacturer_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.company co ON co.id = t.manufacturer_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C027, CRS-C112

-- CRS-C028 / CRS-C106: equipment tag not in MTR
-- check_type: FK_RESOLVED, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'tag_name_in_mtr' AS check_field,
  t.tag_name AS actual_value,
  (t.id IS NOT NULL AND t.object_status = 'Active') AS is_resolved
FROM project_core.tag t
WHERE t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C028, CRS-C106

-- CRS-C093: equipment class vs description mismatch — SEMANTIC
-- check_type: SEMANTIC, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'class_desc_match' AS check_field,
  CONCAT(COALESCE(c.name,'?'), ' | ', LEFT(COALESCE(t.description,''),80)) AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag t
LEFT JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.equip_no IS NOT NULL
  AND t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C093, check_type: SEMANTIC

-- CRS-C094: equipment description duplicated (AGGREGATE)
-- check_type: COUNT_ZERO, check_domain: equipment
SELECT
  t.description AS object_key,
  'description_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.description IS NOT NULL
  AND t.description != ''
GROUP BY t.description
HAVING COUNT(*) > 1;
-- category: CRS-C094

-- CRS-C095 / CRS-C098: description starts/ends with dash
-- check_type: REGEX, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'description_dash_format' AS check_field,
  LEFT(COALESCE(t.description,''), 50) AS actual_value,
  (t.description IS NULL
   OR (NOT TRIM(t.description) ~ '^-' AND NOT TRIM(t.description) ~ '-$')) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C095, CRS-C098

-- CRS-C097 / CRS-C099 / CRS-C102 / CRS-C104 / CRS-C108 / CRS-C109: process/admin — DEFERRED
-- check_type: DEFERRED, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'equip_admin' AS check_field,
  'DEFERRED' AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C097, CRS-C099, CRS-C102, CRS-C104, CRS-C108, CRS-C109, check_type: DEFERRED

-- CRS-C100: equipment has no document references
-- check_type: NOT_NULL, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'equip_doc_mapping' AS check_field,
  COALESCE(STRING_AGG(d.doc_number, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.equip_no;
-- category: CRS-C100

-- CRS-C101: equipment is own parent
-- check_type: VALUE_MATCH, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'self_parent_equip' AS check_field,
  COALESCE(t.parent_tag_raw, 'NULL') AS actual_value,
  (t.parent_tag_id IS NULL OR t.parent_tag_id != t.id) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C101

-- CRS-C103: equipment number missing plant code prefix
-- check_type: REGEX, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'equip_no_prefix' AS check_field,
  COALESCE(t.equip_no, 'NULL') AS actual_value,
  (t.equip_no LIKE 'Equip_%' OR t.equip_no LIKE 'JDA%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C103

-- CRS-C105: equipment plant code not in register
-- check_type: FK_RESOLVED, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'plant_id_equip' AS check_field,
  COALESCE(pl.code, t.plant_raw, 'NULL') AS actual_value,
  (t.plant_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.plant pl ON pl.id = t.plant_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C105

-- CRS-C107: equipment TNC non-compliance
-- check_type: REGEX, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'equip_no_tnc' AS check_field,
  COALESCE(t.equip_no, 'NULL') AS actual_value,
  (t.equip_no LIKE 'Equip_JDA-%') AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C107

-- CRS-C111: manufacturer serial number is NA
-- check_type: VALUE_MATCH, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'serial_no_not_na' AS check_field,
  COALESCE(t.serial_no, 'NULL') AS actual_value,
  (t.serial_no IS NULL
   OR UPPER(TRIM(t.serial_no)) NOT IN ('NA','N/A','NOT APPLICABLE')) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C111

-- CRS-C113: model part name missing
-- check_type: FK_RESOLVED, check_domain: equipment
SELECT
  t.equip_no AS object_key,
  'model_part' AS check_field,
  COALESCE(mp.name, t.model_part_raw, 'NULL') AS actual_value,
  (t.model_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.model_part mp ON mp.id = t.model_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C113

-- =============================================================================
-- DOMAIN: equipment_property
-- =============================================================================

-- CRS-C115: duplicate equipment property entries (AGGREGATE)
-- check_type: COUNT_ZERO, check_domain: equipment_property
SELECT
  tag_name_raw || '.' || property_code_raw AS object_key,
  'equip_property_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.property_value
WHERE object_status = 'Active'
  AND tag_name_raw = ANY(:tag_names)
GROUP BY tag_name_raw, property_code_raw
HAVING COUNT(*) > 1;
-- category: CRS-C115

-- CRS-C116 / CRS-C123: equipment class-property mapping mismatch
-- check_type: FK_RESOLVED, check_domain: equipment_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'equip_property_class_scope' AS check_field,
  COALESCE(pv.property_code_raw,'NULL') AS actual_value,
  (pv.property_id IS NOT NULL AND pv.mapping_id IS NOT NULL) AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C116, CRS-C123

-- CRS-C117: equipment has no properties
-- check_type: COUNT_ZERO, check_domain: equipment_property
SELECT
  t.equip_no AS object_key,
  'equip_has_properties' AS check_field,
  COUNT(pv.id)::TEXT AS actual_value,
  EXISTS (
    SELECT 1 FROM project_core.property_value pv2
    WHERE pv2.tag_id = t.id AND pv2.object_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN project_core.property_value pv ON pv.tag_id = t.id AND pv.object_status = 'Active'
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.equip_no;
-- category: CRS-C117

-- CRS-C118 / CRS-C119: property register orphan
-- check_type: FK_RESOLVED, check_domain: equipment_property
SELECT
  pv.tag_name_raw AS object_key,
  'equip_in_register' AS check_field,
  COALESCE(t.equip_no, 'NOT_IN_REGISTER') AS actual_value,
  (t.id IS NOT NULL AND t.equip_no IS NOT NULL) AS is_resolved
FROM project_core.property_value pv
LEFT JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C118, CRS-C119

-- CRS-C120 / CRS-C125: structural/header issues — DEFERRED
-- check_type: DEFERRED, check_domain: equipment_property
SELECT
  pv.tag_name_raw AS object_key,
  'structural' AS check_field,
  'DEFERRED' AS actual_value,
  TRUE AS is_resolved
FROM project_core.property_value pv
WHERE pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C120, CRS-C125, check_type: DEFERRED

-- CRS-C121 / CRS-C122 / CRS-C124: equipment property value issues
-- check_type: VALUE_MATCH, check_domain: equipment_property
SELECT
  pv.tag_name_raw || '.' || pv.property_code_raw AS object_key,
  'equip_property_value' AS check_field,
  COALESCE(pv.property_value,'NULL') || ' | ' || COALESCE(pv.property_uom_raw,'') AS actual_value,
  (pv.property_value IS NOT NULL
   AND TRIM(pv.property_value) != ''
   AND TRIM(COALESCE(pv.property_value,'')) != '0'
   AND NOT (UPPER(TRIM(COALESCE(pv.property_value,''))) IN ('NA','N/A')
            AND pv.property_uom_raw IS NOT NULL
            AND TRIM(pv.property_uom_raw) != '')) AS is_resolved
FROM project_core.property_value pv
JOIN project_core.tag t ON t.tag_name = pv.tag_name_raw AND t.object_status = 'Active'
WHERE pv.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND pv.tag_name_raw = ANY(:tag_names);
-- category: CRS-C121, CRS-C122, CRS-C124

-- =============================================================================
-- DOMAIN: document
-- =============================================================================

-- CRS-C030 / CRS-C077 / CRS-C078: document missing or NYI/CAN status
-- check_type: VALUE_MATCH, check_domain: document
-- param: :doc_numbers
SELECT
  d.doc_number AS object_key,
  'document_status' AS check_field,
  COALESCE(d.status, 'NULL') AS actual_value,
  (d.id IS NOT NULL
   AND d.object_status = 'Active'
   AND d.status IS NOT NULL
   AND UPPER(TRIM(d.status)) NOT IN ('NYI','CAN')) AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
-- category: CRS-C030, CRS-C077, CRS-C078

-- CRS-C031 / CRS-C086: tag has no document reference
-- check_type: NOT_NULL, check_domain: document
SELECT
  t.tag_name AS object_key,
  'doc_tag_link' AS check_field,
  COALESCE(STRING_AGG(d.doc_number, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.tag_name;
-- category: CRS-C031, CRS-C086

-- CRS-C032 / CRS-C074: document in mapping not in DocMaster
-- check_type: FK_RESOLVED, check_domain: document
SELECT
  td.doc_number_raw AS object_key,
  'doc_in_docmaster' AS check_field,
  COALESCE(d.doc_number, 'NOT_IN_DOCMASTER') AS actual_value,
  (d.id IS NOT NULL AND d.object_status = 'Active') AS is_resolved
FROM mapping.tag_document td
LEFT JOIN project_core.document d ON d.doc_number = td.doc_number_raw
WHERE td.mapping_status = 'Active'
  AND td.doc_number_raw = ANY(:doc_numbers);
-- category: CRS-C032, CRS-C074

-- CRS-C033 / CRS-C075: tag in mapping not in MTR
-- check_type: FK_RESOLVED, check_domain: document
SELECT
  td.tag_name_raw AS object_key,
  'tag_in_mtr' AS check_field,
  COALESCE(t.tag_name, 'NOT_IN_MTR') AS actual_value,
  (t.id IS NOT NULL AND t.object_status = 'Active') AS is_resolved
FROM mapping.tag_document td
LEFT JOIN project_core.tag t ON t.tag_name = td.tag_name_raw AND t.object_status = 'Active'
WHERE td.mapping_status = 'Active'
  AND td.tag_name_raw = ANY(:tag_names);
-- category: CRS-C033, CRS-C075

-- CRS-C034 / CRS-C060: document area code missing
-- check_type: NOT_NULL, check_domain: document
SELECT
  d.doc_number AS object_key,
  'doc_area_code' AS check_field,
  COALESCE(STRING_AGG(DISTINCT a.code, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td2
    JOIN project_core.tag t2 ON t2.id = td2.tag_id AND t2.area_id IS NOT NULL
    WHERE td2.document_id = d.id AND td2.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.document d
LEFT JOIN mapping.tag_document td ON td.document_id = d.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.tag t ON t.id = td.tag_id
LEFT JOIN reference_core.area a ON a.id = t.area_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers)
GROUP BY d.id, d.doc_number;
-- category: CRS-C034, CRS-C060

-- CRS-C035 / CRS-C071: document process unit missing
-- check_type: NOT_NULL, check_domain: document
SELECT
  d.doc_number AS object_key,
  'doc_process_unit' AS check_field,
  COALESCE(STRING_AGG(DISTINCT pu.code, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td2
    JOIN project_core.tag t2 ON t2.id = td2.tag_id AND t2.process_unit_id IS NOT NULL
    WHERE td2.document_id = d.id AND td2.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.document d
LEFT JOIN mapping.tag_document td ON td.document_id = d.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.tag t ON t.id = td.tag_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers)
GROUP BY d.id, d.doc_number;
-- category: CRS-C035, CRS-C071

-- CRS-C040 / CRS-C062 / CRS-C080: equipment has no document mapping
-- check_type: NOT_NULL, check_domain: document
SELECT
  t.equip_no AS object_key,
  'equip_doc_mapping' AS check_field,
  COALESCE(STRING_AGG(d.doc_number, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    WHERE td.tag_id = t.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.equip_no;
-- category: CRS-C040, CRS-C062, CRS-C080

-- CRS-C046: tag linked to inactive document
-- check_type: VALUE_MATCH, check_domain: document
SELECT
  t.tag_name AS object_key,
  'doc_is_active' AS check_field,
  COALESCE(STRING_AGG(d.status, '; '), 'NULL') AS actual_value,
  NOT EXISTS (
    SELECT 1 FROM mapping.tag_document td
    JOIN project_core.document d2 ON d2.id = td.document_id
    WHERE td.tag_id = t.id
      AND td.mapping_status = 'Active'
      AND d2.object_status != 'Active'
  ) AS is_resolved
FROM project_core.tag t
LEFT JOIN mapping.tag_document td ON td.tag_id = t.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.document d ON d.id = td.document_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.id, t.tag_name;
-- category: CRS-C046

-- CRS-C057: informational — DEFERRED
-- check_type: DEFERRED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'doc_info' AS check_field,
  'DEFERRED' AS actual_value,
  TRUE AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
-- category: CRS-C057, check_type: DEFERRED

-- CRS-C058: company name in doc-PO not in company register
-- check_type: FK_RESOLVED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'po_company_in_register' AS check_field,
  COALESCE(co.name, 'NOT_IN_REGISTER') AS actual_value,
  (co.id IS NOT NULL) AS is_resolved
FROM project_core.document d
JOIN mapping.document_po dpo ON dpo.document_id = d.id AND dpo.mapping_status = 'Active'
JOIN reference_core.purchase_order po ON po.id = dpo.po_id
LEFT JOIN reference_core.company co ON co.id = po.issuer_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers);
-- category: CRS-C058

-- CRS-C059 / CRS-C061 / CRS-C065 / CRS-C067 / CRS-C068 / CRS-C073: doc cross-ref checks
-- check_type: FK_RESOLVED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'doc_in_docmaster' AS check_field,
  d.doc_number AS actual_value,
  (d.object_status = 'Active') AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
-- category: CRS-C059, CRS-C061, CRS-C065, CRS-C067, CRS-C068, CRS-C073

-- CRS-C063 / CRS-C064 / CRS-C072 / CRS-C076: doc mismatch with external DMS — DEFERRED
-- check_type: DEFERRED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'dms_match' AS check_field,
  d.doc_number AS actual_value,
  TRUE AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
-- category: CRS-C063, CRS-C064, CRS-C072, CRS-C076, check_type: DEFERRED

-- CRS-C066 / CRS-C087: PO code in doc-PO not in PO register / is void
-- check_type: FK_RESOLVED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'doc_po_link' AS check_field,
  COALESCE(STRING_AGG(po.code, '; '), 'NULL') AS actual_value,
  NOT EXISTS (
    SELECT 1 FROM mapping.document_po dpo
    JOIN reference_core.purchase_order po2 ON po2.id = dpo.po_id
    WHERE dpo.document_id = d.id
      AND dpo.mapping_status = 'Active'
      AND (po2.id IS NULL OR po2.object_status != 'Active')
  ) AS is_resolved
FROM project_core.document d
LEFT JOIN mapping.document_po dpo ON dpo.document_id = d.id AND dpo.mapping_status = 'Active'
LEFT JOIN reference_core.purchase_order po ON po.id = dpo.po_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers)
GROUP BY d.id, d.doc_number;
-- category: CRS-C066, CRS-C087

-- CRS-C069: doc plant code not in register
-- check_type: FK_RESOLVED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'doc_plant_id' AS check_field,
  COALESCE(pl.code, 'NULL') AS actual_value,
  (d.plant_id IS NOT NULL) AS is_resolved
FROM project_core.document d
LEFT JOIN reference_core.plant pl ON pl.id = d.plant_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers);
-- category: CRS-C069

-- CRS-C070: doc process unit not in register
-- check_type: FK_RESOLVED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'doc_pu_in_register' AS check_field,
  COALESCE(STRING_AGG(DISTINCT pu.code, '; '), 'NULL') AS actual_value,
  EXISTS (
    SELECT 1 FROM mapping.tag_document td
    JOIN project_core.tag t ON t.id = td.tag_id
    JOIN reference_core.process_unit pu2 ON pu2.id = t.process_unit_id
    WHERE td.document_id = d.id AND td.mapping_status = 'Active'
  ) AS is_resolved
FROM project_core.document d
LEFT JOIN mapping.tag_document td ON td.document_id = d.id AND td.mapping_status = 'Active'
LEFT JOIN project_core.tag t ON t.id = td.tag_id
LEFT JOIN reference_core.process_unit pu ON pu.id = t.process_unit_id
WHERE d.object_status = 'Active'
  AND d.doc_number = ANY(:doc_numbers)
GROUP BY d.id, d.doc_number;
-- category: CRS-C070

-- CRS-C079: duplicate document records (AGGREGATE)
-- check_type: COUNT_ZERO, check_domain: document
SELECT
  doc_number AS object_key,
  'doc_number_unique' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.document
WHERE object_status = 'Active'
GROUP BY doc_number
HAVING COUNT(*) > 1;
-- category: CRS-C079

-- CRS-C081 / CRS-C082 / CRS-C083 / CRS-C084 / CRS-C085 / CRS-C088 / CRS-C089 / CRS-C090:
-- External DMS / process issues — DEFERRED
-- check_type: DEFERRED, check_domain: document
SELECT
  d.doc_number AS object_key,
  'external_dms' AS check_field,
  'DEFERRED' AS actual_value,
  TRUE AS is_resolved
FROM project_core.document d
WHERE d.doc_number = ANY(:doc_numbers);
-- category: CRS-C081, CRS-C082, CRS-C083, CRS-C084, CRS-C085, CRS-C088, CRS-C089, CRS-C090, check_type: DEFERRED

-- =============================================================================
-- DOMAIN: purchase_order
-- =============================================================================

-- CRS-C036 / CRS-C138: PO code not in register
-- check_type: FK_RESOLVED, check_domain: purchase_order
SELECT
  t.tag_name AS object_key,
  'po_code_in_register' AS check_field,
  COALESCE(po.code, t.po_code_raw, 'NULL') AS actual_value,
  (t.po_id IS NOT NULL AND po.id IS NOT NULL
   AND po.object_status = 'Active') AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C036, CRS-C138

-- CRS-C037 / CRS-C139: PO date missing
-- check_type: NOT_NULL, check_domain: purchase_order
-- NOTE: :po_codes param — передавать коды PO, не tag_names
SELECT
  po.code AS object_key,
  'po_date' AS check_field,
  COALESCE(po.po_date, 'NULL') AS actual_value,
  (po.po_date IS NOT NULL AND TRIM(po.po_date) != '') AS is_resolved
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active'
  AND po.code = ANY(:po_codes);
-- category: CRS-C037, CRS-C139

-- CRS-C038 / CRS-C141: company name missing for PO / receiver company missing
-- check_type: FK_RESOLVED, check_domain: purchase_order
-- NOTE: :po_codes param — передавать коды PO, не tag_names
SELECT
  po.code AS object_key,
  'po_company' AS check_field,
  COALESCE(co.name, 'NULL') AS actual_value,
  (po.issuer_id IS NOT NULL AND co.id IS NOT NULL) AS is_resolved
FROM reference_core.purchase_order po
LEFT JOIN reference_core.company co ON co.id = po.issuer_id
WHERE po.object_status = 'Active'
  AND po.code = ANY(:po_codes);
-- category: CRS-C038, CRS-C141

-- CRS-C135: multiple PO codes for same equipment
-- check_type: COUNT_ZERO, check_domain: purchase_order
SELECT
  t.equip_no AS object_key,
  'po_count_per_equip' AS check_field,
  COUNT(DISTINCT t.po_id)::TEXT AS actual_value,
  (COUNT(DISTINCT t.po_id) <= 1) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
  AND t.tag_name = ANY(:tag_names)
GROUP BY t.equip_no;
-- category: CRS-C135

-- CRS-C136: PO code is void
-- check_type: VALUE_MATCH, check_domain: purchase_order
SELECT
  t.tag_name AS object_key,
  'po_not_void' AS check_field,
  COALESCE(t.po_code_raw, po.code, 'NULL') AS actual_value,
  (t.po_code_raw IS NULL
   OR (t.po_code_raw NOT ILIKE '%-VOID%'
       AND t.po_code_raw NOT ILIKE '%VOID-%')) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C136

-- CRS-C137: PO code missing for physical tags
-- check_type: NOT_NULL, check_domain: purchase_order
SELECT
  t.tag_name AS object_key,
  'po_for_physical_tag' AS check_field,
  COALESCE(po.code, t.po_code_raw, 'NULL') AS actual_value,
  (t.po_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
LEFT JOIN reference_core.purchase_order po ON po.id = t.po_id
JOIN ontology_core.class c ON c.id = t.class_id
WHERE t.object_status = 'Active'
  AND c.concept ILIKE '%Physical%'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C137

-- CRS-C140: PO description contains invalid characters
-- check_type: REGEX, check_domain: purchase_order
-- NOTE: :po_codes param — передавать коды PO, не tag_names
SELECT
  po.code AS object_key,
  'po_name_characters' AS check_field,
  COALESCE(po.name, 'NULL') AS actual_value,
  (po.name IS NULL
   OR (po.name NOT LIKE '%,%' AND po.name NOT LIKE '%""%')) AS is_resolved
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active'
  AND po.code = ANY(:po_codes);
-- category: CRS-C140

-- =============================================================================
-- DOMAIN: area
-- =============================================================================

-- CRS-C053 / CRS-C055 / CRS-C056: area mandatory data / hierarchy — DEFERRED
-- check_type: DEFERRED, check_domain: area
SELECT
  code AS object_key,
  'area_data' AS check_field,
  code AS actual_value,
  TRUE AS is_resolved
FROM reference_core.area
WHERE code = ANY(:tag_names);
-- category: CRS-C053, CRS-C055, CRS-C056, check_type: DEFERRED

-- CRS-C054: area name spelling error — SEMANTIC
-- check_type: SEMANTIC, check_domain: area
SELECT
  code AS object_key,
  'area_name' AS check_field,
  COALESCE(name, 'NULL') AS actual_value,
  (name IS NOT NULL AND TRIM(name) != '') AS is_resolved
FROM reference_core.area
WHERE code = ANY(:tag_names);
-- category: CRS-C054, check_type: SEMANTIC

-- =============================================================================
-- DOMAIN: process_unit
-- =============================================================================

-- CRS-C129: multiple PU codes for same system — DEFERRED
-- check_type: DEFERRED, check_domain: process_unit
SELECT
  code AS object_key,
  'pu_uniqueness' AS check_field,
  code AS actual_value,
  TRUE AS is_resolved
FROM reference_core.process_unit
WHERE code = ANY(:tag_names);
-- category: CRS-C129, check_type: DEFERRED

-- CRS-C130: process unit description blank
-- check_type: NOT_NULL, check_domain: process_unit
SELECT
  pu.code AS object_key,
  'pu_name' AS check_field,
  COALESCE(pu.name, 'NULL') AS actual_value,
  (pu.name IS NOT NULL AND TRIM(pu.name) != '') AS is_resolved
FROM reference_core.process_unit pu
WHERE pu.object_status = 'Active'
  AND pu.code = ANY(:tag_names);
-- category: CRS-C130

-- CRS-C131 / CRS-C133: formatting / mandatory data — DEFERRED
-- check_type: DEFERRED, check_domain: process_unit
SELECT
  code AS object_key,
  'pu_data' AS check_field,
  COALESCE(name, 'NULL') AS actual_value,
  TRUE AS is_resolved
FROM reference_core.process_unit
WHERE code = ANY(:tag_names);
-- category: CRS-C131, CRS-C133, check_type: DEFERRED

-- CRS-C132: PU hierarchy inconsistent with area / plant
-- check_type: FK_RESOLVED, check_domain: process_unit
SELECT
  pu.code AS object_key,
  'pu_plant_match' AS check_field,
  COALESCE(pl.code, 'NULL') AS actual_value,
  (pu.plant_id IS NOT NULL AND pl.id IS NOT NULL) AS is_resolved
FROM reference_core.process_unit pu
LEFT JOIN reference_core.plant pl ON pl.id = pu.plant_id
WHERE pu.object_status = 'Active'
  AND pu.code = ANY(:tag_names);
-- category: CRS-C132

-- CRS-C134: PU plant code not in standard list
-- check_type: FK_RESOLVED, check_domain: process_unit
SELECT
  pu.code AS object_key,
  'pu_plant_in_register' AS check_field,
  COALESCE(pl.code, 'NULL') AS actual_value,
  (pu.plant_id IS NOT NULL) AS is_resolved
FROM reference_core.process_unit pu
LEFT JOIN reference_core.plant pl ON pl.id = pu.plant_id
WHERE pu.object_status = 'Active'
  AND pu.code = ANY(:tag_names);
-- category: CRS-C134

-- =============================================================================
-- DOMAIN: tag_connection
-- =============================================================================

-- CRS-C039 / CRS-C206: duplicate physical connection entries (AGGREGATE)
-- check_type: COUNT_ZERO, check_domain: tag_connection
SELECT
  from_tag_raw || '->' || to_tag_raw AS object_key,
  'connection_duplicate' AS check_field,
  COUNT(*)::TEXT AS actual_value,
  (COUNT(*) = 1) AS is_resolved
FROM project_core.tag
WHERE object_status = 'Active'
  AND from_tag_raw IS NOT NULL
  AND to_tag_raw IS NOT NULL
GROUP BY from_tag_raw, to_tag_raw
HAVING COUNT(*) > 1;
-- category: CRS-C039, CRS-C206

-- CRS-C045 / CRS-C208: from_tag not in MTR
-- check_type: FK_RESOLVED, check_domain: tag_connection
SELECT
  t.tag_name AS object_key,
  'from_tag_in_mtr' AS check_field,
  COALESCE(t.from_tag_raw, 'NULL') AS actual_value,
  (t.from_tag_raw IS NULL
   OR t.from_tag_raw = ''
   OR t.from_tag_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.from_tag_raw IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C045, CRS-C208

-- CRS-C207: from_tag equals to_tag (self-loop)
-- check_type: VALUE_MATCH, check_domain: tag_connection
SELECT
  t.tag_name AS object_key,
  'from_to_not_equal' AS check_field,
  COALESCE(t.from_tag_raw,'') || '->' || COALESCE(t.to_tag_raw,'') AS actual_value,
  (t.from_tag_raw IS NULL
   OR t.to_tag_raw IS NULL
   OR t.from_tag_raw != t.to_tag_raw) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C207

-- CRS-C213: to_tag not in MTR
-- check_type: FK_RESOLVED, check_domain: tag_connection
SELECT
  t.tag_name AS object_key,
  'to_tag_in_mtr' AS check_field,
  COALESCE(t.to_tag_raw, 'NULL') AS actual_value,
  (t.to_tag_raw IS NULL
   OR t.to_tag_raw = ''
   OR t.to_tag_id IS NOT NULL) AS is_resolved
FROM project_core.tag t
WHERE t.object_status = 'Active'
  AND t.to_tag_raw IS NOT NULL
  AND t.tag_name = ANY(:tag_names);
-- category: CRS-C213

-- CRS-C209 / CRS-C210 / CRS-C211 / CRS-C212 / CRS-C214: connection info/process — DEFERRED
-- check_type: DEFERRED, check_domain: tag_connection
SELECT
  tag_name AS object_key,
  'connection_info' AS check_field,
  'DEFERRED' AS actual_value,
  TRUE AS is_resolved
FROM project_core.tag
WHERE object_status = 'Active'
  AND tag_name = ANY(:tag_names);
-- category: CRS-C209, CRS-C210, CRS-C211, CRS-C212, CRS-C214, check_type: DEFERRED

-- =============================================================================
-- DOMAIN: model_part
-- =============================================================================

-- CRS-C128: model part number invalid characters
-- check_type: REGEX, check_domain: model_part
SELECT
  mp.code AS object_key,
  'model_part_code_chars' AS check_field,
  mp.code AS actual_value,
  (mp.code NOT SIMILAR TO '.*[<>=&"''%].*') AS is_resolved
FROM reference_core.model_part mp
WHERE mp.object_status = 'Active'
  AND mp.code = ANY(:tag_names);
-- category: CRS-C128

-- =============================================================================
-- DOMAIN: tag_class_property (ISM coverage)
-- =============================================================================

-- CRS-C203 / CRS-C204 / CRS-C205: tag class properties ISM coverage
-- check_type: NOT_NULL, check_domain: tag_class_property
SELECT
  c.name AS object_key,
  'class_property_coverage' AS check_field,
  COUNT(cp.id)::TEXT AS actual_value,
  (COUNT(cp.id) > 0) AS is_resolved
FROM ontology_core.class c
LEFT JOIN ontology_core.class_property cp
  ON cp.class_id = c.id AND cp.mapping_status = 'Active'
WHERE c.object_status = 'Active'
  AND c.name = ANY(:tag_names)
GROUP BY c.id, c.name;
-- category: CRS-C203, CRS-C204, CRS-C205

-- =============================================================================
-- NOT COVERED IN REFERENCE FILE (требуют уточнения из crs_comment_template):
-- CRS-C047, CRS-C049, CRS-C114
-- Не найдены ни в оригинальном файле, ни в schema.sql.
-- Claude Code должен проверить их наличие в audit_core.crs_comment_template
-- и запросить описание у аналитика если они существуют.
-- =============================================================================