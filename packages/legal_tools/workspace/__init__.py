"""Workspace data models and helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AuditLog",
    "Base",
    "Document",
    "DocumentChunk",
    "File",
    "Instruction",
    "Memory",
    "Organization",
    "Permission",
    "PermissionRole",
    "PrincipalType",
    "Project",
    "ProjectBudget",
    "ProjectChat",
    "ProjectMember",
    "RedactionRule",
    "RedactionRun",
    "RedactionRunItem",
    "ResourceType",
    "SensitivityLevel",
    "ShareLink",
    "ShareMode",
    "Snapshot",
    "SnapshotFile",
    "UsageLedger",
    "permission_role_enum",
    "principal_type_enum",
    "resource_type_enum",
    "sensitivity_level_enum",
    "share_mode_enum",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin import shim
    if name in __all__:
        module = import_module(".models", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:  # pragma: no cover - introspection helper
    return sorted(__all__ + ["schema"])
