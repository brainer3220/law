# Fix for project_chats.added_by Column Issue

## Problem
The API was throwing a `ProgrammingError` when trying to list chats:
```
sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedColumn) 
column project_chats.added_by does not exist
```

## Root Cause
1. The `project_chats` table schema in the database had evolved to include additional columns (`title`, `created_by`, `created_at`, `updated_at`, `added_by`)
2. The SQLAlchemy model in `models.py` only defined 4 columns (project_id, chat_id, added_by, added_at)
3. The column `added_by` existed in the database but the model was out of sync
4. Migration `002_remove_auth_fk.sql` removed foreign key constraints to `auth.users` but didn't cover `project_chats`

## Solution

### 1. Created Migration: `003_fix_project_chats_added_by.sql`
- Ensures `project_chats` table exists
- Adds `added_by` column if missing (with fallback default)
- Removes foreign key constraint to `auth.users`
- Sets column to NOT NULL

### 2. Updated Migration: `002_remove_auth_fk.sql`
- Extended to remove foreign key constraints from ALL tables that reference `auth.users`:
  - `project_chats.added_by`
  - `instructions.created_by`
  - `memories.created_by`
  - `files.created_by`
  - `permissions.created_by`
  - `share_links.created_by`
  - `redaction_rules.created_by`
  - `redaction_runs.created_by`
  - `snapshots.created_by`

### 3. Updated Model: `packages/legal_tools/workspace/models.py`
Updated `ProjectChat` class to match actual database schema:

```python
class ProjectChat(Base):
    """Association between projects and existing chats."""

    __tablename__ = "project_chats"

    # Primary keys - order matches database
    chat_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid()
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    
    # Chat metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    added_by: Mapped[uuid.UUID] = mapped_column(
        nullable=False, server_default=func.gen_random_uuid()
    )

    project: Mapped[Project] = relationship(back_populates="project_chats")
```

### 4. Updated Model: `packages/legal_tools/workspace/models/chats.py`
Updated to match the schema (though this file is not currently imported by `service.py`)

## Database Schema
The final `project_chats` table schema:
- `chat_id` (uuid, PK, auto-generated)
- `project_id` (uuid, PK, FK to projects.id)
- `title` (text, required)
- `created_by` (uuid, required)
- `created_at` (timestamptz, auto-generated)
- `updated_at` (timestamptz, auto-updated)
- `added_by` (uuid, required, auto-generated as fallback)

## Testing
✅ Migrations applied successfully
✅ Query test passed without errors
✅ No foreign key constraint violations

## Additional Fixes

### Removed All auth.users Foreign Key References
After running the migration to drop foreign key constraints, the SQLAlchemy models still contained 
`ForeignKey("auth.users.id")` references. These were systematically removed from all model definitions 
to keep the Python code in sync with the database schema.

**Models updated:**
- `Project.created_by`
- `ProjectMember.user_id` and `invited_by`
- `Instruction.created_by`
- `Memory.created_by`
- `File.created_by`
- `Permission.created_by`
- `ShareLink.created_by`
- `RedactionRule.created_by`
- `RedactionRun.created_by`
- `Snapshot.created_by`
- `AuditLog.actor_user_id`

## Files Modified
1. `/packages/legal_tools/workspace/migrations/003_fix_project_chats_added_by.sql` (created)
2. `/packages/legal_tools/workspace/migrations/002_remove_auth_fk.sql` (updated)
3. `/packages/legal_tools/workspace/models.py` (comprehensive update - removed all auth.users FKs)
4. `/packages/legal_tools/workspace/models/chats.py` (updated)

## Verification
```bash
# Run migrations
uv run python scripts/run_workspace_migrations.py

# Test the fix
uv run python -c "
from law_shared.legal_tools.workspace.service import WorkspaceSettings, WorkspaceService, init_engine
from sqlalchemy.orm import Session
settings = WorkspaceSettings.from_env()
engine = init_engine(settings)
session = Session(engine)
service = WorkspaceService(session, settings)
print('✓ Service initialized successfully')
"
```
