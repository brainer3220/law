"""Canonical workspace enum definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

__all__ = [
    "EnumDefinition",
    "PermissionRole",
    "SensitivityLevel",
    "ShareMode",
    "PrincipalType",
    "ResourceType",
    "ENUM_DEFINITIONS",
    "ENUM_DEFINITION_BY_NAME",
    "render_enum_sql",
    "pg_enum",
]


class WorkspaceEnum(str, Enum):
    """Base class for workspace enums stored in PostgreSQL."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(item.value for item in cls)


class PermissionRole(WorkspaceEnum):
    OWNER = "owner"
    MAINTAINER = "maintainer"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"


class SensitivityLevel(WorkspaceEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    SECRET = "secret"


class ShareMode(WorkspaceEnum):
    PRIVATE = "private"
    ORG = "org"
    LINK = "link"
    DOMAIN = "domain"


class PrincipalType(WorkspaceEnum):
    USER = "user"
    ORG = "org"
    DOMAIN = "domain"
    GROUP = "group"
    LINK = "link"


class ResourceType(WorkspaceEnum):
    PROJECT = "project"
    FILE = "file"
    DOCUMENT = "document"
    MEMORY = "memory"
    INSTRUCTION = "instruction"
    CHAT = "chat"
    SNAPSHOT = "snapshot"


@dataclass(frozen=True)
class EnumDefinition:
    """Metadata describing a PostgreSQL enum type."""

    name: str
    values: tuple[str, ...]
    enum_cls: type[WorkspaceEnum]

    def render_sql(self) -> str:
        values_sql = ",".join(f"'{value}'" for value in self.values)
        return (
            "DO $$ BEGIN\n"
            f"  CREATE TYPE {self.name} AS ENUM ({values_sql});\n"
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        )


ENUM_DEFINITIONS: tuple[EnumDefinition, ...] = (
    EnumDefinition("permission_role", PermissionRole.values(), PermissionRole),
    EnumDefinition("sensitivity_level", SensitivityLevel.values(), SensitivityLevel),
    EnumDefinition("share_mode", ShareMode.values(), ShareMode),
    EnumDefinition("principal_type", PrincipalType.values(), PrincipalType),
    EnumDefinition("resource_type", ResourceType.values(), ResourceType),
)

ENUM_DEFINITION_BY_NAME: Mapping[str, EnumDefinition] = {
    definition.name: definition for definition in ENUM_DEFINITIONS
}

ENUM_DEFINITION_BY_CLASS: Mapping[type[WorkspaceEnum], EnumDefinition] = {
    definition.enum_cls: definition for definition in ENUM_DEFINITIONS
}


def render_enum_sql() -> str:
    """Return ``CREATE TYPE`` statements for all workspace enums."""

    return "\n\n".join(definition.render_sql() for definition in ENUM_DEFINITIONS)


def pg_enum(enum_cls: type[WorkspaceEnum]):
    """Return a SQLAlchemy ``ENUM`` tied to the canonical definition."""

    from sqlalchemy.dialects.postgresql import ENUM as PgEnum

    definition = ENUM_DEFINITION_BY_CLASS[enum_cls]
    return PgEnum(enum_cls, name=definition.name, create_type=False)
