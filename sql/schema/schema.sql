-- ===========================================================================
-- Jackdaw EDW - Canonical Database Schema
-- Database: engineering_core
-- Last Updated: 2026-04-09 (from live DB via MCP)
-- ===========================================================================
-- This is the single source of truth for database structure.
-- All migrations must update this file in the same commit.
-- Never add columns/tables here without also creating a migration file.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- Schema: app_core
-- Purpose: Jackdaw EDW UI user management and feedback system
-- ---------------------------------------------------------------------------

-- ui_user: Jackdaw EDW UI users with bcrypt passwords and role-based access.
CREATE TABLE "app_core"."ui_user" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "username" TEXT NOT NULL,
  "password_hash" TEXT NOT NULL, -- bcrypt hash (rounds=12). Never store plaintext.
  "role" TEXT NOT NULL DEFAULT 'viewer', -- viewer = read-only pages; admin = full access incl. ETL/EIS.
  "is_active" BOOLEAN NOT NULL DEFAULT true,
  "last_login" TIMESTAMP WITH TIME ZONE,
  "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  CONSTRAINT "ui_user_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "ui_user_username_key" UNIQUE ("username")
);

-- ui_feedback: User-submitted feedback and enhancement requests from the UI.
CREATE TABLE "app_core"."ui_feedback" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "title" TEXT NOT NULL,
  "body" TEXT NOT NULL,
  "feedback_type" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'Open',
  "username" TEXT,
  "user_id" UUID,
  "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  CONSTRAINT "ui_feedback_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "ui_feedback_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "app_core"."ui_user" ("id")
);

-- ---------------------------------------------------------------------------
-- Schema: audit_core
-- Purpose: Audit trail, validation results, and ETL run statistics
-- ---------------------------------------------------------------------------

-- sync_run_stats: ETL run statistics and audit log entries.
CREATE TABLE "audit_core"."sync_run_stats" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "run_id" UUID NOT NULL,
  "target_table" TEXT NOT NULL,
  "start_time" TIMESTAMP NOT NULL,
  "end_time" TIMESTAMP,
  "source_file" TEXT,
  "count_created" INTEGER DEFAULT 0,
  "count_updated" INTEGER DEFAULT 0,
  "count_unchanged" INTEGER DEFAULT 0,
  "count_deleted" INTEGER DEFAULT 0,
  "count_errors" INTEGER DEFAULT 0,
  "count_exported" INTEGER NOT NULL DEFAULT 0, -- Number of rows written to the EIS export CSV file. Set by export_pipeline._log_audit_end().
  "mapping_status" TEXT DEFAULT 'Active',
  CONSTRAINT "sync_run_stats_pkey" PRIMARY KEY ("id")
);

-- tag_status_history: SCD Type 2 change tracking for tag records.
CREATE TABLE "audit_core"."tag_status_history" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "tag_id" UUID NOT NULL,
  "tag_name" TEXT NOT NULL,
  "source_id" TEXT NOT NULL,
  "sync_status" TEXT NOT NULL,
  "row_hash" TEXT,
  "snapshot" JSONB,
  "run_id" UUID,
  "sync_timestamp" TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT "tag_status_history_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "tag_status_history_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id")
);

-- export_validation_rule: Configurable validation rules for EIS export quality checks.
CREATE TABLE "audit_core"."export_validation_rule" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "rule_code" TEXT NOT NULL,
  "scope" TEXT NOT NULL,
  "object_field" TEXT,
  "description" TEXT,
  "rule_expression" TEXT NOT NULL,
  "fix_expression" TEXT,
  "is_builtin" BOOLEAN NOT NULL DEFAULT false,
  "is_blocking" BOOLEAN NOT NULL DEFAULT false,
  "severity" TEXT NOT NULL DEFAULT 'Warning',
  "object_status" TEXT NOT NULL DEFAULT 'Active',
  "tier" TEXT,
  "category" TEXT,
  "source_ref" TEXT,
  "check_type" TEXT NOT NULL DEFAULT 'dsl',
  "sort_order" INTEGER,
  CONSTRAINT "export_validation_rule_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "export_validation_rule_code_key" UNIQUE ("rule_code")
);

-- validation_result: Violation records from full-scan validation runs.
CREATE TABLE "audit_core"."validation_result" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "session_id" UUID NOT NULL,
  "run_time" TIMESTAMP NOT NULL DEFAULT now(),
  "rule_code" TEXT NOT NULL,
  "scope" TEXT NOT NULL,
  "severity" TEXT NOT NULL DEFAULT 'Warning',
  "object_type" TEXT,
  "object_id" UUID,
  "object_name" TEXT,
  "violation_detail" TEXT,
  "column_name" TEXT,
  "original_value" TEXT,
  "is_resolved" BOOLEAN NOT NULL DEFAULT false,
  "tier" TEXT,
  "category" TEXT,
  "check_type" TEXT,
  CONSTRAINT "validation_result_pkey" PRIMARY KEY ("id")
);

