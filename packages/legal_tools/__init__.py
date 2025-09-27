"""Lightweight namespace for legal tools.

Avoid importing heavy dependencies at package import time to keep optional
features (like the LangGraph agent) usable without extra installs.
"""

__all__ = []

try:  # pragma: no cover - optional dependency (LangGraph + Postgres)
    from .multi_turn_chat import (  # type: ignore
        ChatResponse,
        PostgresChatConfig,
        PostgresChatManager,
    )

    __all__.extend(
        [
            "ChatResponse",
            "PostgresChatConfig",
            "PostgresChatManager",
        ]
    )
except Exception:
    pass

# Expose contextual_rag symbols lazily if dependencies are available
try:  # pragma: no cover - optional import
    from .contextual_rag import (  # type: ignore
        ContextConfig,
        ContextualChunker,
        EmbeddingModel,
        IndexRecord,
    )

    __all__.extend(
        [
            "ContextConfig",
            "ContextualChunker",
            "EmbeddingModel",
            "IndexRecord",
        ]
    )
except Exception:
    # Optional module not available (e.g., missing pydantic).
    # This keeps `packages.legal_tools` importable for other features like pg_search/agent_graph.
    pass
