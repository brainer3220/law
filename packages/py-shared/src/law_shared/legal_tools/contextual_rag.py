from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Protocol, Sequence, Tuple

from pydantic import BaseModel, Field

from law_shared.legal_schemas import Anchor, Chunk, Document, Section, SourceType


class ContextConfig(BaseModel):
    """Configuration knobs for chunking and contextual enrichment.

    token_budget numbers assume ko SentencePiece-like tokens.
    """

    statute_chunk_tokens: Tuple[int, int] = (350, 550)
    statute_overlap: int = 50
    case_chunk_tokens: Tuple[int, int] = (150, 300)
    case_overlap: int = 40
    contract_chunk_tokens: Tuple[int, int] = (200, 400)
    contract_overlap: int = 50
    context_prefix_tokens: int = 160


class EmbeddingModel(Protocol):
    """Pluggable embedding model interface.

    Implementations should be thin adapters around your chosen
    embedding backend (e.g., bge-m3, jina-v3, Cohere). The module
    intentionally avoids taking a runtime dependency.
    """

    model_name: str

    def embed(self, texts: Sequence[str]) -> List[List[float]]:  # pragma: no cover - interface only
        ...


@dataclass(frozen=True)
class IndexRecord:
    """A flattened, index-ready record for a chunk.

    Use this to send data to pgvector or OpenSearch; map fields as needed.
    """

    chunk_id: str
    section_id: str
    doc_id: str
    doc_version: Optional[str]
    source_type: str
    headings_path: Tuple[str, ...]
    anchor: Anchor
    bm25_text: str
    chunk_text: str
    contextualized_text_hash: str
    keywords: Tuple[str, ...]
    normalized_citations: Tuple[str, ...]
    embedding: Optional[List[float]]
    embedding_model: Optional[str]


