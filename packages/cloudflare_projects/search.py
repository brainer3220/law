from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional, Sequence

from .bindings import CacheBinding
from .config import CloudflareProjectsConfig
from .d1_repository import D1Repository, InstructionVersion, ProjectMemory
from .reranker import AIGatewayReranker, AnswerResult, RerankedChunk


@dataclass(frozen=True)
class SearchResponse:
    query: str
    answer: AnswerResult
    reranked: Sequence[RerankedChunk]
    instructions: Sequence[InstructionVersion]
    memories: Sequence[ProjectMemory]


class SearchService:
    """End-to-end search → rerank → answer pipeline."""

    def __init__(
        self,
        *,
        repository: D1Repository,
        reranker: AIGatewayReranker,
        cfg: CloudflareProjectsConfig,
        cache: Optional[CacheBinding] = None,
    ) -> None:
        self._repo = repository
        self._reranker = reranker
        self._cfg = cfg
        self._cache = cache

    async def search(self, project_id: str, query: str) -> SearchResponse:
        normalized_query = query.strip()
        cache_key = self._cache_key(project_id, normalized_query)
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                return self._deserialize_cached(cached)

        candidates = await self._repo.search_candidates(project_id, normalized_query)
        reranked = await self._reranker.rerank(normalized_query, candidates)
        instructions = await self._repo.load_project_instructions(project_id)
        memories = await self._repo.load_project_memories(project_id)
        answer = await self._reranker.build_answer(
            query=normalized_query,
            reranked=reranked,
            instructions=instructions,
            memories=memories,
        )
        response = SearchResponse(
            query=normalized_query,
            answer=answer,
            reranked=reranked,
            instructions=instructions,
            memories=memories,
        )

        if self._cache and self._cfg.search_cache_ttl_seconds > 0:
            await self._cache.put(cache_key, self._serialize_cached(response), ttl_seconds=self._cfg.search_cache_ttl_seconds)
        return response

    # ---------------------- Cache helpers ----------------------
    def _cache_key(self, project_id: str, query: str) -> str:
        digest = hashlib.sha1(f"{project_id}:{query}".encode("utf-8")).hexdigest()
        return f"search:{digest}"

    def _serialize_cached(self, response: SearchResponse) -> dict:
        return {
            "query": response.query,
            "answer": {
                "text": response.answer.text,
                "citations": [c.rowid for c in response.answer.citations],
            },
            "instructions": [
                {
                    "version": inst.version,
                    "content": inst.content,
                    "created_by": inst.created_by,
                    "created_at": inst.created_at,
                }
                for inst in response.instructions
            ],
            "memories": [
                {
                    "key": mem.key,
                    "value": mem.value,
                    "source": mem.source,
                    "expires_at": mem.expires_at,
                    "confidence": mem.confidence,
                }
                for mem in response.memories
            ],
        }

    def _deserialize_cached(self, payload: dict) -> SearchResponse:
        instructions = [
            InstructionVersion(
                version=item["version"],
                content=item["content"],
                created_by=item.get("created_by"),
                created_at=item.get("created_at"),
            )
            for item in payload.get("instructions", [])
        ]
        memories = [
            ProjectMemory(
                key=item["key"],
                value=item["value"],
                source=item.get("source"),
                expires_at=item.get("expires_at"),
                confidence=item.get("confidence"),
            )
            for item in payload.get("memories", [])
        ]

        answer = AnswerResult(
            text=payload.get("answer", {}).get("text", ""),
            citations=[],
        )
        return SearchResponse(
            query=payload.get("query", ""),
            answer=answer,
            reranked=[],
            instructions=instructions,
            memories=memories,
        )

__all__ = ["SearchResponse", "SearchService"]
