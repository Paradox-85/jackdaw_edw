Manage a schema-related change safely.

## Rules
1. `sql/schema/schema.sql` is the canonical schema file and MUST be updated for every schema-related change
2. NEVER modify the database directly — not via MCP, not via Python, not via Bash/psql
3. Database access is READ-ONLY only
4. Schema changes must exist as repository artifacts first; actual DB execution is outside Claude Code

## Workflow
1. Read the relevant code, SQL, and docs
2. Determine what schema-related logic changed
3. Update `sql/schema/schema.sql`
4. Update any affected code, mappings, docs, or tests
5. Show the exact diff
6. Verify that `sql/schema/schema.sql` is staged before commit

## Verification
```bash
git diff -- sql/schema/schema.sql
git diff --cached --name-only | grep "sql/schema/schema.sql"
```
