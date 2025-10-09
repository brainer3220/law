from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from .bindings import R2Binding
from .config import CloudflareProjectsConfig
from .d1_repository import D1Repository


@dataclass(frozen=True)
class ExtractedPage:
    page: int
    heading: Optional[str]
    text: str


@dataclass(frozen=True)
class ExtractionResult:
    doc_id: Optional[str]
    title: Optional[str]
    pages: List[ExtractedPage]
    metadata: Dict[str, str]


class TextExtractor(Protocol):
    async def extract(
        self,
        *,
        blob: bytes,
        mime: Optional[str],
        metadata: Dict[str, str],
    ) -> ExtractionResult:
        ...


@dataclass(frozen=True)
class IndexingMessage:
    project_id: str
    r2_key: str
    mime: Optional[str] = None
    doc_id: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class IndexingPipeline:
    """Queue consumer that normalizes text and writes into D1 FTS tables."""

    def __init__(
        self,
        *,
        r2: R2Binding,
        repository: D1Repository,
        extractor: TextExtractor,
        cfg: CloudflareProjectsConfig,
    ) -> None:
        self._r2 = r2
        self._repo = repository
        self._extractor = extractor
        self._cfg = cfg

    async def handle_message(self, message: IndexingMessage) -> None:
        mime = message.mime
        if mime and mime not in self._cfg.queue.allowed_mime_types:
            raise ValueError(f"Unsupported MIME type for indexing: {mime}")

        obj = await self._r2.get(message.r2_key)
        if obj is None:
            raise FileNotFoundError(f"R2 key not found: {message.r2_key}")

        blob = await obj.array_buffer()
        meta = message.metadata or {}
        obj_mime = mime or (obj.http_metadata or {}).get("contentType")
        result = await self._extractor.extract(blob=blob, mime=obj_mime, metadata=meta)
        doc_id = message.doc_id or result.doc_id or str(uuid.uuid4())

        for page in result.pages:
            chunks = self._chunk_text(page.text, max_chars=self._cfg.queue.max_chunk_chars)
            for ix, chunk in enumerate(chunks):
                heading = page.heading
                page_no = page.page
                # For now map directly to D1 chunk table; advanced metadata stored separately.
                await self._repo.upsert_document_chunk(
                    doc_id=doc_id,
                    project_id=message.project_id,
                    page=page_no,
                    heading=heading,
                    body=chunk,
                )

    # ---------------------- Text helpers ----------------------
    def _chunk_text(self, text: str, *, max_chars: int) -> List[str]:
        if not text:
            return []

        text = text.strip()
        if len(text) <= max_chars:
            return [text]

        segments: List[str] = []
        cursor = 0
        overlap = self._cfg.queue.overlap_chars
        length = len(text)
        stride = max_chars - overlap if overlap < max_chars else max_chars

        while cursor < length:
            segment = text[cursor : cursor + max_chars]
            segments.append(segment.strip())
            if cursor + max_chars >= length:
                break
            cursor += stride
        return [s for s in segments if s]


__all__ = [
    "ExtractionResult",
    "ExtractedPage",
    "IndexingMessage",
    "IndexingPipeline",
    "TextExtractor",
]