-- report_metadata: Dynamic SQL report catalogue for EDW Control Center.
CREATE TABLE "audit_core"."report_metadata" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "report_name" TEXT NOT NULL,
  "sql_query" TEXT NOT NULL,
  "category" TEXT NOT NULL DEFAULT 'General',
  "description" TEXT,
  "is_active" BOOLEAN NOT NULL DEFAULT true,
  "is_parametric" BOOLEAN NOT NULL DEFAULT false, -- True if sql_query contains :param placeholders. UI will render input widgets before execution.
  "author" TEXT DEFAULT 'system',
  "created_at" TIMESTAMP NOT NULL DEFAULT now(),
  "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT "report_metadata_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "report_metadata_report_name_key" UNIQUE ("report_name")
);

-- ---------------------------------------------------------------------------
-- Schema: mapping
-- Purpose: Many-to-many relationship tables
-- ---------------------------------------------------------------------------

-- tag_document: Tag to document cross-reference mapping.
CREATE TABLE "mapping"."tag_document" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "tag_id" UUID,
  "document_id" UUID,
  "tag_name_raw" TEXT,
  "doc_number_raw" TEXT,
  "row_hash" TEXT,
  "sync_status" TEXT DEFAULT 'Active',
  "sync_timestamp" TIMESTAMP DEFAULT now(),
  "mapping_status" TEXT DEFAULT 'Active',
  CONSTRAINT "tag_document_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "tag_document_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id"),
  CONSTRAINT "tag_document_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "project_core"."document" ("id")
);

-- tag_sece: Tag to Safety/Environment/Criticality/Equipment (SECE) code mapping.
CREATE TABLE "mapping"."tag_sece" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "tag_id" UUID,
  "sece_id" UUID,
  "row_hash" TEXT,
  "sync_status" TEXT DEFAULT 'Active',
  "sync_timestamp" TIMESTAMP DEFAULT now(),
  "mapping_status" TEXT DEFAULT 'Active',
  CONSTRAINT "tag_sece_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "tag_sece_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id"),
  CONSTRAINT "tag_sece_sece_id_fkey" FOREIGN KEY ("sece_id") REFERENCES "reference_core"."sece" ("id")
);

-- document_po: Document to purchase order cross-reference mapping.
CREATE TABLE "mapping"."document_po" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "document_id" UUID,
  "po_id" UUID,
  "row_hash" TEXT,
  "sync_status" TEXT DEFAULT 'Active',
  "sync_timestamp" TIMESTAMP DEFAULT now(),
  "mapping_status" TEXT DEFAULT 'Active',
  CONSTRAINT "document_po_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "document_po_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "project_core"."document" ("id"),
  CONSTRAINT "document_po_po_id_fkey" FOREIGN KEY ("po_id") REFERENCES "reference_core"."purchase_order" ("id")
);

-- ---------------------------------------------------------------------------
-- Schema: ontology_core
-- Purpose: CFIHOS ontology definitions (classes, properties, UoM, validation rules)
-- ---------------------------------------------------------------------------

-- class: CFIHOS class definitions (tag classes, equipment classes).
CREATE TABLE "ontology_core"."class" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "definition" TEXT,
  "concept" TEXT, -- Functional | Physical | Functional Physical
  "is_abstract" BOOLEAN,
  "parent_class_id" UUID,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "class_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "class_code_key" UNIQUE ("code"),
  CONSTRAINT "class_parent_class_id_fkey" FOREIGN KEY ("parent_class_id") REFERENCES "ontology_core"."class" ("id")
);

-- property: CFIHOS property/attribute definitions.
CREATE TABLE "ontology_core"."property" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "definition" TEXT,
  "data_type" TEXT,
  "length" INTEGER,
  "uom_group_id" UUID,
  "validation_rule_id" UUID,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "property_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "property_code_key" UNIQUE ("code"),
  CONSTRAINT "property_uom_group_id_fkey" FOREIGN KEY ("uom_group_id") REFERENCES "ontology_core"."uom_group" ("id"),
  CONSTRAINT "property_validation_rule_id_fkey" FOREIGN KEY ("validation_rule_id") REFERENCES "ontology_core"."validation_rule" ("id")
);

-- uom: Units of measure.
CREATE TABLE "ontology_core"."uom" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "symbol" TEXT,
  "uom_group_id" UUID,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "uom_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "uom_code_key" UNIQUE ("code"),
  CONSTRAINT "uom_uom_group_id_fkey" FOREIGN KEY ("uom_group_id") REFERENCES "ontology_core"."uom_group" ("id")
);

-- uom_group: Unit of measure groupings (Pressure, Temperature, Length, Mass, Power, etc.).
CREATE TABLE "ontology_core"."uom_group" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "uom_group_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "uom_group_code_key" UNIQUE ("code")
);

-- validation_rule: Property validation rules and picklists.
CREATE TABLE "ontology_core"."validation_rule" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "validation_type" TEXT, -- picklist | regex | range
  "validation_value" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "validation_rule_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "validation_rule_code_key" UNIQUE ("code")
);

