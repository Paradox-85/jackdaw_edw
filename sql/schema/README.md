# sql/schema — Database Schema & Migrations

## Structure

```
sql/schema/
├── schema.sql          — Canonical table definitions (single source of truth)
├── README.md           — This file
└── migration/          — All migration scripts, ordered by number
```

## Running a Migration

```bash
psql -U postgres_admin -d engineering_core -f sql/schema/migration/migration_NNN_name.sql
```

Migrations are idempotent where noted in the file header.

---

## Active Migrations (001–022)

| # | File | Purpose |
|---|------|---------|
| 001 | `migration_001_tag_export_columns.sql` | Add export columns to project_core.tag |
| 002 | `migration_002_fix_purchase_order_unique.sql` | Fix UNIQUE constraint on purchase_order |
| 003 | `migration_003_export_validation_rules.sql` | Create audit_core.export_validation_rule + audit_core.validation_result; seed 42 base rules |
| 004 | `migration_004_fix_nan_strings_rule.sql` | Fix NO_NAN_STRINGS rule: icontains → regex exact match |
| 005 | `migration_005_validation_rule_schema_v2.sql` | ADD tier, category, check_type, source_ref, sort_order to rule table |
| 006 | `migration_006_update_existing_rules.sql` | Backfill tier/category/check_type on all 42 existing rules |
| 007 | `migration_007_new_validation_rules.sql` | INSERT 27 new rules (L0×3, L1×8, L2×9, L3×6, L4×2) |
| 008 | `migration_008_property_value_rules.sql` | INSERT 10 rules for scopes tag_property and equipment_property |
| 009 | `migration_009_validation_rules_cleanup.sql` | DELETE 5 duplicate rules; UPDATE 6 rules; INSERT 6 new rules |
| 010 | `migration_010_pseudo_null_expansion.sql` | Expand pseudo-null detection rules |
| 011 | `migration_011_report_catalogue_viewer_role.sql` | Add audit_core.report_metadata; grant edw_viewer role |
| 012 | `migration_012_app_core.sql` | Create app_core schema and ui_user table |
| 013 | `migration_013_add_count_exported.sql` | ADD count_exported to audit_core.sync_run_stats |
| 014 | `migration_014_crs_module.sql` | Create CRS module tables: crs_comment, crs_validation_query |
| 015 | `migration_015_crs_add_document_number.sql` | ADD document_number to audit_core.crs_comment |
| 016 | `migration_016_crs_add_from_to_tag.sql` | ADD from_tag / to_tag to audit_core.crs_comment |
| 017 | `migration_017_crs_phase2.sql` | CRS Phase 2 additions (property_name, tag_id FK, indexes) |
| 018 | `migration_018_crs_templates.sql` | CREATE audit_core.crs_comment_template table |
| 019 | `migration_019_crs_audit_reset_type.sql` | ADD reset_type to audit_core.crs_comment |
| 020 | `migration_020_crs_template_short_text.sql` | ADD short_template_text to audit_core.crs_comment_template |
| 021 | `migration_021_add_crs_llm_staging.sql` | CREATE audit_core.crs_llm_template_staging table |
| 022 | `migration_022_crs_template_harmonisation.sql` | Harmonise crs_comment_template: fix check_type, reformat category to 3-digit CRS-C001..C229, assign unique codes to 179 old-format rows, DROP domain/category_code/response_template |

---

## Naming Convention

```
migration_NNN_snake_case_description.sql
```

- `NNN` — zero-padded 3-digit sequence number (001, 002, ..., 022)
- Name describes the primary change in snake_case
- All DDL migrations include `BEGIN; ... COMMIT;`
- Idempotency noted in file header where guaranteed

---

## Candidates for Deletion

These files are legacy seeds or superseded attempts. They have been **renamed** with the
`_CANDIDATE_FOR_DELETION.sql` suffix and kept for reference. Do **not** run them.

| File | Reason |
|------|--------|
| `migration_018_crs_categories_seed_CANDIDATE_FOR_DELETION.sql` | Legacy data seed — superseded by migration_022 |
| `migration_018-2_crs_categories_extended_CANDIDATE_FOR_DELETION.sql` | Non-standard name; legacy data seed |
| `migration_019_crs_comment_templates_CANDIDATE_FOR_DELETION.sql` | Legacy master template seed — superseded by migration_022 |
| `migration_020_crs_harmonize_templates_CANDIDATE_FOR_DELETION.sql` | Incorrect logic: sets category to long text instead of CRS-Cxx codes |
| `migration_021_crs_short_text_seed_CANDIDATE_FOR_DELETION.sql` | Legacy data seed — superseded by migration_022 |
| `migration_023_clean_llm_entries_CANDIDATE_FOR_DELETION.sql` | Legacy cleanup — already applied or no longer needed |
| `migration_024_crs_check_type_domain_update_CANDIDATE_FOR_DELETION.sql` | Partial fix — superseded by migration_022 |
| `migration_025_template_harmonization_CANDIDATE_FOR_DELETION.sql` | Earlier attempt at harmonisation — replaced by migration_022 |
