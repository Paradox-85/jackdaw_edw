# Database Schema Change Workflow

MANDATORY: Use this command before making any database schema changes.

## Process
1. **Read** `sql/schema.sql` for current state.
2. **Validate** with pgedge MCP:
   ```sql
   SELECT * FROM information_schema.tables WHERE table_schema = 'project_core';
   SELECT * FROM information_schema.table_constraints;
   ```
3. **Use subagent (schema-validator)** for conflict analysis.
4. **Implement** change (DDL or migration).
5. **Update** `schema.sql` immediately after — same commit.
6. **Verify**: `pg_dump -d edw_db -s > /tmp/current.sql && diff /tmp/current.sql sql/schema.sql`

## Commit message template
```
[sql] <short description>

- Changed: <table/column/index>
- Purpose: <business reason>
- FK: <if applicable>
- Verified with pgedge MCP and schema.sql diff clean
```
