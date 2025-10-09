from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .bindings import (
    AIGatewayBinding,
    CacheBinding,
    D1Binding,
    QueueBinding,
    R2Binding,
)
from .config import CloudflareProjectsConfig
from .d1_repository import D1Repository
from .queues_pipeline import IndexingMessage, IndexingPipeline, TextExtractor
from .reranker import AIGatewayReranker
from .search import SearchResponse, SearchService


@dataclass
class QueueEnvelope:
    body: Dict[str, Any]


class ProjectsService:
    """Facade that wires repository, queue pipeline, and search together."""

    def __init__(
        self,
        *,
        cfg: CloudflareProjectsConfig,
        repository: D1Repository,
        pipeline: IndexingPipeline,
        search_service: SearchService,
        queue: QueueBinding,
    ) -> None:
        self._cfg = cfg
        self._repo = repository
        self._pipeline = pipeline
        self._search = search_service
        self._queue = queue

    @classmethod
    def from_bindings(
        cls,
        *,
        cfg: CloudflareProjectsConfig,
        d1: D1Binding,
        r2: R2Binding,
        queue: QueueBinding,
        ai: AIGatewayBinding,
        extractor: TextExtractor,
        cache: Optional[CacheBinding] = None,
    ) -> "ProjectsService":
        repository = D1Repository(d1, cfg)
        reranker = AIGatewayReranker(ai, cfg)
        pipeline = IndexingPipeline(r2=r2, repository=repository, extractor=extractor, cfg=cfg)
        search_service = SearchService(repository=repository, reranker=reranker, cfg=cfg, cache=cache)
        return cls(cfg=cfg, repository=repository, pipeline=pipeline, search_service=search_service, queue=queue)

    # ---------------------- Indexing ----------------------
    async def enqueue_indexing(self, message: IndexingMessage) -> None:
        await self._queue.send(
            {
                "projectId": message.project_id,
                "r2Key": message.r2_key,
                "mime": message.mime,
                "docId": message.doc_id,
                "metadata": message.metadata,
            }
        )

    async def consume_queue(self, envelope: QueueEnvelope) -> None:
        body = envelope.body
        message = IndexingMessage(
            project_id=body["projectId"],
            r2_key=body["r2Key"],
            mime=body.get("mime"),
            doc_id=body.get("docId"),
            metadata=body.get("metadata") or {},
        )
        await self._pipeline.handle_message(message)

    # ---------------------- Search ----------------------
    async def search(self, project_id: str, query: str) -> SearchResponse:
        return await self._search.search(project_id, query)


__all__ = ["ProjectsService", "QueueEnvelope"]
