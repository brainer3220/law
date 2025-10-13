from __future__ import annotations

import pytest


pytest.importorskip("langgraph")


from law_shared.legal_tools import multi_turn_chat as mtc


class DummyCheckpointer:
    def __init__(self) -> None:
        self.setup_called = False

    def setup(self) -> None:
        self.setup_called = True


class DummyContextManager:
    def __init__(self, checkpointer: DummyCheckpointer) -> None:
        self.checkpointer = checkpointer
        self.entered = False
        self.exited = False

    def __enter__(self) -> DummyCheckpointer:
        self.entered = True
        return self.checkpointer

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.exited = True


class DummyCompiledGraph:
    def invoke(self, *_args, **_kwargs) -> None:
        return None

    def get_state(self, _cfg):
        return None

    def get_state_history(self, _cfg):
        return []


def test_postgres_chat_manager_sets_up_checkpointer(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_checkpointer = DummyCheckpointer()
    ctx = DummyContextManager(dummy_checkpointer)

    def fake_from_conn_string(cls, db_uri: str):  # type: ignore[override]
        assert db_uri == "postgresql://example"
        return ctx

    monkeypatch.setattr(
        mtc.PostgresSaver,
        "from_conn_string",
        classmethod(fake_from_conn_string),
    )

    created_graphs = []

    class DummyStateGraph:
        def __init__(self, _state):
            created_graphs.append(self)

        def add_node(self, *_args, **_kwargs) -> None:
            return None

        def add_edge(self, *_args, **_kwargs) -> None:
            return None

        def compile(self, *, checkpointer):
            assert checkpointer is dummy_checkpointer
            return DummyCompiledGraph()

    monkeypatch.setattr(mtc, "StateGraph", DummyStateGraph)

    class DummyModel:
        def invoke(self, _messages):
            return {"role": "assistant", "content": "ok"}

    monkeypatch.setattr(mtc, "init_chat_model", lambda _model_id: DummyModel())

    config = mtc.PostgresChatConfig(db_uri="postgresql://example")

    manager = mtc.PostgresChatManager(config=config)

    assert ctx.entered is True
    assert dummy_checkpointer.setup_called is True
    assert isinstance(manager._graph, DummyCompiledGraph)  # type: ignore[attr-defined]

    manager.close()
    assert ctx.exited is True
    assert manager._checkpointer is None  # type: ignore[attr-defined]
    assert manager._checkpointer_cm is None  # type: ignore[attr-defined]

    # close twice to ensure idempotence
    manager.close()
