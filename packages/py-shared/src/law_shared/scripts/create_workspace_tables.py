#!/usr/bin/env python3
"""Create all workspace tables in the database."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from law_shared.legal_tools.workspace.service import WorkspaceSettings, init_engine
from law_shared.legal_tools.workspace.models import Base


def create_tables():
    """Create all workspace tables."""
    settings = WorkspaceSettings.from_env()
    engine = init_engine(settings)
    
    print("Creating all workspace tables...")
    Base.metadata.create_all(engine)
    print("✓ All tables created successfully!")


if __name__ == "__main__":
    create_tables()
