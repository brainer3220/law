import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from packages.legal_tools.workspace import schemas
from packages.legal_tools.workspace.models import Project
from packages.legal_tools.workspace.service import (
    WorkspaceDatabase,
    WorkspaceService,
    WorkspaceSettings,
    init_engine,
)


@pytest.fixture()
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "workspace.db"


def _build_service(db_path: Path, **settings_overrides):
    settings = WorkspaceSettings(
        database_url=f"sqlite:///{db_path}",
        **settings_overrides,
    )
    engine = init_engine(settings)
    WorkspaceDatabase(engine).create_all()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()

    service = WorkspaceService(session=session, settings=settings)

    def _teardown():
        session.close()
        engine.dispose()

    return service, _teardown


def test_workspace_settings_from_env(monkeypatch):
    monkeypatch.setenv("LAW_SHARE_DB_URL", "postgres://user:pass@db/test")
    monkeypatch.setenv("LAW_ENABLE_AUDIT", "false")
    monkeypatch.setenv("LAW_WORKSPACE_AUTO_CREATE_DEFAULT_ORG", "true")

    settings = WorkspaceSettings.from_env()

    assert settings.database_url == "postgres://user:pass@db/test"
    assert settings.enable_audit is False
    assert settings.auto_create_default_org is True


def test_init_engine_normalizes_urls(monkeypatch):
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return "fake-engine"

    monkeypatch.setattr("packages.legal_tools.workspace.service.create_engine", fake_create_engine)

    settings = WorkspaceSettings(database_url="postgres://user:pass@host/db")
    engine = init_engine(settings)

    assert engine == "fake-engine"
    assert captured["url"] == "postgresql+psycopg://user:pass@host/db"
    assert captured["kwargs"]["pool_pre_ping"] is True


def test_create_project_sets_defaults(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        request = schemas.ProjectCreateRequest(name="Workspace", description="Desc")
        creator = uuid.uuid4()

        project = service.create_project(request, creator)

        assert isinstance(project, Project)
        assert project.status == "active"
        assert project.org_id is None

        members = service.list_members(project.id, creator)
        assert len(members) == 1
        assert members[0].user_id == creator
        assert str(members[0].role) == "owner"
    finally:
        cleanup()


def test_create_project_auto_creates_default_org(temp_db_path):
    service, cleanup = _build_service(temp_db_path, auto_create_default_org=True)
    try:
        creator = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="Org project"),
            creator,
        )

        assert project.org_id is not None
    finally:
        cleanup()


def test_update_project_changes_status(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        creator = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="To update"),
            creator,
        )

        updated = service.update_project(
            project.id,
            schemas.ProjectUpdateRequest(status="planning", description="Revised"),
            creator,
        )

        assert updated.status == "planning"
        assert updated.description == "Revised"
    finally:
        cleanup()


def test_clone_project_duplicates_description(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        creator = uuid.uuid4()
        original = service.create_project(
            schemas.ProjectCreateRequest(name="Original", description="Keep", status="blocked"),
            creator,
        )

        clone = service.clone_project(
            original.id,
            schemas.ProjectCloneRequest(name="Clone"),
            creator,
        )

        assert clone.name == "Clone"
        assert clone.description == "Keep"
        assert clone.status == "blocked"
        assert clone.archived is False
    finally:
        cleanup()


def test_delete_project_soft_archives(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        creator = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="Delete me"),
            creator,
        )

        service.delete_project(project.id, creator, hard_delete=False)

        refreshed = service.get_project(project.id, creator)
        assert refreshed.archived is True
    finally:
        cleanup()


def test_create_instruction_increments_version(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        creator = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="Instructional"),
            creator,
        )

        first = service.create_instruction(
            project.id,
            schemas.InstructionCreateRequest(content="v1"),
            creator,
        )
        second = service.create_instruction(
            project.id,
            schemas.InstructionCreateRequest(content="v2"),
            creator,
        )

        assert first.version == 1
        assert second.version == 2
        instructions = service.list_instructions(project.id, creator)
        assert [i.version for i in instructions] == [2, 1]
    finally:
        cleanup()


def test_instruction_queries_require_membership(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        owner = uuid.uuid4()
        outsider = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="Restricted"),
            owner,
        )

        with pytest.raises(PermissionError):
            service.list_instructions(project.id, outsider)
    finally:
        cleanup()


def test_create_update_records_entry(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        creator = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="Updated project"),
            creator,
        )

        update = service.create_update(
            project.id,
            schemas.UpdateCreateRequest(body="Initial release planned"),
            creator,
        )

        assert update.body == "Initial release planned"
        updates = service.list_updates(project.id, creator)
        assert updates[0].id == update.id
    finally:
        cleanup()


def test_create_update_requires_body_or_attachment(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        creator = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="Update validation"),
            creator,
        )

        with pytest.raises(ValueError):
            service.create_update(project.id, schemas.UpdateCreateRequest(), creator)
    finally:
        cleanup()


def test_updates_require_membership(temp_db_path):
    service, cleanup = _build_service(temp_db_path)
    try:
        owner = uuid.uuid4()
        outsider = uuid.uuid4()
        project = service.create_project(
            schemas.ProjectCreateRequest(name="Restricted updates"),
            owner,
        )

        service.create_update(
            project.id,
            schemas.UpdateCreateRequest(body="Owner only"),
            owner,
        )

        with pytest.raises(PermissionError):
            service.list_updates(project.id, outsider)
    finally:
        cleanup()
