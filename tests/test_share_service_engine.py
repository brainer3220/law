import types

from packages.legal_tools.share import service
from packages.legal_tools.share.service import ShareSettings, init_engine


def _setup_engine_stub(monkeypatch):
    captured: dict[str, object] = {}

    def fake_create_engine(url, **kwargs):  # type: ignore[no-untyped-def]
        captured["url"] = url
        captured["kwargs"] = kwargs
        engine = types.SimpleNamespace()
        captured["engine"] = engine
        return engine

    monkeypatch.setattr(service, "create_engine", fake_create_engine)
    monkeypatch.setattr(service.Base.metadata, "create_all", lambda engine: None)
    return captured


def test_init_engine_rewrites_postgresql_driver(monkeypatch):
    captured = _setup_engine_stub(monkeypatch)
    settings = ShareSettings(database_url="postgresql://user:pass@localhost:5432/db")

    engine = init_engine(settings)

    assert engine is captured["engine"]
    assert captured["url"] == "postgresql+psycopg://user:pass@localhost:5432/db"


def test_init_engine_upgrades_legacy_postgres_scheme(monkeypatch):
    captured = _setup_engine_stub(monkeypatch)
    settings = ShareSettings(database_url="postgres://user:pass@localhost:5432/db")

    init_engine(settings)

    assert captured["url"] == "postgresql+psycopg://user:pass@localhost:5432/db"