-- class_property: Property definitions per class (CFIHOS mappings).
CREATE TABLE "ontology_core"."class_property" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "class_id" UUID,
  "property_id" UUID,
  "mapping_concept" TEXT, -- Functional | Physical | Functional Physical
  "mapping_presence" TEXT, -- Mandatory | Optional
  "mapping_status" TEXT DEFAULT 'Active',
  "mapping_class_name_raw" TEXT,
  "mapping_class_code_raw" TEXT,
  "mapping_property_code_raw" TEXT,
  "mapping_property_name_raw" TEXT,
  CONSTRAINT "class_property_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "class_property_unique_link" UNIQUE ("class_id", "property_id"),
  CONSTRAINT "class_property_class_id_fkey" FOREIGN KEY ("class_id") REFERENCES "ontology_core"."class" ("id"),
  CONSTRAINT "class_property_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "ontology_core"."property" ("id")
);

-- ---------------------------------------------------------------------------
-- Schema: project_core
-- Purpose: Core project data: tags, documents, property values (SCD Type 2)
-- ---------------------------------------------------------------------------

-- tag: Master tag register with SCD Type 2 change tracking.
CREATE TABLE "project_core"."tag" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "source_id" TEXT NOT NULL,
  "tag_name" TEXT NOT NULL,
  "tag_status" TEXT,
  "description" TEXT,
  "parent_tag_raw" TEXT,
  "parent_tag_id" UUID,
  "tag_class_raw" TEXT,
  "class_id" UUID,
  "area_code_raw" TEXT,
  "area_id" UUID,
  "process_unit_raw" TEXT,
  "process_unit_id" UUID,
  "discipline_code_raw" TEXT,
  "discipline_id" UUID,
  "po_code_raw" TEXT,
  "po_id" UUID,
  "design_company_name_raw" TEXT,
  "design_company_id" UUID,
  "manufacturer_company_raw" TEXT,
  "manufacturer_id" UUID,
  "vendor_company_raw" TEXT,
  "vendor_id" UUID,
  "article_code_raw" TEXT,
  "article_id" UUID,
  "model_part_raw" TEXT,
  "model_id" UUID,
  "safety_critical_item" TEXT,
  "safety_critical_item_reason_awarded" TEXT,
  "production_critical_item" TEXT,
  "safety_critical_item_group" TEXT,
  "serial_no" TEXT,
  "install_date" TEXT,
  "startup_date" TEXT,
  "warranty_end_date" TEXT,
  "price" TEXT,
  "tech_id" TEXT,
  "ip_grade" TEXT,
  "ex_class" TEXT,
  "mc_package_code" TEXT,
  "equip_no" TEXT,
  "alias" TEXT,
  "from_tag_raw" TEXT,
  "from_tag_id" UUID,
  "to_tag_raw" TEXT,
  "to_tag_id" UUID,
  "plant_raw" TEXT,
  "plant_id" UUID,
  "project_id" UUID,
  "purchase_date_raw"      TEXT,
  "company_raw"           TEXT,
  "company_id"            UUID,
  "requisition_code_raw"   TEXT,
  "part_of_raw"           TEXT,
  "vendor_company_raw" TEXT,
  "vendor_id" UUID,
  "article_code_raw" TEXT,
  "article_id" UUID,
  "model_part_raw" TEXT,
  "model_id" UUID,
  "safety_critical_item" TEXT,
  "safety_critical_item_reason_awarded" TEXT,
  "production_critical_item" TEXT,
  "safety_critical_item_group" TEXT,
  "serial_no" TEXT,
  "install_date" TEXT,
  "startup_date" TEXT,
  "warranty_end_date" TEXT,
  "price" TEXT,
  "tech_id" TEXT,
  "ip_grade" TEXT,
  "ex_class" TEXT,
  "mc_package_code" TEXT,
  "equip_no" TEXT,
  "alias" TEXT,
  "from_tag_raw" TEXT,
  "from_tag_id" UUID,
  "to_tag_raw" TEXT,
  "to_tag_id" UUID,
  "plant_raw" TEXT,
  "plant_id" UUID,
  "project_id" UUID,
  "purchase_date_raw"      TEXT,
  "company_raw"           TEXT,
  "requisition_code_raw"   TEXT,
  "part_of_raw"           TEXT,
  "row_hash" TEXT,
  "sync_status" TEXT,
  "sync_timestamp" TIMESTAMP DEFAULT now(),
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "tag_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "tag_source_id_key" UNIQUE ("source_id"),
  CONSTRAINT "tag_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id"),
  CONSTRAINT "tag_class_id_fkey" FOREIGN KEY ("class_id") REFERENCES "ontology_core"."class" ("id"),
  CONSTRAINT "tag_area_id_fkey" FOREIGN KEY ("area_id") REFERENCES "reference_core"."area" ("id"),
  CONSTRAINT "tag_process_unit_id_fkey" FOREIGN KEY ("process_unit_id") REFERENCES "reference_core"."process_unit" ("id"),
  CONSTRAINT "tag_discipline_id_fkey" FOREIGN KEY ("discipline_id") REFERENCES "reference_core"."discipline" ("id"),
  CONSTRAINT "tag_po_id_fkey" FOREIGN KEY ("po_id") REFERENCES "reference_core"."purchase_order" ("id"),
  CONSTRAINT "tag_design_company_id_fkey" FOREIGN KEY ("design_company_id") REFERENCES "reference_core"."company" ("id"),
  CONSTRAINT "tag_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "reference_core"."article" ("id"),
  CONSTRAINT "tag_parent_tag_id_fkey" FOREIGN KEY ("parent_tag_id") REFERENCES "project_core"."tag" ("id"),
  CONSTRAINT "tag_from_tag_id_fkey" FOREIGN KEY ("from_tag_id") REFERENCES "project_core"."tag" ("id"),
  CONSTRAINT "tag_to_tag_id_fkey" FOREIGN KEY ("to_tag_id") REFERENCES "project_core"."tag" ("id"),
  CONSTRAINT "tag_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "reference_core"."project" ("id")
);

