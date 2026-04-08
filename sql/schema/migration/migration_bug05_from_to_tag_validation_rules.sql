/*
Fix: BUG-05 — Добавление правила валидации для self-loop соединений
Date: 2026-04-08
Purpose: Выявление tag connections где FROM_TAG = TO_TAG.
Note:    Это правило full scan only (is_builtin=false), non-blocking.
         Фактическая фильтрация происходит в transform_tag_connections().
*/

INSERT INTO audit_core.export_validation_rule (
    id, rule_code, scope, object_field, description,
    rule_expression, fix_expression,
    is_builtin, is_blocking, severity, object_status,
    tier, category, source_ref, check_type, sort_order
) VALUES (
    gen_random_uuid(),
    'FROM_TO_TAG_NOT_EQUAL',
    'tag',
    'FROM_TAG_NAME',
    'FROM_TAG and TO_TAG must not be equal — self-referencing connections are invalid.',
    'FROM_TAG_NAME == TO_TAG_NAME',
    NULL,
    FALSE,
    FALSE,
    'Warning',
    'Active',
    'L3',
    'Topology',
    'JDAW-KVE-E-JA-6944-00001-006',
    'dsl',
    70
) ON CONFLICT (rule_code) DO NOTHING;
