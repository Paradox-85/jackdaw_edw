#!/usr/bin/env python3
"""
Execute CRS Migrations

Purpose: Apply all missing CRS (Comment Resolution System) migrations
          to bring the database schema in sync with schema.sql

Usage: python execute_crs_migrations.py
"""

import os
import psycopg2
from psycopg2 import sql, OperationalError
from pathlib import Path

# DB Connection Parameters (from config.yaml)
DB_HOST = "10.10.10.50"  # External IP for Docker service
DB_PORT = "5432"
DB_NAME = "engineering_core"
DB_USER = "postgres_admin"  # Admin user for schema changes
DB_PASSWORD = "***"  # Will use environment variable or config

def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", DB_PASSWORD))
    )

def execute_sql_file(conn, file_path):
    """Execute SQL file and return success status."""
    print(f"\n{'='*60}")
    print(f"Executing: {file_path}")
    print(f"{'='*60}")

    try:
        with conn.cursor() as cursor:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Execute SQL (may contain multiple statements)
            cursor.execute(sql_content)

        conn.commit()
        print(f"✅ Success: {file_path}")
        return True

    except OperationalError as e:
        print(f"❌ Error executing {file_path}: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Unexpected error in {file_path}: {e}")
        conn.rollback()
        return False

def verify_migration(conn):
    """Run verification queries."""
    print(f"\n{'='*60}")
    print("Running Verification Queries")
    print(f"{'='*60}\n")

    with conn.cursor() as cursor:

        # Check CRS tables
        print("📊 CRS Tables:")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'audit_core'
              AND table_name LIKE 'crs_%'
            ORDER BY table_name
        """)
        for row in cursor.fetchall():
            print(f"  ✅ {row[0]}")

        # Check views
        print("\n📊 CRS Views:")
        cursor.execute("""
            SELECT viewname
            FROM information_schema.views
            WHERE schemaname = 'project_core'
              AND viewname LIKE 'v_tag_%'
            ORDER BY viewname
        """)
        for row in cursor.fetchall():
            print(f"  ✅ {row[0]}")

        # Count rows in key tables
        print("\n📊 Table Row Counts:")
        cursor.execute("SELECT COUNT(*) FROM audit_core.crs_comment")
        count = cursor.fetchone()[0]
        print(f"  crs_comment: {count}")

        cursor.execute("SELECT COUNT(*) FROM audit_core.crs_validation_query")
        count = cursor.fetchone()[0]
        print(f"  crs_validation_query: {count}")

        cursor.execute("SELECT COUNT(*) FROM audit_core.crs_comment_template")
        count = cursor.fetchone()[0]
        print(f"  crs_comment_template: {count}")

        cursor.execute("SELECT COUNT(*) FROM audit_core.crs_llm_template_staging")
        count = cursor.fetchone()[0]
        print(f"  crs_llm_template_staging: {count}")

def main():
    """Main execution function."""
    print(f"{'='*60}")
    print(f"Applying CRS Migrations to {DB_NAME}")
    print(f"{'='*60}\n")

    # Get script directory
    script_dir = Path(__file__).parent
    sql_file = script_dir / "apply_crs_migrations.sql"

    if not sql_file.exists():
        print(f"❌ Error: {sql_file} not found")
        return 1

    print(f"Migration file: {sql_file}\n")

    # Execute migration
    conn = get_db_connection()
    try:
        success = execute_sql_file(conn, sql_file)
        if success:
            print(f"\n{'='*60}")
            print("✅ All CRS migrations applied successfully!")
            print(f"{'='*60}")

            # Run verification
            verify_migration(conn)

            return 0
        else:
            print(f"\n❌ Migration failed!")
            return 1

    finally:
        conn.close()

if __name__ == "__main__":
    exit(main())