-- document: Master document register with SCD Type 2 change tracking.
CREATE TABLE "project_core"."document" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "doc_number" TEXT NOT NULL,
  "title" TEXT,
  "rev" TEXT,
  "rev_date" DATE,
  "rev_comment" TEXT,
  "rev_author" TEXT,
  "status" TEXT,
  "doc_type_code" TEXT,
  "plant_id" UUID,
  "project_id" UUID,
  "company_id" UUID,
  "company_name_raw" TEXT,
  "mdr_flag" BOOLEAN,
  "row_hash" TEXT,
  "sync_status" TEXT,
  "sync_timestamp" TIMESTAMP DEFAULT now(),
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "document_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "document_doc_number_key" UNIQUE ("doc_number"),
  CONSTRAINT "document_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id"),
  CONSTRAINT "document_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "reference_core"."project" ("id"),
  CONSTRAINT "document_company_id_fkey" FOREIGN KEY ("company_id") REFERENCES "reference_core"."company" ("id")
);

-- property_value: Tag property values (EAV pattern) with SCD Type 2 change tracking.
CREATE TABLE "project_core"."property_value" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "tag_id" UUID,
  "tag_name_raw" TEXT,
  "tag_source_id_raw" TEXT,
  "mapping_id" UUID,
  "property_id" UUID,
  "class_id" UUID,
  "class_code_raw" TEXT,
  "property_code_raw" TEXT,
  "property_value" TEXT,
  "property_uom_raw" TEXT,
  "mapping_concept_raw" TEXT,
  "row_hash" TEXT,
  "sync_status" TEXT,
  "sync_timestamp" TIMESTAMP DEFAULT now(),
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "property_value_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "property_value_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id"),
  CONSTRAINT "property_value_mapping_id_fkey" FOREIGN KEY ("mapping_id") REFERENCES "ontology_core"."class_property" ("id"),
  CONSTRAINT "property_value_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "ontology_core"."property" ("id"),
  CONSTRAINT "property_value_class_id_fkey" FOREIGN KEY ("class_id") REFERENCES "ontology_core"."class" ("id")
);

-- ---------------------------------------------------------------------------
-- Schema: reference_core
-- Purpose: Reference/master data: companies, POs, locations, units, articles, etc.
-- ---------------------------------------------------------------------------

-- site: Geographic sites.
CREATE TABLE "reference_core"."site" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "site_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "site_code_key" UNIQUE ("code")
);

-- plant: Production plants.
CREATE TABLE "reference_core"."plant" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "site_id" UUID,
  "site_code_raw" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "plant_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "plant_code_key" UNIQUE ("code"),
  CONSTRAINT "plant_site_id_fkey" FOREIGN KEY ("site_id") REFERENCES "reference_core"."site" ("id")
);

-- project: Projects.
CREATE TABLE "reference_core"."project" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "site_id" UUID,
  "site_code_raw" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "project_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "project_code_key" UNIQUE ("code"),
  CONSTRAINT "project_site_id_fkey" FOREIGN KEY ("site_id") REFERENCES "reference_core"."site" ("id")
);

-- area: Area/zone hierarchy.
CREATE TABLE "reference_core"."area" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "main_area_code" TEXT,
  "plant_id" UUID,
  "plant_code_raw" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "area_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "area_code_key" UNIQUE ("code"),
  CONSTRAINT "area_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id")
);

-- process_unit: Process unit breakdown.
CREATE TABLE "reference_core"."process_unit" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "plant_id" UUID,
  "plant_code_raw" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "process_unit_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "process_unit_code_key" UNIQUE ("code"),
  CONSTRAINT "process_unit_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id")
);

-- discipline: Engineering disciplines (EA=Electrical, MX=Mechanical, IN=Instrumentation, etc.).
CREATE TABLE "reference_core"."discipline" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "code_internal" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "discipline_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "discipline_code_key" UNIQUE ("code")
);

-- company: Companies (manufacturers, suppliers, contractors).
CREATE TABLE "reference_core"."company" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "address" TEXT,
  "town_city" TEXT,
  "zip_code" TEXT,
  "country_code" CHAR(2),
  "phone" TEXT,
  "email" TEXT,
  "website" TEXT,
  "contact_person" TEXT,
  "is_manufacturer" BOOLEAN,
  "is_supplier" BOOLEAN,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "company_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "company_code_key" UNIQUE ("code")
);

