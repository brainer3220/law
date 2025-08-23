"""SQLAlchemy base and models for domain entities."""

from .base import Base
from .models import (
    Tenant,
    User,
    Role,
    Policy,
    Client,
    Matter,
    MatterMembership,
    Document,
    Chunk,
    Citation,
    QueryLog,
    AnswerLog,
    AuditEvent,
    Notification,
)
from .session import SessionLocal, engine, get_session

__all__ = [
    "Base",
    "Tenant",
    "User",
    "Role",
    "Policy",
    "Client",
    "Matter",
    "MatterMembership",
    "Document",
    "Chunk",
    "Citation",
    "QueryLog",
    "AnswerLog",
    "AuditEvent",
    "Notification",
    "SessionLocal",
    "engine",
    "get_session",
]

