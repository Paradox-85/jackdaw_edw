CREATE TABLE "reference_core"."site" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "site_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "site_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."company" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "address" TEXT NULL,
  "town_city" TEXT NULL,
  "zip_code" TEXT NULL,
  "country_code" CHARACTER(2) NULL,
  "phone" TEXT NULL,
  "email" TEXT NULL,
  "website" TEXT NULL,
  "contact_person" TEXT NULL,
  "is_manufacturer" BOOLEAN NULL DEFAULT false ,
  "is_supplier" BOOLEAN NULL DEFAULT false ,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "company_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "company_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."sece" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "sece_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "sece_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."discipline" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "code_internal" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "discipline_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "discipline_code_key" UNIQUE ("code")
);
CREATE TABLE "ontology_core"."class_property" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "class_id" UUID NULL,
  "property_id" UUID NULL,
  "mapping_concept" TEXT NULL,
  "mapping_presence" TEXT NULL,
  "mapping_status" TEXT NULL DEFAULT 'Active'::text ,
  "mapping_class_name_raw" TEXT NULL,
  "mapping_class_code_raw" TEXT NULL,
  "mapping_property_code_raw" TEXT NULL,
  "mapping_property_name_raw" TEXT NULL,
  CONSTRAINT "class_property_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "class_property_unique_link" UNIQUE ("class_id", "property_id")
);
CREATE TABLE "reference_core"."po_package" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "po_package_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "po_package_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."article" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "definition" TEXT NULL,
  "article_type" TEXT NULL,
  "basic_construction" TEXT NULL,
  "cable_cross_sectional_area" REAL NULL,
  "cable_outer_diameter" REAL NULL,
  "commodity_code" TEXT NULL,
  "manufacturer_id" UUID NULL,
  "manufacturer_el_number" TEXT NULL,
  "manufacturer_material" TEXT NULL,
  "model_part_id" UUID NULL,
  "manufacturer_sap_code" TEXT NULL,
  "product_family" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "manufacturer_company_name_raw" TEXT NULL,
  "model_part_code_raw" TEXT NULL,
  CONSTRAINT "article_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "article_code_key" UNIQUE ("code")
);
CREATE TABLE "project_core"."document" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "doc_number" TEXT NOT NULL,
  "title" TEXT NULL,
  "rev" TEXT NULL,
  "rev_comment" TEXT NULL,
  "status" TEXT NULL,
  "doc_type_code" TEXT NULL,
  "rev_author" TEXT NULL,
  "plant_id" UUID NULL,
  "project_id" UUID NULL,
  "company_id" UUID NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "row_hash" TEXT NULL,
  "sync_status" TEXT NULL,
  "sync_timestamp" TIMESTAMP NULL DEFAULT now() ,
  "mdr_flag" BOOLEAN NULL,
  "rev_date" DATE NULL,
  "company_name_raw" TEXT NULL,
  CONSTRAINT "document_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "document_doc_number_key" UNIQUE ("doc_number")
);
CREATE TABLE "audit_core"."sync_run_stats" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "run_id" UUID NOT NULL,
  "target_table" TEXT NOT NULL,
  "start_time" TIMESTAMP NOT NULL,
  "end_time" TIMESTAMP NULL,
  "count_created" INTEGER NULL DEFAULT 0 ,
  "count_updated" INTEGER NULL DEFAULT 0 ,
  "count_unchanged" INTEGER NULL DEFAULT 0 ,
  "count_deleted" INTEGER NULL DEFAULT 0 ,
  "count_errors" INTEGER NULL DEFAULT 0 ,
  "source_file" TEXT NULL,
  "mapping_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "sync_run_stats_pkey" PRIMARY KEY ("id")
);
CREATE TABLE "ontology_core"."class" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "parent_class_id" UUID NULL,
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "is_abstract" BOOLEAN NULL DEFAULT false ,
  "definition" TEXT NULL,
  "concept" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "class_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "class_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."purchase_order" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "package_id" UUID NULL,
  "issuer_id" UUID NULL,
  "receiver_id" UUID NULL,
  "name" TEXT NULL,
  "definition" TEXT NULL,
  "po_date" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "issuer_company_raw" TEXT NULL,
  "receiver_company_raw" TEXT NULL,
  "package_code_raw" TEXT NULL,
  "code" TEXT NOT NULL,
  CONSTRAINT "purchase_order_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "purchase_order_code_key" UNIQUE ("code")
);
CREATE TABLE "ontology_core"."uom_group" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "uom_group_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "uom_group_code_key" UNIQUE ("code")
);
CREATE TABLE "ontology_core"."uom" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "uom_group_id" UUID NULL,
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "symbol" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "uom_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "uom_code_key" UNIQUE ("code")
);
CREATE TABLE "ontology_core"."validation_rule" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "validation_type" TEXT NULL,
  "validation_value" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  CONSTRAINT "validation_rule_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "validation_rule_code_key" UNIQUE ("code")
);
CREATE TABLE "ontology_core"."property" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "code" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "definition" TEXT NULL,
  "data_type" TEXT NULL,
  "length" INTEGER NULL,
  "uom_group_id" UUID NULL,
  "validation_rule_id" UUID NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  CONSTRAINT "property_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "property_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."plant" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "site_id" UUID NULL,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "site_code_raw" TEXT NULL,
  CONSTRAINT "plant_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "plant_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."project" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "site_id" UUID NULL,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "site_code_raw" TEXT NULL,
  CONSTRAINT "project_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "project_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."area" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "plant_id" UUID NULL,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "main_area_code" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "plant_code_raw" TEXT NULL,
  CONSTRAINT "area_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "area_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."process_unit" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "plant_id" UUID NULL,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "plant_code_raw" TEXT NULL,
  CONSTRAINT "process_unit_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "process_unit_code_key" UNIQUE ("code")
);
CREATE TABLE "reference_core"."model_part" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "manufacturer_id" UUID NULL,
  "code" TEXT NOT NULL,
  "name" TEXT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "manuf_company_raw" TEXT NULL,
  "definition" TEXT NULL,
  CONSTRAINT "model_part_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "uq_model_part_manuf_raw_code" UNIQUE ("manuf_company_raw", "code")
);
CREATE TABLE "project_core"."tag" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "tag_name" TEXT NOT NULL,
  "tag_status" TEXT NULL,
  "parent_tag_id" UUID NULL,
  "class_id" UUID NULL,
  "article_id" UUID NULL,
  "design_company_id" UUID NULL,
  "area_id" UUID NULL,
  "discipline_id" UUID NULL,
  "process_unit_id" UUID NULL,
  "project_id" UUID NULL,
  "po_id" UUID NULL,
  "row_hash" TEXT NULL,
  "tag_class_raw" TEXT NULL,
  "sync_status" TEXT NULL,
  "sync_timestamp" TIMESTAMP NULL DEFAULT now() ,
  "article_code_raw" TEXT NULL,
  "design_company_name_raw" TEXT NULL,
  "area_code_raw" TEXT NULL,
  "process_unit_raw" TEXT NULL,
  "discipline_code_raw" TEXT NULL,
  "po_code_raw" TEXT NULL,
  "equip_no" TEXT NULL,
  "manufacturer_id" UUID NULL,
  "vendor_id" UUID NULL,
  "model_id" UUID NULL,
  "serial_no" TEXT NULL,
  "tech_id" TEXT NULL,
  "alias" TEXT NULL,
  "description" TEXT NULL,
  "install_date" TEXT NULL,
  "startup_date" TEXT NULL,
  "warranty_end_date" TEXT NULL,
  "price" TEXT NULL,
  "model_part_raw" TEXT NULL,
  "manufacturer_company_raw" TEXT NULL,
  "vendor_company_raw" TEXT NULL,
  "source_id" TEXT NOT NULL,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "parent_tag_raw" TEXT NULL,
  "ex_class" TEXT NULL,
  "ip_grade" TEXT NULL,
  "mc_package_code" TEXT NULL,
  "from_tag_raw"    TEXT NULL,
  "to_tag_raw"      TEXT NULL,
  "from_tag_id"     UUID NULL,
  "to_tag_id"       UUID NULL,
  -- Export-facing columns added by migration_001 (2026-03-10)
  "plant_id"        UUID NULL,
  "plant_raw" TEXT NULL,
  "safety_critical_item"                TEXT NULL,
  "safety_critical_item_reason_awarded" TEXT NULL,
  "production_critical_item"            TEXT NULL,
  CONSTRAINT "tag_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "uq_source_id" UNIQUE ("source_id")
);
CREATE TABLE "mapping"."document_po" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "document_id" UUID NULL,
  "po_id" UUID NULL,
  "mapping_status" TEXT NULL DEFAULT 'Active'::text ,
  "row_hash" TEXT NULL,
  "sync_status" TEXT NULL,
  "sync_timestamp" TIMESTAMP NULL DEFAULT now() ,
  CONSTRAINT "document_po_pkey" PRIMARY KEY ("id")
);
CREATE TABLE "mapping"."tag_document" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "tag_id" UUID NULL,
  "document_id" UUID NULL,
  "mapping_status" TEXT NULL DEFAULT 'Active'::text ,
  "row_hash" TEXT NULL,
  "sync_status" TEXT NULL,
  "sync_timestamp" TIMESTAMP NULL DEFAULT now() ,
  "doc_number_raw" TEXT NULL,
  "tag_name_raw" TEXT NULL,
  CONSTRAINT "tag_document_pkey" PRIMARY KEY ("id")
);
CREATE TABLE "mapping"."tag_sece" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "tag_id" UUID NULL,
  "sece_id" UUID NULL,
  "mapping_status" TEXT NULL DEFAULT 'Active'::text ,
  "row_hash" TEXT NULL,
  "sync_status" TEXT NULL,
  "sync_timestamp" TIMESTAMP NULL DEFAULT now() ,
  CONSTRAINT "tag_sece_pkey" PRIMARY KEY ("id")
);
CREATE TABLE "project_core"."property_value" ( 
  "id" UUID NOT NULL DEFAULT gen_random_uuid() ,
  "tag_id" UUID NULL,
  "class_id" UUID NULL,
  "property_id" UUID NULL,
  "mapping_id" UUID NULL,
  "tag_name_raw" TEXT NULL,
  "class_code_raw" TEXT NULL,
  "property_code_raw" TEXT NULL,
  "mapping_concept_raw" TEXT NULL,
  "property_uom_raw" TEXT NULL,
  "property_value" TEXT NULL,
  "row_hash" TEXT NULL,
  "sync_status" TEXT NULL,
  "sync_timestamp" TIMESTAMP NULL DEFAULT now() ,
  "object_status" TEXT NULL DEFAULT 'Active'::text ,
  "tag_source_id_raw" TEXT NULL,
  CONSTRAINT "property_value_pkey" PRIMARY KEY ("id")
);
CREATE TABLE "audit_core"."tag_status_history" (
  "id"             UUID      NOT NULL DEFAULT gen_random_uuid(),
  "tag_id"         UUID      NOT NULL,
  "tag_name"       TEXT      NOT NULL,
  "source_id"      TEXT      NOT NULL,
  "sync_status"    TEXT      NOT NULL,
  "sync_timestamp" TIMESTAMP NOT NULL DEFAULT now(),
  "run_id"         UUID      NULL,
  "row_hash"       TEXT      NULL,
  "snapshot"       JSONB     NULL,
  CONSTRAINT "tag_status_history_pkey" PRIMARY KEY ("id")
);
CREATE INDEX "idx_tag_hist_tag_id" ON "audit_core"."tag_status_history" ("tag_id"         ASC);
CREATE INDEX "idx_tag_hist_ts"     ON "audit_core"."tag_status_history" ("sync_timestamp" ASC);
ALTER TABLE "audit_core"."tag_status_history"
  ADD CONSTRAINT "tag_status_history_tag_id_fkey"
  FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id")
  ON DELETE NO ACTION ON UPDATE NO ACTION;
