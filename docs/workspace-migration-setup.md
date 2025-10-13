# Workspace Migration Setup

## Overview
The SQL migration file `20240308000000_project_workspace_schema.sql` has been successfully integrated into the workspace migration system.

## Changes Made

### 1. Migration File Location
- **Original location**: `supabase/migrations/20240308000000_project_workspace_schema.sql`
- **New location**: `packages/legal_tools/workspace/migrations/007_project_workspace_schema.sql`
- **Naming convention**: Changed from timestamp-based (`20240308000000_`) to sequential numbering (`007_`)

### 2. Migration Script Compatibility
The existing `scripts/run_workspace_migrations.py` script will now:
- Detect the new migration file automatically
- Apply it in the correct order (after migration 006)
- Execute all SQL statements within a transaction

## How to Run Migrations

### Prerequisites
Ensure the workspace database settings are configured in your environment:
```bash
export WORKSPACE_DB_URL="postgresql://user:pass@host:port/dbname"
```

### Execute Migrations
```bash
cd /Users/brainer/Programming/law
uv run python scripts/run_workspace_migrations.py
```

### Expected Output
```
Found 8 migration file(s)
Applying migration: 000_create_enums.sql...
✓ 000_create_enums.sql applied successfully
Applying migration: 001_add_archived_description.sql...
✓ 001_add_archived_description.sql applied successfully
...
Applying migration: 007_project_workspace_schema.sql...
✓ 007_project_workspace_schema.sql applied successfully
All migrations applied successfully!
```

## Migration Content Summary

The `007_project_workspace_schema.sql` migration performs:

1. **Cleanup**: Drops legacy tables and views
   - `v_project_search`, `usage_ledger`, `project_budgets`, etc.

2. **Schema Reset**: Recreates core workspace tables
   - `organizations`: Base organization entities
   - `projects`: Workspace projects with archival support
   - `project_members`: User memberships with role-based access
   - `project_update_files`: File metadata for project updates
   - `updates`: Project timeline updates
   - `instructions`: Project-specific AI instructions

3. **Relationships**: Establishes foreign keys between entities

4. **Extensions**: Ensures required PostgreSQL extensions
   - `pgcrypto`, `pg_trgm`, `unaccent`

## Notes

- All migrations run within a single transaction (`engine.begin()`)
- If any migration fails, all changes are rolled back
- The script applies migrations in alphabetical order
- Migration files should follow the pattern: `NNN_description.sql`

## Troubleshooting

### Migration Already Applied
If tables already exist, the migration may fail. Options:
1. Drop tables manually before running
2. Modify migration to use `CREATE TABLE IF NOT EXISTS`
3. Skip this migration if schema is already current

### Connection Issues
Verify database connectivity:
```bash
uv run python -c "from law_shared.legal_tools.workspace.service import WorkspaceSettings, init_engine; engine = init_engine(WorkspaceSettings.from_env()); print('✓ Connected')"
```
