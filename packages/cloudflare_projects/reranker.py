from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .bindings import AIGatewayBinding
from .config import CloudflareProjectsConfig
from .d1_repository import ChunkCandidate, InstructionVersion, ProjectMemory


@dataclass(frozen=True)
class RerankedChunk:
    candidate: ChunkCandidate
    score: float


@dataclass(frozen=True)
class AnswerResult:
    text: str
    citations: Sequence[ChunkCandidate]


class AIGatewayReranker:
    """Orchestrates Cloudflare AI Gateway reranking and answer generation."""

    def __init__(self, ai: AIGatewayBinding, cfg: CloudflareProjectsConfig) -> None:
        self._ai = ai
        self._cfg = cfg

    async def rerank(self, query: str, candidates: Sequence[ChunkCandidate]) -> List[RerankedChunk]:
        if not candidates:
            return []

        response = await self._ai.rerank(
            model=self._cfg.reranker.model,
            query=query,
            documents=[c.snippet for c in candidates],
        )
        results = response.get("data") or response.get("results") or []
        reranked: List[RerankedChunk] = []
        for item in results:
            idx = item.get("index")
            if idx is None or idx >= len(candidates):
                continue
            score = float(item.get("relevance", item.get("score", 0.0)))
            reranked.append(RerankedChunk(candidate=candidates[idx], score=score))

        reranked.sort(key=lambda r: r.score, reverse=True)
        top = reranked[: self._cfg.reranker.top_k]
        return top

    async def build_answer(
        self,
        *,
        query: str,
        reranked: Sequence[RerankedChunk],
        instructions: Sequence[InstructionVersion],
        memories: Sequence[ProjectMemory],
    ) -> AnswerResult:
        context = self._render_context(
            reranked[: self._cfg.answer.max_context_snippets],
        )
        system_prompt = self._render_system_prompt(instructions, memories)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._render_user_prompt(query, context)},
        ]

        response = await self._ai.complete(
            model=self._cfg.answer.model,
            messages=messages,
        )

        text = self._extract_text(response)
        citations = [chunk.candidate for chunk in reranked[: self._cfg.answer.max_context_snippets]]
        return AnswerResult(text=text, citations=citations)

    # ---------------------- Prompt builders ----------------------
    def _render_context(self, reranked: Sequence[RerankedChunk]) -> str:
        lines: List[str] = []
        for idx, item in enumerate(reranked, start=1):
            candidate = item.candidate
            heading = candidate.heading or ""
            page = f"page={candidate.page}" if candidate.page is not None else ""
            meta = ", ".join(filter(None, [heading, page]))
            block = f"[{idx}] ({meta}) {candidate.snippet}"
            lines.append(block.strip())
        return "\n".join(lines)

    def _render_system_prompt(
        self,
        instructions: Sequence[InstructionVersion],
        memories: Sequence[ProjectMemory],
    ) -> str:
        instruction_blocks = "\n".join(
            f"- v{inst.version}: {inst.content.strip()}" for inst in instructions
        )
        memory_blocks = "\n".join(
            f"- {mem.key}: {mem.value.strip()} (source={mem.source})" for mem in memories
        )
        guardrails = ", ".join(self._cfg.answer.guardrail_tags)
        return (
            "당신은 법률 도우미입니다. 아래 지침과 프로젝트 메모리를 우선적으로 따르십시오.\n"
            f"지침:\n{instruction_blocks or '- (지침 없음)'}\n"
            f"프로젝트 메모리:\n{memory_blocks or '- (메모리 없음)'}\n"
            f"응답 언어: {self._cfg.answer.response_language}\n"
            f"가드레일 태그: {guardrails}"
        )

    def _render_user_prompt(self, query: str, context: str) -> str:
        return (
            "아래 검색 스니펫을 참고하여 질문에 답변하십시오. 각 주장에는 근거가 되는 스니펫 번호를 괄호로 표시하십시오.\n"
            f"질문: {query}\n"
            f"스니펫:\n{context or '(검색 결과가 없습니다)'}"
        )

    def _extract_text(self, response: dict) -> str:
        choices = response.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, list):
                fragments = [item.get("text", "") for item in content if isinstance(item, dict)]
                return "".join(fragments).strip()
            if isinstance(content, str):
                return content.strip()
        return response.get("text", "").strip()


__all__ = ["AIGatewayReranker", "AnswerResult", "RerankedChunk"]
