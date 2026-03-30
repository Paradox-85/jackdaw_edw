---
description: MCP tool selection and fallback rules — when to use which MCP and what to do on failure
---
# MCP Decision Rules

## Selection Priority

| Need | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| DB schema, column names | pgedge `get_schema_info` | Read `sql/schema.sql` | STOP — never invent |
| DB data, cardinality | pgedge `query_database` | STOP — never estimate | — |
| Library API, framework docs | context7 | Search official docs via Bash | STOP |
| Architecture decision | pgedge first, then context7 | Both + Opus + ultrathink | — |

## Failure Handling (MANDATORY)

### pgedge unavailable
1. Try: read `sql/schema.sql` for column/table names
2. Say explicitly: "pgedge MCP unavailable — reading from sql/schema.sql"
3. NEVER invent column names — if not in schema.sql, ask user
4. NEVER run psql bash commands as substitute — pgedge is the safe path

### context7 returns empty
1. Try: Bash(curl ...) for framework-specific docs (Prefect, Next.js official docs)
2. Try: Read pyproject.toml to find pinned library version, then search for that version's docs
3. NEVER invent API signatures — say "I couldn't find this in documentation, please verify"

### Both MCPs unavailable
STOP. Say: "Both pgedge and context7 are unavailable.
I cannot safely proceed with [task] without verifying [specific thing].
Options: (1) restore MCP access, (2) provide the schema/docs manually, (3) I proceed with explicit [assumption] — confirm?"

## Never
- Never substitute `curl https://ai-db.adzv-pt.dev/mcp/v1` for pgedge MCP calls
- Never query pgedge inside a row-processing loop (N+1)
- Never use context7 for project-specific data (DB schema, business logic) — that's pgedge's domain