-- purchase_order: Purchase orders.
CREATE TABLE "reference_core"."purchase_order" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "definition" TEXT,
  "po_date" TEXT,
  "issuer_id" UUID,
  "receiver_id" UUID,
  "issuer_company_raw" TEXT,
  "receiver_company_raw" TEXT,
  "package_id" UUID,
  "package_code_raw" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "purchase_order_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "purchase_order_code_key" UNIQUE ("code"),
  CONSTRAINT "purchase_order_issuer_id_fkey" FOREIGN KEY ("issuer_id") REFERENCES "reference_core"."company" ("id"),
  CONSTRAINT "purchase_order_receiver_id_fkey" FOREIGN KEY ("receiver_id") REFERENCES "reference_core"."company" ("id"),
  CONSTRAINT "purchase_order_package_id_fkey" FOREIGN KEY ("package_id") REFERENCES "reference_core"."po_package" ("id")
);

-- po_package: Purchase order groupings/packages.
CREATE TABLE "reference_core"."po_package" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "po_package_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "po_package_code_key" UNIQUE ("code")
);

-- sece: Safety/Environment/Criticality/Equipment codes.
CREATE TABLE "reference_core"."sece" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "sece_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "sece_code_key" UNIQUE ("code")
);

-- model_part: Component models and parts (technical catalog).
CREATE TABLE "reference_core"."model_part" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "definition" TEXT,
  "manuf_company_raw" TEXT,
  "manufacturer_id" UUID,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "model_part_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "model_part_code_key" UNIQUE ("code"),
  CONSTRAINT "model_part_manufacturer_id_fkey" FOREIGN KEY ("manufacturer_id") REFERENCES "reference_core"."company" ("id")
);

-- article: Vendor parts/equipment specifications (SKU catalog).
CREATE TABLE "reference_core"."article" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "code" TEXT NOT NULL,
  "name" TEXT,
  "definition" TEXT,
  "article_type" TEXT,
  "product_family" TEXT,
  "commodity_code" TEXT,
  "basic_construction" TEXT,
  "manufacturer_material" TEXT,
  "manufacturer_company_name_raw" TEXT,
  "manufacturer_id" UUID,
  "manufacturer_el_number" TEXT,
  "manufacturer_sap_code" TEXT,
  "model_part_code_raw" TEXT,
  "model_part_id" UUID,
  "cable_outer_diameter" REAL,
  "cable_cross_sectional_area" REAL,
  "object_status" TEXT DEFAULT 'Active',
  CONSTRAINT "article_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "article_code_key" UNIQUE ("code"),
  CONSTRAINT "article_manufacturer_id_fkey" FOREIGN KEY ("manufacturer_id") REFERENCES "reference_core"."company" ("id"),
  CONSTRAINT "article_model_part_id_fkey" FOREIGN KEY ("model_part_id") REFERENCES "reference_core"."model_part" ("id")
);

-- ===========================================================================
-- CRS Module (Comment Response Sheet) — migrations 014–029
-- ===========================================================================

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_template" (
  "id"                  UUID      NOT NULL DEFAULT gen_random_uuid(),
  "template_text"       TEXT      NOT NULL,
  "template_hash"       TEXT      NOT NULL,
  "category_code"       TEXT      NOT NULL,
  "check_type"          TEXT      NULL,
  "last_used_at"        TIMESTAMP NOT NULL DEFAULT now(),
  "created_at"          TIMESTAMP NOT NULL DEFAULT now(),
  "object_status"       TEXT      NOT NULL DEFAULT 'Active',
  "short_template_text" TEXT      NULL,
  "severity"            TEXT      NULL DEFAULT 'Warning',
  "updated_at"          TIMESTAMPTZ NULL DEFAULT now(),
  CONSTRAINT "crs_comment_template_pkey"     PRIMARY KEY ("id"),
  CONSTRAINT "crs_comment_template_hash_key" UNIQUE ("template_hash"),
  CONSTRAINT "chk_crs_template_object_status"
      CHECK ("object_status" IN ('Active', 'Inactive'))
);
CREATE INDEX IF NOT EXISTS "idx_crs_template_hash"
    ON "audit_core"."crs_comment_template"("template_hash")
    WHERE "object_status" = 'Active';
CREATE INDEX IF NOT EXISTS "idx_crs_template_category"
    ON "audit_core"."crs_comment_template"("category_code")
    WHERE "object_status" = 'Active';

