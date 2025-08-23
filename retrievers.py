"""Compatibility shim for retrieval utilities.

Definitions live in `packages.legal_tools.retrieval` and are re-exported here
to keep imports stable while transitioning to the monorepo layout.
"""
import warnings
warnings.warn(
    "retrievers.py is deprecated. Import from packages.legal_tools.retrieval instead (e.g., from packages.legal_tools import FAISSRetriever).",
    DeprecationWarning,
    stacklevel=2,
)
# Expose algorithm classes from shared package
from packages.legal_tools.retrieval import (  # noqa: F401
    BaseRetriever,
    TFIDFRetriever,
    EmbeddingRetriever,
    FAISSRetriever,
)

# Expose symbols targeted by unit tests for patching
try:  # sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
    from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401
except Exception:  # pragma: no cover
    class TfidfVectorizer:  # type: ignore
        pass

    def cosine_similarity(*args, **kwargs):  # type: ignore
        return []

try:  # sentence-transformers
    from sentence_transformers import SentenceTransformer  # noqa: F401
except Exception:  # pragma: no cover
    class SentenceTransformer:  # type: ignore
        pass

try:  # faiss
    import faiss  # noqa: F401
except Exception:  # pragma: no cover
    class _FaissDummy:  # type: ignore
        class Index:
            pass

        IndexFlatIP = object
        IndexFlatL2 = object

    faiss = _FaissDummy()  # type: ignore

__all__ = [
    "BaseRetriever",
    "TFIDFRetriever",
    "EmbeddingRetriever",
    "FAISSRetriever",
    "TfidfVectorizer",
    "cosine_similarity",
    "SentenceTransformer",
    "faiss",
]
