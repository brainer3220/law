from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="tenant")
    matters = relationship("Matter", back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(Text)
    definition = Column(Text)  # OPA/Rego source or reference


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Matter(Base):
    __tablename__ = "matters"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    title = Column(String(255), nullable=False)
    status = Column(String(64), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="matters")


class MatterMembership(Base):
    __tablename__ = "matter_memberships"
    id = Column(Integer, primary_key=True)
    matter_id = Column(Integer, ForeignKey("matters.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(64), nullable=True)
    __table_args__ = (UniqueConstraint("matter_id", "user_id", name="uq_matter_user"),)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    matter_id = Column(Integer, ForeignKey("matters.id"), nullable=True)
    source = Column(String(128))
    hash = Column(String(64), index=True)
    sensitivity = Column(String(64))
    retention_policy = Column(String(128))
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    text = Column(Text, nullable=False)
    citation_anchor = Column(String(128))
    embedding = Column(JSON)  # placeholder; use pgvector in production
    created_at = Column(DateTime, default=datetime.utcnow)
    Index("ix_chunks_document", "document_id")


class Citation(Base):
    __tablename__ = "citations"
    id = Column(Integer, primary_key=True)
    chunk_id = Column(Integer, ForeignKey("chunks.id"), nullable=False)
    kind = Column(String(64))  # statute/case_law/reference
    reference = Column(String(512))  # link/article/case_no/page


class QueryLog(Base):
    __tablename__ = "queries"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    prompt = Column(Text, nullable=False)
    model = Column(String(128))
    version = Column(String(64))
    context_hash = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnswerLog(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=True)
    decision = Column(String(32))  # allow/deny
    findings = Column(JSON)  # policy evaluation results
    pii_masked_before = Column(Boolean, default=False)
    pii_masked_after = Column(Boolean, default=True)
    trace_id = Column(String(128), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    topic = Column(String(128))  # statutes/case_law/keyword
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

