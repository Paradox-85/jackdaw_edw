#!/bin/bash
# =============================================================================
# Execute CRS Migrations
#
# Purpose: Apply all missing CRS (Comment Resolution System) migrations
#          to bring the database schema in sync with schema.sql
#
# Usage: bash execute_crs_migrations.sh
# =============================================================================

set -e  # Exit on error

# DB Connection Parameters
DB_HOST="10.10.10.50"
DB_PORT="5432"
DB_NAME="engineering_core"
DB_USER="ai_agent_user"

echo "======================================================"
echo "Applying CRS Migrations to ${DB_NAME}"
echo "======================================================"

# Function to execute SQL file
execute_sql() {
    echo "Executing: $1"
    PGPASSWORD=*** psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "$1"
    if [ $? -eq 0 ]; then
        echo "✅ Success: $1"
    else
        echo "❌ Failed: $1"
        exit 1
    fi
    echo ""
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/apply_crs_migrations.sql"

if [ ! -f "${SQL_FILE}" ]; then
    echo "❌ Error: ${SQL_FILE} not found"
    exit 1
fi

echo "======================================================"
echo "Migration file: ${SQL_FILE}"
echo "======================================================"
echo ""

# Execute the combined migration script
execute_sql "${SQL_FILE}"

echo "======================================================"
echo "✅ All CRS migrations applied successfully!"
echo "======================================================"

echo ""
echo "Running verification queries..."
echo ""

# Verification queries
PGPASSWORD=*** psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
-- Check all CRS tables created
SELECT 'CRS Tables' as check_type, table_name as result
FROM information_schema.tables
WHERE table_schema = 'audit_core' AND table_name LIKE 'crs_%'
ORDER BY table_name;

-- Check views created
SELECT 'CRS Views' as check_type, viewname as result
FROM information_schema.views
WHERE schemaname IN ('project_core')
ORDER BY viewname;

-- Count rows in key tables
SELECT 'Table Counts' as check_type, 'crs_comment: ' || COUNT(*) as result
FROM audit_core.crs_comment
UNION ALL
SELECT 'Table Counts', 'crs_validation_query: ' || COUNT(*)
FROM audit_core.crs_validation_query
UNION ALL
SELECT 'Table Counts', 'crs_comment_template: ' || COUNT(*)
FROM audit_core.crs_comment_template
UNION ALL
SELECT 'Table Counts', 'crs_llm_template_staging: ' || COUNT(*)
FROM audit_core.crs_llm_template_staging;
"

echo ""
echo "======================================================"
echo "✅ Verification complete!"
echo "======================================================"
