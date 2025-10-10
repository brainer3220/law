#!/usr/bin/env python3
"""Apply database migrations for workspace schema."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

from packages.legal_tools.workspace.service import WorkspaceSettings, init_engine


def run_migrations():
    """Run all pending SQL migrations."""
    settings = WorkspaceSettings.from_env()
    engine = init_engine(settings)
    
    migrations_dir = Path(__file__).parent.parent / "packages" / "legal_tools" / "workspace" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("No migration files found.")
        return
    
    print(f"Found {len(migration_files)} migration file(s)")
    
    with engine.begin() as conn:
        for migration_file in migration_files:
            print(f"Applying migration: {migration_file.name}...")
            sql = migration_file.read_text()
            conn.execute(text(sql))
            print(f"✓ {migration_file.name} applied successfully")
    
    print("All migrations applied successfully!")


if __name__ == "__main__":
    try:
        run_migrations()
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