CREATE INDEX "idx_sync_stats_time"
ON "audit_core"."sync_run_stats" (
  "start_time" ASC
);
CREATE INDEX "idx_prop_val_tag_id" 
ON "project_core"."property_value" (
  "tag_id" ASC
);
CREATE INDEX "idx_prop_val_row_hash" 
ON "project_core"."property_value" (
  "row_hash" ASC
);
CREATE INDEX "idx_prop_val_mapping_id" 
ON "project_core"."property_value" (
  "mapping_id" ASC
);
ALTER TABLE "ontology_core"."class_property" ADD CONSTRAINT "class_property_class_id_fkey" FOREIGN KEY ("class_id") REFERENCES "ontology_core"."class" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "ontology_core"."class_property" ADD CONSTRAINT "class_property_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "ontology_core"."property" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."article" ADD CONSTRAINT "article_manufacturer_id_fkey" FOREIGN KEY ("manufacturer_id") REFERENCES "reference_core"."company" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."article" ADD CONSTRAINT "article_model_part_id_fkey" FOREIGN KEY ("model_part_id") REFERENCES "reference_core"."model_part" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."document" ADD CONSTRAINT "document_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."document" ADD CONSTRAINT "document_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "reference_core"."project" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."document" ADD CONSTRAINT "document_company_id_fkey" FOREIGN KEY ("company_id") REFERENCES "reference_core"."company" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "ontology_core"."class" ADD CONSTRAINT "class_parent_class_id_fkey" FOREIGN KEY ("parent_class_id") REFERENCES "ontology_core"."class" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."purchase_order" ADD CONSTRAINT "purchase_order_package_id_fkey" FOREIGN KEY ("package_id") REFERENCES "reference_core"."po_package" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."purchase_order" ADD CONSTRAINT "purchase_order_issuer_id_fkey" FOREIGN KEY ("issuer_id") REFERENCES "reference_core"."company" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."purchase_order" ADD CONSTRAINT "purchase_order_receiver_id_fkey" FOREIGN KEY ("receiver_id") REFERENCES "reference_core"."company" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "ontology_core"."uom" ADD CONSTRAINT "uom_uom_group_id_fkey" FOREIGN KEY ("uom_group_id") REFERENCES "ontology_core"."uom_group" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "ontology_core"."property" ADD CONSTRAINT "property_uom_group_id_fkey" FOREIGN KEY ("uom_group_id") REFERENCES "ontology_core"."uom_group" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "ontology_core"."property" ADD CONSTRAINT "property_validation_id_fkey" FOREIGN KEY ("validation_rule_id") REFERENCES "ontology_core"."validation_rule" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."plant" ADD CONSTRAINT "plant_site_id_fkey" FOREIGN KEY ("site_id") REFERENCES "reference_core"."site" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."project" ADD CONSTRAINT "project_site_id_fkey" FOREIGN KEY ("site_id") REFERENCES "reference_core"."site" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."area" ADD CONSTRAINT "area_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."process_unit" ADD CONSTRAINT "process_unit_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "reference_core"."model_part" ADD CONSTRAINT "model_part_manuf_id_fkey" FOREIGN KEY ("manufacturer_id") REFERENCES "reference_core"."company" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_parent_tag_id_fkey" FOREIGN KEY ("parent_tag_id") REFERENCES "project_core"."tag" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_plant_id_fkey" FOREIGN KEY ("plant_id") REFERENCES "reference_core"."plant" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
CREATE INDEX "idx_tag_plant_id" ON "project_core"."tag" ("plant_id") WHERE "plant_id" IS NOT NULL;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_from_tag_id_fkey" FOREIGN KEY ("from_tag_id") REFERENCES "project_core"."tag" ("id") ON DELETE SET NULL ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_to_tag_id_fkey" FOREIGN KEY ("to_tag_id") REFERENCES "project_core"."tag" ("id") ON DELETE SET NULL ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_class_id_fkey" FOREIGN KEY ("class_id") REFERENCES "ontology_core"."class" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "reference_core"."article" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_company_id_fkey" FOREIGN KEY ("design_company_id") REFERENCES "reference_core"."company" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_area_id_fkey" FOREIGN KEY ("area_id") REFERENCES "reference_core"."area" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_discipline_id_fkey" FOREIGN KEY ("discipline_id") REFERENCES "reference_core"."discipline" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_process_unit_id_fkey" FOREIGN KEY ("process_unit_id") REFERENCES "reference_core"."process_unit" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "reference_core"."project" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."tag" ADD CONSTRAINT "tag_po_id_fkey" FOREIGN KEY ("po_id") REFERENCES "reference_core"."purchase_order" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "mapping"."document_po" ADD CONSTRAINT "document_po_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "project_core"."document" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "mapping"."document_po" ADD CONSTRAINT "document_po_po_id_fkey" FOREIGN KEY ("po_id") REFERENCES "reference_core"."purchase_order" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "mapping"."tag_document" ADD CONSTRAINT "tag_document_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "mapping"."tag_document" ADD CONSTRAINT "tag_document_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "project_core"."document" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "mapping"."tag_sece" ADD CONSTRAINT "tag_sece_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "mapping"."tag_sece" ADD CONSTRAINT "tag_sece_sece_id_fkey" FOREIGN KEY ("sece_id") REFERENCES "reference_core"."sece" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."property_value" ADD CONSTRAINT "property_value_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "project_core"."tag" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."property_value" ADD CONSTRAINT "property_value_class_id_fkey" FOREIGN KEY ("class_id") REFERENCES "ontology_core"."class" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."property_value" ADD CONSTRAINT "property_value_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "ontology_core"."property" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "project_core"."property_value" ADD CONSTRAINT "property_value_mapping_id_fkey" FOREIGN KEY ("mapping_id") REFERENCES "ontology_core"."class_property" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;