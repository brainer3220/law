# Workspace Schema Cleanup Summary

## Overview
Removed duplicate and legacy models to align with migration `007_project_workspace_schema.sql`.

## Changes Made

### 1. Models Removed (per migration 007)
The following model files were **deleted** as they no longer exist in the new schema:
- `packages/legal_tools/workspace/models/audit.py` (AuditLog)
- `packages/legal_tools/workspace/models/budget.py` (ProjectBudget)
- `packages/legal_tools/workspace/models/chats.py` (ProjectChat)
- `packages/legal_tools/workspace/models/redaction.py` (RedactionRule, RedactionRun, RedactionRunItem)
- `packages/legal_tools/workspace/models/sharing.py` (Permission, ShareLink)
- `packages/legal_tools/workspace/models/snapshots.py` (Snapshot, SnapshotFile)
- `packages/legal_tools/workspace/models/usage.py` (UsageLedger)
- `packages/legal_tools/workspace/models/legacy.py` (Memory, File, Document, DocumentChunk)

### 2. Models Kept (per migration 007)
The following models remain and match the new schema:
- **Base**: `Base`, `PermissionRole`, `permission_role_enum()`
- **Projects**: `Organization`, `Project`, `ProjectMember`
- **Content**: `Instruction`, `ProjectUpdateFile`, `Update`

### 3. Enums Simplified
Removed legacy enums from `packages/legal_tools/workspace/schema/enums.py`:
- ❌ `SensitivityLevel`
- ❌ `ShareMode`
- ❌ `PrincipalType`
- ❌ `ResourceType`
- ✓ `PermissionRole` (kept - only enum in new schema)

### 4. Updated Files
- `packages/legal_tools/workspace/models/__init__.py` - Exports only core models
- `packages/legal_tools/workspace/models/base.py` - Only PermissionRole enum
- `packages/legal_tools/workspace/schema/enums.py` - Removed legacy enums
- `packages/legal_tools/workspace/service.py` - Updated imports (methods still need refactoring)

## Known Issues / TODO

### Service Layer Needs Refactoring
The `packages/legal_tools/workspace/service.py` file has been updated to import only the new models, but **many methods still reference removed models** and will cause runtime errors:

**Methods using removed Memory model:**
- `create_memory()`
- `list_memories()`
- `get_memory()`
- `update_memory()`
- `delete_memory()`

**Methods using removed File model:**
- `upload_file()`
- `list_files()`
- `get_file()`
- `delete_file()`

**Methods using removed ProjectChat model:**
- `list_chats()`
- `create_chat()`
- `get_chat()`
- `update_chat()`

**Methods using removed Snapshot model:**
- `create_snapshot()`
- `list_snapshots()`
- `get_snapshot()`

**Methods using removed AuditLog model:**
- `log_audit()`
- `list_audit_logs()`

**Methods using removed Budget/Usage models:**
- `get_budget()`
- `update_budget()`
- `log_usage()`
- `get_usage_summary()`

### Next Steps
1. **Decision needed**: Should these methods be:
   - Removed entirely?
   - Refactored to work with the new schema (Updates/ProjectUpdateFiles)?
   - Moved to a separate legacy service?

2. **Update tests**: `tests/workspace/test_service.py` will need updates to match new schema

3. **Update API endpoints**: Any REST/GraphQL endpoints using these models need updates

## Migration Alignment
This cleanup ensures the ORM models match the database schema defined in:
- `packages/legal_tools/workspace/migrations/007_project_workspace_schema.sql`

## Backup
A backup of the original service.py was created at:
- `packages/legal_tools/workspace/service.py.backup`