class ContextualChunker:
    """Heuristic chunker + contextualizer for legal corpora.

    - Splits by corpus-aware boundaries first; falls back to length-based.
    - Generates compact document/section context and prefixes it to chunks
      for embedding only (preserves raw chunk_text for citations).
    - Produces index-ready records; embeddings are optional at this stage.
    """

    def __init__(self, cfg: Optional[ContextConfig] = None) -> None:
        self.cfg = cfg or ContextConfig()

    # ----------------------- Public API -----------------------
    def build_index_records(
        self,
        document: Document,
        sections: Sequence[Section],
        embedder: Optional[EmbeddingModel] = None,
    ) -> List[IndexRecord]:
        """Create index-ready records from a document and its sections.

        Args:
            document: Canonical document metadata.
            sections: Parsed sections (headings + text).
            embedder: Optional embedding model adapter.

        Returns:
            List of IndexRecord with optional embeddings populated.
        """

        doc_synopsis = self._doc_synopsis(document, sections)
        chunks: List[Chunk] = []
        for s in sections:
            section_chunks = self._chunk_section(document, s)
            enriched = self._enrich_section_chunks(document, s, doc_synopsis, section_chunks)
            chunks.extend(enriched)

        # Prepare texts for embedding: use contextualized_text, clipped by prefix budget
        contextuals = [c.contextualized_text or c.chunk_text for c in chunks]
        embeddings: Optional[List[List[float]]] = None
        if embedder:
            embeddings = embedder.embed(contextuals)
            assert len(embeddings) == len(chunks)

        records: List[IndexRecord] = []
        for i, c in enumerate(chunks):
            records.append(
                IndexRecord(
                    chunk_id=c.chunk_id,
                    section_id=c.section_id,
                    doc_id=c.doc_id,
                    doc_version=document.version,
                    source_type=document.source_type.value,
                    headings_path=tuple(c.headings_path),
                    anchor=c.anchor or Anchor(),
                    bm25_text=self._bm25_text(document, c),
                    chunk_text=c.chunk_text,
                    contextualized_text_hash=_sha1((c.contextualized_text or "").encode("utf-8")),
                    keywords=tuple(c.keywords),
                    normalized_citations=tuple(c.normalized_citations),
                    embedding=(embeddings[i] if embeddings else None),
                    embedding_model=(embedder.model_name if embedder else None),
                )
            )
        return records

    # ----------------------- Chunking -------------------------
    def _chunk_section(self, document: Document, section: Section) -> List[Chunk]:
        text = section.text.strip()
        if not text:
            return []

        if document.source_type == SourceType.statute:
            spans = _split_by_statute_paragraphs(text)
            desired = self.cfg.statute_chunk_tokens
            overlap = self.cfg.statute_overlap
        elif document.source_type == SourceType.case:
            spans = _split_by_numbered_paragraphs(text)
            desired = self.cfg.case_chunk_tokens
            overlap = self.cfg.case_overlap
        elif document.source_type == SourceType.contract:
            spans = _split_by_contract_clauses(text)
            desired = self.cfg.contract_chunk_tokens
            overlap = self.cfg.contract_overlap
        else:
            spans = _split_by_paragraphs(text)
            desired = (250, 400)
            overlap = 40

        # Re-pack to stay within token window
        merged = _pack_spans(spans, desired, overlap)

        chunks: List[Chunk] = []
        for order, chunk_text in enumerate(merged):
            chunks.append(
                Chunk(
                    chunk_id=f"{section.section_id}:{order}",
                    section_id=section.section_id,
                    doc_id=section.doc_id,
                    order=order,
                    anchor=section.anchor,
                    chunk_text=chunk_text,
                    headings_path=section.headings_path,
                )
            )
        return chunks

    # ----------------------- Enrichment ----------------------
    def _enrich_section_chunks(
        self,
        document: Document,
        section: Section,
        doc_synopsis: str,
        chunks: Sequence[Chunk],
    ) -> List[Chunk]:
        section_synopsis = section.section_synopsis or self._section_synopsis(document, section)
        prefix_parts = _compact_prefix(
            title=document.title,
            headings=section.headings_path,
            doc_synopsis=doc_synopsis,
            section_synopsis=section_synopsis,
            max_tokens=self.cfg.context_prefix_tokens,
        )

        enriched: List[Chunk] = []
        for c in chunks:
            keywords = _keywords_guess(document, section, c)
            citations = _citations_guess(document, section, c)
            contextualized_text = prefix_parts + "\n\n" + c.chunk_text
            enriched.append(
                Chunk(
                    chunk_id=c.chunk_id,
                    section_id=c.section_id,
                    doc_id=c.doc_id,
                    order=c.order,
                    anchor=c.anchor,
                    chunk_text=c.chunk_text,
                    contextualized_text=contextualized_text,
                    headings_path=c.headings_path,
                    keywords=keywords,
                    normalized_citations=citations,
                )
            )
        return enriched

    # ----------------------- Synopses ------------------------
    def _doc_synopsis(self, document: Document, sections: Sequence[Section]) -> str:
        # Heuristic: take first 2–3 non-empty sentences across early sections.
        sentences: List[str] = []
        for s in sections[:3]:
            sentences.extend(_sentences(s.text)[:2])
            if len(sentences) >= 3:
                break
        synopsis = " ".join(sentences[:3])
        return synopsis[:600]

    def _section_synopsis(self, document: Document, section: Section) -> str:
        # Heuristic: first 1–2 sentences within the section
        sents = _sentences(section.text)
        synopsis = " ".join(sents[:2])
        # Keep article/paragraph labels if present
        label = _first_label(section.text)
        if label:
            synopsis = f"{label} — {synopsis}"
        return synopsis[:400]

    # ----------------------- BM25 text -----------------------
    def _bm25_text(self, document: Document, chunk: Chunk) -> str:
        parts = [
            document.title,
            " > ".join(chunk.headings_path),
            chunk.chunk_text,
        ]
        return "\n".join([p for p in parts if p])


# ----------------------- Helpers -------------------------------


def _split_by_statute_paragraphs(text: str) -> List[str]:
    # Split on markers like "제1항", "제2호" while keeping them attached
    pattern = re.compile(r"(?=\s*제\d+(?:항|호))")
    parts = [p.strip() for p in pattern.split(text) if p.strip()]
    return parts if parts else [text]


def _split_by_numbered_paragraphs(text: str) -> List[str]:
    # Common in cases: numbered paras like "1.", "(1)", etc.
    pattern = re.compile(r"(?=\n\s*(?:\(\d+\)|\d+\.|\d+\)\s))")
    parts = [p.strip() for p in pattern.split(text) if p.strip()]
    return parts if parts else _split_by_paragraphs(text)


