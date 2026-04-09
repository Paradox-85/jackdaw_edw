Compact context while preserving EDW-critical state.

Before compacting, produce a structured snapshot:

1. **Current task** — one sentence: what were we doing?
2. **Modified files** — list every file edited this session (exact paths)
3. **DB state** — schema changes made, tables affected, schema.sql updated? (yes/no)
4. **SCD2 state** — hash formula confirmed in use, which sync_status values were involved
5. **Pending decisions** — unresolved questions, TODOs, FK misses discovered
6. **Blockers** — anything that was failing or unclear
7. **Schema file status** — was `sql/schema/schema.sql` updated? if not, why not?
8. **DB safety reminder** — direct DB writes remain forbidden after resume
9. **Next step** — what is EXACT first action to take after context reset

Save snapshot to docs/plans/session-snapshot.md (overwrite each time).
Then run /compact using this snapshot as compaction instruction.
