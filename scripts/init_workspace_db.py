#!/usr/bin/env python3
"""Initialize workspace database with default data."""

from __future__ import annotations

import sys
import uuid

from sqlalchemy import text

from packages.legal_tools.workspace.service import WorkspaceSettings, init_engine
from packages.legal_tools.workspace.models import Organization, Project


def init_workspace_db():
    """Initialize workspace database with default organization."""
    settings = WorkspaceSettings.from_env()
    engine = init_engine(settings)
    
    with engine.begin() as conn:
        # Check if default organization exists
        result = conn.execute(
            text("SELECT id FROM organizations WHERE name = 'Default Organization'")
        )
        org_row = result.fetchone()
        
        if org_row:
            org_id = org_row[0]
            print(f"✓ Default organization already exists (ID: {org_id})")
        else:
            # Create default organization
            org_id = uuid.uuid4()
            conn.execute(
                text("""
                    INSERT INTO organizations (id, name)
                    VALUES (:id, :name)
                """),
                {"id": org_id, "name": "Default Organization"}
            )
            print(f"✓ Created default organization (ID: {org_id})")
        
        # Create demo user if not exists (for testing)
        demo_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        result = conn.execute(
            text("SELECT id FROM auth.users WHERE id = :id"),
            {"id": demo_user_id}
        )
        if not result.fetchone():
            conn.execute(
                text("""
                    INSERT INTO auth.users (id, email, encrypted_password)
                    VALUES (:id, :email, :password)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": demo_user_id,
                    "email": "demo@example.com",
                    "password": "dummy"  # This is just for demo, not real auth
                }
            )
            print(f"✓ Created demo user (ID: {demo_user_id})")
        else:
            print(f"✓ Demo user already exists (ID: {demo_user_id})")
        
        # Create a demo project
        result = conn.execute(
            text("SELECT COUNT(*) FROM projects WHERE org_id = :org_id"),
            {"org_id": org_id}
        )
        project_count = result.scalar()
        
        if project_count == 0:
            project_id = uuid.uuid4()
            conn.execute(
                text("""
                    INSERT INTO projects (id, org_id, name, description, created_by)
                    VALUES (:id, :org_id, :name, :description, :created_by)
                """),
                {
                    "id": project_id,
                    "org_id": org_id,
                    "name": "Demo Project",
                    "description": "This is a demo project to test the workspace functionality",
                    "created_by": demo_user_id
                }
            )
            
            # Add demo user as project member
            conn.execute(
                text("""
                    INSERT INTO project_members (project_id, user_id, role)
                    VALUES (:project_id, :user_id, :role)
                """),
                {
                    "project_id": project_id,
                    "user_id": demo_user_id,
                    "role": "owner"
                }
            )
            print(f"✓ Created demo project (ID: {project_id})")
        else:
            print(f"✓ {project_count} project(s) already exist")
    
    print("\n✅ Workspace database initialized successfully!")
    print(f"\n📝 Demo user ID: {demo_user_id}")
    print("   Use this ID in the X-User-ID header for testing")


if __name__ == "__main__":
    try:
        init_workspace_db()
    except Exception as e:
        print(f"❌ Initialization failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