CREATE TABLE IF NOT EXISTS "audit_core"."crs_validation_query" (
  "id"                  UUID      NOT NULL DEFAULT gen_random_uuid(),
  "query_code"          TEXT      NOT NULL,
  "query_name"          TEXT      NOT NULL,
  "description"         TEXT      NULL,
  "category"            TEXT      NOT NULL,
  "category_description" TEXT     NULL,
  "sql_query"           TEXT      NOT NULL,
  "expected_result"     TEXT      NULL,
  "has_parameters"      BOOLEAN   NOT NULL DEFAULT false,
  "parameter_names"     TEXT[]    NULL,
  "is_active"           BOOLEAN   NOT NULL DEFAULT true,
  "created_at"          TIMESTAMP NOT NULL DEFAULT now(),
  "updated_at"          TIMESTAMP NOT NULL DEFAULT now(),
  "created_by"          TEXT      NULL,
  "notes"               TEXT      NULL,
  "object_status"       TEXT      NOT NULL DEFAULT 'Active',
  "evaluation_strategy" TEXT      NULL,
  "group_by_field"      TEXT      NULL,
  "response_template"   TEXT      NULL,
  "query_type"          TEXT      NOT NULL DEFAULT 'GROUP',
  CONSTRAINT "crs_validation_query_pkey"     PRIMARY KEY ("id"),
  CONSTRAINT "crs_validation_query_code_key" UNIQUE ("query_code"),
  CONSTRAINT "chk_crs_vq_query_type"
      CHECK ("query_type" IN ('GROUP', 'INDIVIDUAL'))
);
CREATE INDEX IF NOT EXISTS "idx_crs_query_category"
    ON "audit_core"."crs_validation_query"("category");
CREATE INDEX IF NOT EXISTS "idx_crs_query_is_active"
    ON "audit_core"."crs_validation_query"("is_active");
CREATE INDEX IF NOT EXISTS "idx_crs_query_evaluation_strategy"
    ON "audit_core"."crs_validation_query"("evaluation_strategy")
    WHERE "evaluation_strategy" IS NOT NULL;
