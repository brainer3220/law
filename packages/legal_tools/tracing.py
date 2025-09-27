"""LangSmith tracing utilities for CLI and HTTP entry points."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_DISABLED_VALUES = {"0", "false", "off", "no", "disable", "disabled"}

_callbacks: Optional[List[Any]] = None
_configured = False
_trace_loaded = False
_trace_func: Optional[Any] = None


def _load_trace_func() -> Optional[Any]:
    global _trace_loaded, _trace_func
    if _trace_loaded:
        return _trace_func
    try:
        from langsmith.run_helpers import trace as trace_func  # type: ignore import
    except Exception:
        trace_func = None
    _trace_func = trace_func
    _trace_loaded = True
    return _trace_func


@contextmanager
def _noop_context() -> Iterable[None]:
    yield


def _normalize_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized not in _DISABLED_VALUES


def _build_callbacks(project: str) -> List[Any]:
    callbacks: List[Any] = []
    try:
        from langsmith import Client  # type: ignore import
    except Exception as exc:
        logger.debug("langsmith_import_failed", error=str(exc))
        return callbacks

    api_key = os.getenv("LANGSMITH_API_KEY")
    endpoint = os.getenv("LANGSMITH_ENDPOINT")

    client_kwargs: Dict[str, Any] = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if endpoint:
        client_kwargs["api_url"] = endpoint

    try:
        client = Client(**client_kwargs)
        client.verify_api_key()
    except Exception as exc:
        logger.warning("langsmith_client_verification_failed", error=str(exc))
        return callbacks

    try:
        from langsmith.run_helpers import get_langchain_callbacks  # type: ignore import
    except Exception:
        get_langchain_callbacks = None  # type: ignore[assignment]

    if get_langchain_callbacks is not None:
        try:
            generated = get_langchain_callbacks(client=client, project_name=project)
            callbacks = list(generated) if generated is not None else []
        except TypeError:
            try:
                generated = get_langchain_callbacks(client, project)  # type: ignore[misc]
                callbacks = list(generated) if generated is not None else []
            except Exception as exc:
                logger.debug("langsmith_get_callbacks_failed", error=str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.debug("langsmith_get_callbacks_failed", error=str(exc))

    if callbacks:
        return callbacks

    tracer: Optional[Any] = None
    try:
        from langchain.callbacks.tracers.langchain import (  # type: ignore import
            LangChainTracer,
        )
    except Exception:
        try:
            from langchain_core.tracers.langchain import (  # type: ignore import
                LangChainTracer,
            )
        except Exception as exc:
            logger.debug("langsmith_tracer_import_failed", error=str(exc))
            return callbacks

    try:
        tracer = LangChainTracer(project_name=project)
    except TypeError:
        tracer = LangChainTracer()  # type: ignore[call-arg]
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.debug("langsmith_tracer_init_failed", error=str(exc))
        tracer = None

    if tracer is not None:
        try:
            ensure_session = getattr(tracer, "ensure_session", None)
            if callable(ensure_session):
                ensure_session()
        except Exception:
            logger.debug("langsmith_tracer_ensure_session_failed")
        callbacks = [tracer]
    return callbacks


def configure_langsmith() -> Sequence[Any]:
    """Enable LangSmith tracing when credentials are present."""

    global _configured, _callbacks
    if _configured:
        return _callbacks or []

    enabled_toggle = _normalize_bool(os.getenv("LAW_LANGSMITH_ENABLED"))
    api_key = os.getenv("LANGSMITH_API_KEY")
    project = os.getenv("LANGSMITH_PROJECT")

    if enabled_toggle is False:
        logger.info("langsmith_disabled_via_env")
        _configured = True
        _callbacks = []
        return _callbacks

    if not api_key or not project:
        if enabled_toggle:
            logger.warning("langsmith_missing_credentials")
        else:
            logger.debug("langsmith_credentials_not_found")
        _configured = True
        _callbacks = []
        return _callbacks

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
    endpoint = os.getenv("LANGSMITH_ENDPOINT")
    if endpoint:
        os.environ.setdefault("LANGCHAIN_ENDPOINT", endpoint)

    callbacks = _build_callbacks(project)
    if callbacks:
        logger.info("langsmith_tracing_enabled", project=project)
    else:
        logger.debug("langsmith_tracing_enabled_without_callbacks", project=project)

    _callbacks = callbacks
    _configured = True
    return _callbacks


def get_langsmith_callbacks() -> Sequence[Any]:
    """Return LangSmith callback handlers (empty when disabled)."""

    callbacks = configure_langsmith()
    if not callbacks:
        return []
    return list(callbacks)


def trace_run(name: str, *, metadata: Optional[Dict[str, Any]] = None):
    """Return a context manager that wraps a block in a LangSmith trace."""

    configure_langsmith()
    trace_func = _load_trace_func()
    if trace_func is None:
        return _noop_context()
    kwargs: Dict[str, Any] = {}
    if metadata:
        kwargs["metadata"] = metadata
    try:
        return trace_func(name, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.debug("langsmith_trace_failed", error=str(exc))
        return _noop_context()
