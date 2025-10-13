"""Workspace SQLAlchemy models organized by domain.

This module reflects the simplified schema from migration 007_project_workspace_schema.sql.
Only the core workspace tables are included:
- organizations, projects, project_members
- instructions, project_update_files, updates
"""

from .base import (
    Base,
    PermissionRole,
    permission_role_enum,
)
from .content import Instruction, ProjectUpdateFile, Update
from .projects import Organization, Project, ProjectMember

__all__ = [
    # Base & Enums
    "Base",
    "PermissionRole",
    "permission_role_enum",
    # Projects
    "Organization",
    "Project",
    "ProjectMember",
    # Content
    "Instruction",
    "ProjectUpdateFile",
    "Update",
]
