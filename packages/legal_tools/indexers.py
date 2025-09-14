from __future__ import annotations

from typing import Iterable, Protocol

from .contextual_rag import IndexRecord


class VectorIndexer(Protocol):
    """Protocol for indexing index records into a vector-capable store.

    Implementations should map IndexRecord fields to the chosen backend
    (e.g., PostgreSQL+pgvector, OpenSearch with bm25+dense_vector).
    """

    def upsert(self, records: Iterable[IndexRecord]) -> None:  # pragma: no cover - interface only
        ...


class PgvectorIndexer:
    """Example skeleton for a pgvector-backed indexer.

    This avoids runtime dependencies. Provide a DB connection in your app,
    and implement the upsert logic to write canonical rows and vector values.
    """

    def __init__(self) -> None:
        pass

    def upsert(self, records: Iterable[IndexRecord]) -> None:  # pragma: no cover - example only
        # Pseudocode for guidance:
        # for r in records:
        #     INSERT INTO chunks(doc_id, section_id, chunk_id, headings_path, anchor_json,
        #                        bm25_text, chunk_text, ctx_hash, keywords, citations,
        #                        embedding, embedding_model)
        #     ON CONFLICT(chunk_id) DO UPDATE SET ...
        raise NotImplementedError("Implement database write based on your schema")


class OpenSearchIndexer:
    """Example skeleton for OpenSearch-backed indexer.

    Map bm25_text to the default text field and store a dense_vector for kNN.
    """

    def __init__(self) -> None:
        pass

    def upsert(self, records: Iterable[IndexRecord]) -> None:  # pragma: no cover - example only
        # Pseudocode for guidance:
        # bulk actions = [
        #   {"index": {"_index": "legal-chunks", "_id": r.chunk_id}},
        #   {"doc_id": r.doc_id, "section_id": r.section_id, ...,
        #    "bm25_text": r.bm25_text, "embedding": r.embedding},
        # ]
        # client.bulk(actions)
        raise NotImplementedError("Implement OpenSearch bulk indexing")