def _split_by_contract_clauses(text: str) -> List[str]:
    pattern = re.compile(r"(?=\n\s*(?:\d+(?:\.\d+)*\)|\d+(?:\.\d+)*\.|제\d+조))")
    parts = [p.strip() for p in pattern.split(text) if p.strip()]
    return parts if parts else _split_by_paragraphs(text)


def _split_by_paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    return parts if parts else [text]


def _pack_spans(spans: Sequence[str], desired: Tuple[int, int], overlap: int) -> List[str]:
    lo, hi = desired
    out: List[str] = []
    buf: List[str] = []
    for p in spans:
        if _approx_tokens("\n\n".join(buf + [p])) <= hi:
            buf.append(p)
            continue
        # Flush current buffer: optionally overlap from the end of previous buf
        if buf:
            out.append("\n\n".join(buf))
            # Create overlap by carrying tail of previous buf
            if overlap > 0:
                tail = _tail_tokens("\n\n".join(buf), overlap)
                buf = [tail, p]
            else:
                buf = [p]
        else:
            out.append(p)
            buf = []

    if buf:
        out.append("\n\n".join(buf))

    # If any chunk is below lo and can be merged with next, attempt a pass
    merged: List[str] = []
    i = 0
    while i < len(out):
        cur = out[i]
        if _approx_tokens(cur) < lo and i + 1 < len(out):
            nxt = out[i + 1]
            combo = cur + "\n\n" + nxt
            if _approx_tokens(combo) <= hi:
                merged.append(combo)
                i += 2
                continue
        merged.append(cur)
        i += 1
    return merged


def _compact_prefix(
    title: str,
    headings: Sequence[str],
    doc_synopsis: str,
    section_synopsis: str,
    max_tokens: int,
) -> str:
    parts = [title, " > ".join(headings), doc_synopsis, section_synopsis]
    prefix = " \u2758 ".join([p for p in parts if p])  # use vertical bar-like separator
    # Trim to token budget
    words = prefix.split()
    # heuristic token estimate: 1 token ~= 0.75 words (ko mix)
    budget_words = max(1, int(max_tokens / 0.75))
    return " ".join(words[:budget_words])


def _approx_tokens(text: str) -> int:
    # Very rough token proxy: chars/2 for ko-heavy, bounded by words
    chars = len(text)
    words = max(1, len(text.split()))
    return max(words, int(chars / 2))


def _tail_tokens(text: str, approx_tokens: int) -> str:
    # Return a suffix of text roughly approx_tokens long
    if not text:
        return ""
    n = len(text)
    # heuristic: 2 chars per token
    chars = approx_tokens * 2
    return text[max(0, n - chars) :]


def _sentences(text: str) -> List[str]:
    # naive split by sentence enders in ko/en
    parts = re.split(r"(?<=[.!?\u3002\uFF0E])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _first_label(text: str) -> Optional[str]:
    m = re.search(r"제\d+조[^\n]*|제\d+항|제\d+호|\b주문\b|\b이유\b", text)
    return m.group(0) if m else None


def _keywords_guess(document: Document, section: Section, chunk: Chunk) -> List[str]:
    # Extract simple tokens likely to be legal terms or IDs
    kws: List[str] = []
    # statute/article markers
    kws.extend(re.findall(r"민법|형법|상법|행정|지재|제\d+조", chunk.chunk_text))
    # numerics and docket-like
    kws.extend(re.findall(r"\b\d{2,}[가-힣]?\b", chunk.chunk_text))
    # headings words
    if section.title:
        kws.extend(section.title.split())
    return list(dict.fromkeys([k for k in kws if k]))[:12]


def _citations_guess(document: Document, section: Section, chunk: Chunk) -> List[str]:
    cites: List[str] = []
    # statute article pattern
    for m in re.findall(r"(?:민법|형법|상법|민사소송법)?\s*제\s*\d+\s*조", chunk.chunk_text):
        cites.append(re.sub(r"\s+", "", m))
    # case IDs like 2009다12345
    cites.extend(re.findall(r"\b\d{4}[가-힣]{1}\d{3,6}\b", chunk.chunk_text))
    return list(dict.fromkeys(cites))[:12]


def _sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()

