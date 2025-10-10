import enum
import sys
import types
import uuid
from dataclasses import dataclass
from typing import Any

import pytest
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.exc import IntegrityError

if "packages.legal_tools.workspace.models" not in sys.modules:
    models_stub = types.ModuleType("packages.legal_tools.workspace.models")

    class _WorkspaceEnum(str, enum.Enum):
        def __str__(self):
            return self.value

    class PermissionRole(_WorkspaceEnum):
        OWNER = "owner"
        MAINTAINER = "maintainer"
        EDITOR = "editor"
        COMMENTER = "commenter"
        VIEWER = "viewer"

    class SensitivityLevel(_WorkspaceEnum):
        PUBLIC = "public"
        INTERNAL = "internal"
        RESTRICTED = "restricted"
        SECRET = "secret"

    class ShareMode(_WorkspaceEnum):
        PRIVATE = "private"
        ORG = "org"
        LINK = "link"
        DOMAIN = "domain"

    class PrincipalType(_WorkspaceEnum):
        USER = "user"
        ORG = "org"
        DOMAIN = "domain"
        GROUP = "group"
        LINK = "link"

    class ResourceType(_WorkspaceEnum):
        PROJECT = "project"
        FILE = "file"
        DOCUMENT = "document"
        MEMORY = "memory"
        INSTRUCTION = "instruction"
        CHAT = "chat"
        SNAPSHOT = "snapshot"

    Base = orm.declarative_base()

    class _SimpleModel:
        def __init__(self, **attrs):
            for key, value in attrs.items():
                setattr(self, key, value)

    class Project(_SimpleModel):
        def __init__(self, **attrs):
            super().__init__(**attrs)
            self.memories = list(getattr(self, "memories", []))

    class ProjectMember(Base):
        __tablename__ = "project_members"

        project_id = sa.Column(sa.String, primary_key=True)
        user_id = sa.Column(sa.String, primary_key=True)
        role = sa.Column(sa.String, nullable=False)
        invited_by = sa.Column(sa.String, nullable=True)

        def __init__(self, project_id, user_id, role, invited_by=None):
            super().__init__()
            self.project_id = project_id
            self.user_id = user_id
            self.role = role
            self.invited_by = invited_by

    class Instruction(_SimpleModel):
        pass

    class Memory(_SimpleModel):
        pass

    class File(_SimpleModel):
        pass

    class Snapshot(_SimpleModel):
        pass

    class AuditLog:
        def __init__(
            self,
            project_id,
            actor_user_id,
            action,
            resource_type=None,
            resource_id=None,
            meta=None,
        ):
            self.project_id = project_id
            self.actor_user_id = actor_user_id
            self.action = action
            self.resource_type = resource_type
            self.resource_id = resource_id
            self.meta = meta or {}

    class ProjectBudget(_SimpleModel):
        pass

    class UsageLedger(_SimpleModel):
        pass

    models_stub.Base = Base
    models_stub.Project = Project
    models_stub.ProjectMember = ProjectMember
    models_stub.Instruction = Instruction
    models_stub.Memory = Memory
    models_stub.File = File
    models_stub.Snapshot = Snapshot
    models_stub.AuditLog = AuditLog
    models_stub.ProjectBudget = ProjectBudget
    models_stub.UsageLedger = UsageLedger
    models_stub.PermissionRole = PermissionRole
    models_stub.SensitivityLevel = SensitivityLevel
    models_stub.ShareMode = ShareMode
    models_stub.PrincipalType = PrincipalType
    models_stub.ResourceType = ResourceType
    models_stub.permission_role_enum = lambda: None
    models_stub.sensitivity_level_enum = lambda: None
    models_stub.share_mode_enum = lambda: None
    models_stub.principal_type_enum = lambda: None
    models_stub.resource_type_enum = lambda: None

    sys.modules["packages.legal_tools.workspace.models"] = models_stub

if not hasattr(orm, "DeclarativeBase"):  # Compat for SQLAlchemy < 2.0 in test envs
    _mapper_registry = orm.registry()

    class DeclarativeBase:
        """Minimal stand-in for SQLAlchemy 2.0 DeclarativeBase."""

        __abstract__ = True
        registry = _mapper_registry
        metadata = _mapper_registry.metadata

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            if cls is DeclarativeBase:
                return
            if getattr(cls, "__abstract__", False):
                return
            if "__tablename__" in cls.__dict__ or "__table__" in cls.__dict__:
                _mapper_registry.map_declaratively(cls)
            else:
                cls.__abstract__ = True

    orm.DeclarativeBase = DeclarativeBase

if not hasattr(orm, "Mapped"):  # pragma: no cover - typing shim
    orm.Mapped = Any

if not hasattr(orm, "mapped_column"):  # pragma: no cover - SQLAlchemy < 2.0 shim
    def mapped_column(*args, **kwargs):
        return sa.Column(*args, **kwargs)

    orm.mapped_column = mapped_column

from packages.legal_tools.workspace import service as workspace_service
from packages.legal_tools.workspace.models import AuditLog, PermissionRole, ProjectMember
from packages.legal_tools.workspace.service import WorkspaceService, WorkspaceSettings, init_engine


@dataclass
class MemberAddRequest:
    user_id: uuid.UUID
    role: PermissionRole


class _ScalarResult:
    """Mimic SQLAlchemy ScalarResult for stub sessions."""

    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        return self._value


class _PermissionSession:
    """Stub session returning a predefined project member."""

    def __init__(self, member):
        self._member = member
        self.last_statement = None

    def execute(self, statement):
        self.last_statement = statement
        return _ScalarResult(self._member)