CREATE INDEX IF NOT EXISTS "idx_crs_vq_query_type"
    ON "audit_core"."crs_validation_query"("query_type");

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment" (
  "id"                         UUID      NOT NULL DEFAULT gen_random_uuid(),
  "crs_doc_number"             TEXT      NOT NULL,
  "revision"                   TEXT      NULL,
  "return_code"                TEXT      NULL,
  "transmittal_number"         TEXT      NULL,
  "transmittal_date"           DATE      NULL,
  "comment_id"                 TEXT      NOT NULL,
  "group_comment"              TEXT      NOT NULL,
  "comment"                    TEXT      NOT NULL,
  "tag_name"                   TEXT      NULL,
  "tag_id"                     UUID      NULL,
  "property_name"              TEXT      NULL,
  "response_vendor"            TEXT      NULL,
  "source_file"                TEXT      NOT NULL,
  "detail_file"                TEXT      NULL,
  "detail_sheet"               TEXT      NULL,
  "crs_file_path"              TEXT      NOT NULL,
  "crs_file_timestamp"         TIMESTAMP NULL,
  "llm_category"               TEXT      NULL,
  "llm_category_confidence"    REAL      NULL,
  "llm_response"               TEXT      NULL,
  "llm_response_timestamp"     TIMESTAMP NULL,
  "llm_model_used"             TEXT      NULL,
  "status"                     TEXT      NOT NULL DEFAULT 'RECEIVED',
  "formal_response"            TEXT      NULL,
  "formal_response_rationale"  TEXT      NULL,
  "response_author"            TEXT      NULL,
  "response_approval_date"     DATE      NULL,
  "response_review_notes"      TEXT      NULL,
  "row_hash"                   TEXT      NULL,
  "sync_timestamp"             TIMESTAMP NOT NULL DEFAULT now(),
  "object_status"              TEXT      NOT NULL DEFAULT 'Active',
  "document_number"            TEXT      NULL,
  "from_tag"                   TEXT      NULL,
  "to_tag"                     TEXT      NULL,
  "classification_tier"        SMALLINT  NULL,
  "template_id"                UUID      NULL,
  "category_code"              TEXT      NULL,
  "category_confidence"        REAL      NULL,
  "validation_query_ids"       UUID[]    NULL,
  "deferred_reason"            TEXT      NULL,
  CONSTRAINT "crs_comment_pkey"         PRIMARY KEY ("id"),
  CONSTRAINT "crs_comment_comment_id_key" UNIQUE ("comment_id"),
  CONSTRAINT "crs_comment_status_check"
      CHECK ("status" IN ('RECEIVED','IN_REVIEW','RESPONDED','APPROVED','CLOSED','DEFERRED','NEEDS_NEW_CATEGORY')),
  CONSTRAINT "crs_comment_object_status_check"
      CHECK ("object_status" IN ('Active','Inactive')),
  CONSTRAINT "crs_comment_llm_category_confidence_check"
      CHECK ("llm_category_confidence" >= 0.0 AND "llm_category_confidence" <= 1.0),
  CONSTRAINT "crs_comment_tag_id_fkey"
      FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag"("id") ON DELETE SET NULL,
  CONSTRAINT "crs_comment_template_id_fkey"
      FOREIGN KEY ("template_id") REFERENCES "audit_core"."crs_comment_template"("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_crs_comment_status"
    ON "audit_core"."crs_comment"("status");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_category"
    ON "audit_core"."crs_comment"("llm_category");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_tag_id"
    ON "audit_core"."crs_comment"("tag_id");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_crs_doc_number"
    ON "audit_core"."crs_comment"("crs_doc_number");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_source_file"
    ON "audit_core"."crs_comment"("source_file");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_transmittal"
    ON "audit_core"."crs_comment"("transmittal_date");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_sync_timestamp"
    ON "audit_core"."crs_comment"("sync_timestamp");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_low_confidence"
    ON "audit_core"."crs_comment"("llm_category_confidence")
    WHERE "llm_category_confidence" < 0.7 AND "llm_category" IS NOT NULL;
CREATE INDEX IF NOT EXISTS "idx_crs_comment_document_number"
    ON "audit_core"."crs_comment"("document_number")
    WHERE "document_number" IS NOT NULL AND "document_number" <> 'Not Applicable';
CREATE INDEX IF NOT EXISTS "idx_crs_comment_from_tag"
    ON "audit_core"."crs_comment"("from_tag")
    WHERE "from_tag" IS NOT NULL;
CREATE INDEX IF NOT EXISTS "idx_crs_comment_to_tag"
    ON "audit_core"."crs_comment"("to_tag")
    WHERE "to_tag" IS NOT NULL;
CREATE INDEX IF NOT EXISTS "idx_crs_comment_category_code"
    ON "audit_core"."crs_comment"("category_code");
CREATE INDEX IF NOT EXISTS "idx_crs_comment_classification_tier"
    ON "audit_core"."crs_comment"("classification_tier")
    WHERE "classification_tier" IS NOT NULL;
CREATE INDEX IF NOT EXISTS "idx_crs_comment_deferred_reason"
    ON "audit_core"."crs_comment"("deferred_reason")
    WHERE "deferred_reason" IS NOT NULL;

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_validation" (
  "id"                     UUID      NOT NULL DEFAULT gen_random_uuid(),
  "comment_id"             UUID      NOT NULL,
  "validation_query_id"    UUID      NOT NULL,
  "validation_status"      TEXT      NOT NULL DEFAULT 'PENDING',
  "validation_result_json" JSONB     NULL,
  "validation_timestamp"   TIMESTAMP NULL,
  "validation_error"       TEXT      NULL,
  "run_id"                 UUID      NULL,
  CONSTRAINT "crs_comment_validation_pkey"   PRIMARY KEY ("id"),
  CONSTRAINT "crs_comment_validation_unique" UNIQUE ("comment_id", "validation_query_id"),
  CONSTRAINT "crs_validation_status_check"
      CHECK ("validation_status" IN ('PENDING','PASSED','FAILED','INCONCLUSIVE','SKIPPED')),
  CONSTRAINT "crs_comment_validation_comment_id_fkey"
      FOREIGN KEY ("comment_id") REFERENCES "audit_core"."crs_comment"("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_crs_cv_comment"
    ON "audit_core"."crs_comment_validation"("comment_id");
CREATE INDEX IF NOT EXISTS "idx_crs_cv_query"
    ON "audit_core"."crs_comment_validation"("validation_query_id");
CREATE INDEX IF NOT EXISTS "idx_crs_cv_status"
    ON "audit_core"."crs_comment_validation"("validation_status");
CREATE INDEX IF NOT EXISTS "idx_crs_cv_timestamp"
    ON "audit_core"."crs_comment_validation"("validation_timestamp");

CREATE TABLE IF NOT EXISTS "audit_core"."crs_comment_audit" (
  "id"             UUID      NOT NULL DEFAULT gen_random_uuid(),
  "comment_id"     UUID      NOT NULL,
  "change_type"    TEXT      NOT NULL,
  "snapshot"       JSONB     NOT NULL,
  "changed_fields" TEXT[]    NULL,
  "changed_by"     TEXT      NULL,
  "change_reason"  TEXT      NULL,
  "changed_at"     TIMESTAMP NOT NULL DEFAULT now(),
  "run_id"         UUID      NULL,
  CONSTRAINT "crs_comment_audit_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "crs_comment_audit_change_type_check"
      CHECK ("change_type" IN ('INSERT','UPDATE','DELETE','RESET')),
  CONSTRAINT "crs_comment_audit_comment_id_fkey"
      FOREIGN KEY ("comment_id") REFERENCES "audit_core"."crs_comment"("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_crs_audit_comment"
    ON "audit_core"."crs_comment_audit"("comment_id");
CREATE INDEX IF NOT EXISTS "idx_crs_audit_changed_at"
    ON "audit_core"."crs_comment_audit"("changed_at");
CREATE INDEX IF NOT EXISTS "idx_crs_audit_change_type"
    ON "audit_core"."crs_comment_audit"("change_type");

CREATE TABLE IF NOT EXISTS "audit_core"."crs_llm_template_staging" (
  "id"                UUID         NOT NULL DEFAULT gen_random_uuid(),
  "template_text"     TEXT         NOT NULL,
  "template_hash"     CHAR(32)     NOT NULL,
  "suggested_category" VARCHAR(20) NULL,
  "check_type"        VARCHAR(50)  NULL,
  "confidence"        NUMERIC(4,3) NOT NULL,
  "llm_response"      TEXT         NULL,
  "revision"          VARCHAR(20)  NULL,
  "occurrence_count"  INTEGER      NOT NULL DEFAULT 1,
  "last_seen_at"      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  "created_at"        TIMESTAMPTZ  NOT NULL DEFAULT now(),
  "object_status"     VARCHAR(20)  NOT NULL DEFAULT 'PendingReview',
  "reviewed_at"       TIMESTAMPTZ  NULL,
  "review_notes"      TEXT         NULL,
  CONSTRAINT "crs_llm_staging_pkey"       PRIMARY KEY ("id"),
  CONSTRAINT "uq_llm_staging_hash"        UNIQUE ("template_hash"),
  CONSTRAINT "chk_llm_staging_confidence" CHECK ("confidence" BETWEEN 0.0 AND 1.0),
  CONSTRAINT "chk_llm_staging_status"
      CHECK ("object_status" IN ('PendingReview','Approved','Rejected','NeedsNewCategory'))
);
CREATE INDEX IF NOT EXISTS "idx_llm_staging_status"
    ON "audit_core"."crs_llm_template_staging"("object_status");
CREATE INDEX IF NOT EXISTS "idx_llm_staging_category"
    ON "audit_core"."crs_llm_template_staging"("suggested_category");

CREATE TABLE IF NOT EXISTS "audit_core"."crs_template_query_map" (
  "id"          UUID     NOT NULL DEFAULT gen_random_uuid(),
  "template_id" UUID     NOT NULL,
  "query_id"    UUID     NOT NULL,
  "priority"    SMALLINT NOT NULL DEFAULT 1,
  "object_status" TEXT   NOT NULL DEFAULT 'Active',
  "created_at"  TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT "crs_template_query_map_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "crs_template_query_map_uq"  UNIQUE ("template_id", "query_id"),
  CONSTRAINT "crs_tqmap_template_fkey"
      FOREIGN KEY ("template_id") REFERENCES "audit_core"."crs_comment_template"("id") ON DELETE CASCADE,
  CONSTRAINT "crs_tqmap_query_fkey"
      FOREIGN KEY ("query_id") REFERENCES "audit_core"."crs_validation_query"("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_crs_tqmap_template"
    ON "audit_core"."crs_template_query_map"("template_id");
CREATE INDEX IF NOT EXISTS "idx_crs_tqmap_query"
    ON "audit_core"."crs_template_query_map"("query_id");

CREATE TABLE IF NOT EXISTS "audit_core"."crs_benchmark_example" (
  "id"               SERIAL        NOT NULL,
  "comment_pattern"  TEXT          NOT NULL,
  "category"         VARCHAR(20)   NOT NULL,
  "assigned_status"  VARCHAR(30)   NOT NULL,
  "confidence"       NUMERIC       NOT NULL DEFAULT 0.95,
  "rationale"        TEXT          NULL,
  "object_status"    VARCHAR(20)   NOT NULL DEFAULT 'Active',
  "created_by"       VARCHAR(100)  NULL DEFAULT 'system',
  "created_at"       TIMESTAMPTZ   NULL DEFAULT now(),
  CONSTRAINT "crs_benchmark_example_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_benchmark_active"
    ON "audit_core"."crs_benchmark_example"("object_status");

CREATE OR REPLACE VIEW "audit_core"."v_template_queries" AS
SELECT
    ct.id                   AS template_id,
    ct.category_code        AS template_category,
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
    vq.group_by_field,
    vq.expected_result,
    tqm.priority
FROM "audit_core"."crs_template_query_map" tqm
JOIN "audit_core"."crs_comment_template"   ct  ON ct.id  = tqm.template_id
JOIN "audit_core"."crs_validation_query"   vq  ON vq.id  = tqm.query_id
WHERE tqm.object_status = 'Active'
  AND ct.object_status  = 'Active'
  AND vq.is_active      = true
  AND vq.query_type     = 'GROUP';

CREATE OR REPLACE VIEW "audit_core"."v_crs_resolution_report" AS
SELECT
    cc.id                    AS comment_id,
    cc.comment_id            AS comment_ref,
    cc.revision,
    cc.tag_name,
    cc.status                AS comment_status,
    cc.category_code,
    cc.classification_tier,
    cc.deferred_reason,
    cc.formal_response,
    cc.response_author,
    cc.response_approval_date,
    cv.validation_status,
    cv.validation_result_json,
    cv.validation_error,
    cv.validation_timestamp,
    cv.run_id                AS validation_run_id,
    vq.query_code,
    vq.query_name,
    vq.category              AS query_category,
    vq.evaluation_strategy,
    vq.response_template,
    vq.group_by_field,
    vq.expected_result
FROM "audit_core"."crs_comment" cc
LEFT JOIN "audit_core"."crs_comment_validation"  cv ON cv.comment_id = cc.id
LEFT JOIN "audit_core"."crs_validation_query"     vq ON vq.id         = cv.validation_query_id
WHERE cc.object_status = 'Active';

-- ===========================================================================
-- END OF SCHEMA
-- ===========================================================================