class _RecordingSession:
    """Session stub capturing added objects and commit calls."""

    def __init__(self, commit_exception: Exception | None = None):
        self.added: list[object] = []
        self.commit_calls = 0
        self._commit_exception = commit_exception

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commit_calls += 1
        if self._commit_exception:
            raise self._commit_exception


def test_workspace_settings_from_env(monkeypatch):
    monkeypatch.setenv("LAW_SHARE_DB_URL", "postgres://user:pass@db/test")
    monkeypatch.setenv("LAW_ENABLE_AUDIT", "false")
    monkeypatch.setenv("LAW_ENABLE_BUDGET_CHECK", "false")

    settings = WorkspaceSettings.from_env()

    assert settings.database_url == "postgres://user:pass@db/test"
    assert settings.enable_audit is False
    assert settings.enable_budget_check is False


def test_workspace_settings_from_env_missing(monkeypatch):
    monkeypatch.delenv("LAW_SHARE_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError):
        WorkspaceSettings.from_env()


@pytest.mark.parametrize(
    ("input_url", "expected_url"),
    [
        ("postgres://user:pass@host/db", "postgresql+psycopg://user:pass@host/db"),
        ("postgresql://user:pass@host/db", "postgresql+psycopg://user:pass@host/db"),
        ("sqlite:///tmp.db", "sqlite:///tmp.db"),
    ],
)
def test_init_engine_normalizes_urls(monkeypatch, input_url, expected_url):
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return "fake-engine"

    monkeypatch.setattr(workspace_service, "create_engine", fake_create_engine)
    settings = WorkspaceSettings(database_url=input_url)

    engine = init_engine(settings)

    assert engine == "fake-engine"
    assert captured["url"] == expected_url
    assert captured["kwargs"]["pool_pre_ping"] is True
    assert captured["kwargs"]["pool_size"] == 10
    assert captured["kwargs"]["max_overflow"] == 20


def test_check_permission_allows_sufficient_role():
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=PermissionRole.OWNER,
    )
    session = _PermissionSession(member)
    service = WorkspaceService(
        session=session,
        settings=WorkspaceSettings(database_url="postgresql://test"),
    )

    result = service._check_permission(project_id, user_id, PermissionRole.MAINTAINER)

    assert result is member


def test_check_permission_raises_for_non_member():
    service = WorkspaceService(
        session=_PermissionSession(member=None),
        settings=WorkspaceSettings(database_url="postgresql://test"),
    )

    with pytest.raises(PermissionError, match="Not a project member"):
        service._check_permission(uuid.uuid4(), uuid.uuid4(), PermissionRole.VIEWER)


def test_check_permission_raises_for_insufficient_role():
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=PermissionRole.VIEWER,
    )
    service = WorkspaceService(
        session=_PermissionSession(member=member),
        settings=WorkspaceSettings(database_url="postgresql://test"),
    )

    with pytest.raises(PermissionError, match="Requires maintainer"):
        service._check_permission(project_id, user_id, PermissionRole.MAINTAINER)


def test_log_audit_records_entry_when_enabled():
    project_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    session = _RecordingSession()
    service = WorkspaceService(
        session=session,
        settings=WorkspaceSettings(database_url="postgresql://test", enable_audit=True),
    )

    service._log_audit(
        project_id=project_id,
        actor_id=actor_id,
        action="project.created",
        resource_type="project",
        resource_id=str(project_id),
        meta={"foo": "bar"},
    )

    assert len(session.added) == 1
    log = session.added[0]
    assert isinstance(log, AuditLog)
    assert log.project_id == project_id
    assert log.actor_user_id == actor_id
    assert log.action == "project.created"
    assert log.meta == {"foo": "bar"}


def test_log_audit_noop_when_disabled():
    session = _RecordingSession()
    service = WorkspaceService(
        session=session,
        settings=WorkspaceSettings(database_url="postgresql://test", enable_audit=False),
    )

    service._log_audit(
        project_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        action="project.created",
    )

    assert session.added == []


def test_add_member_persists_and_logs(monkeypatch):
    project_id = uuid.uuid4()
    inviter_id = uuid.uuid4()
    new_user_id = uuid.uuid4()
    session = _RecordingSession()
    service = WorkspaceService(
        session=session,
        settings=WorkspaceSettings(database_url="postgresql://test", enable_audit=True),
    )
    monkeypatch.setattr(service, "_check_permission", lambda *args, **kwargs: None)
    request = MemberAddRequest(user_id=new_user_id, role=PermissionRole.EDITOR)

    member = service.add_member(project_id, request, inviter_id)

    assert isinstance(member, ProjectMember)
    assert member.project_id == project_id
    assert member.user_id == new_user_id
    assert member.invited_by == inviter_id
    assert session.commit_calls == 1
    assert len(session.added) == 2
    first_obj, audit_obj = session.added
    assert first_obj is member
    assert isinstance(audit_obj, AuditLog)
    assert audit_obj.action == "member.added"
    assert audit_obj.meta == {"role": request.role.value}


def test_add_member_raises_for_duplicate(monkeypatch):
    project_id = uuid.uuid4()
    inviter_id = uuid.uuid4()
    session = _RecordingSession(
        commit_exception=IntegrityError("stmt", params=None, orig=None)
    )
    service = WorkspaceService(
        session=session,
        settings=WorkspaceSettings(database_url="postgresql://test", enable_audit=True),
    )
    monkeypatch.setattr(service, "_check_permission", lambda *args, **kwargs: None)
    request = MemberAddRequest(user_id=uuid.uuid4(), role=PermissionRole.VIEWER)

    with pytest.raises(ValueError, match="already a member"):
        service.add_member(project_id, request, inviter_id)

    assert session.commit_calls == 1
    assert len(session.added) == 1
