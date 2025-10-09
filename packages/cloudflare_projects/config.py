from __future__ import annotations

from typing import Optional, Sequence

from pydantic import BaseModel, Field


class D1FTSConfig(BaseModel):
    """Settings that control D1 FTS5 candidate retrieval."""

    max_candidates: int = Field(default=200, ge=1, le=1000)
    snippet_tokens: int = Field(default=10, ge=3, le=40)
    snippet_prefix: str = "<b>"
    snippet_suffix: str = "</b>"
    snippet_ellipsis: str = "…"
    default_query_boosts: Sequence[str] = Field(
        default_factory=lambda: ["heading^1.6", "body^1.0"]
    )
    recency_weight: float = 0.4
    click_weight: float = 0.6


class QueuePipelineConfig(BaseModel):
    """Configuration for the upload → extract → chunk → index pipeline."""

    extraction_timeout_ms: int = Field(default=45000, ge=1000)
    max_batch_chunks: int = Field(default=128, ge=1, le=500)
    overlap_chars: int = Field(default=120, ge=0, le=400)
    max_chunk_chars: int = Field(default=1200, ge=200, le=4000)
    allowed_mime_types: Sequence[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ]
    )


class RerankerConfig(BaseModel):
    """LLM reranker parameters."""

    model: str = "cloudflare/ai-rerank-v1"
    top_k: int = Field(default=12, ge=1, le=40)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    system_prompt: str = (
        "당신은 법률 분야 검색 결과를 평가하는 평가자입니다. 각 스니펫이 "
        "질문의 답을 담고 있는지를 0.0에서 1.0 사이 점수로 매기십시오."
    )


class AnswerConfig(BaseModel):
    """Settings for the final answer call."""

    model: str = "cloudflare/ai-answer-v1"
    max_context_snippets: int = Field(default=8, ge=1, le=20)
    guardrail_tags: Sequence[str] = Field(default_factory=lambda: ["legal", "korean"])
    response_language: str = Field(default="ko")
    max_output_tokens: Optional[int] = Field(default=1024, ge=128, le=4096)


class SecurityConfig(BaseModel):
    """Zero Trust, Turnstile, and webhook verification options."""

    zero_trust_aud: Sequence[str] = Field(default_factory=list)
    webhook_signature_header: str = Field(default="cf-webhook-signature")
    webhook_secret: Optional[str] = None
    turnstile_secret: Optional[str] = None
    trusted_ip_ranges: Sequence[str] = Field(default_factory=list)


class LoggingConfig(BaseModel):
    """Audit and telemetry targets."""

    logpush_dataset: Optional[str] = None
    structured_logger_name: str = "cloudflare-projects"
    redact_fields: Sequence[str] = Field(default_factory=lambda: ["token", "secret"])


class CloudflareProjectsConfig(BaseModel):
    """Top-level configuration container for the Projects toolkit."""

    d1_binding: str = "DB"
    r2_bucket_binding: str = "DOCS_BUCKET"
    queue_binding: str = "INDEX_QUEUE"
    durable_object_namespace: Optional[str] = None
    ai_gateway_binding: str = "AI"
    instructions_table: str = "instructions"
    memories_table: str = "memories"
    docs_table: str = "docs"
    doc_chunks_table: str = "doc_chunks_fts"
    doc_chunks_meta_table: str = "doc_chunks_meta"
    projects_table: str = "projects"
    project_members_table: str = "project_members"
    cache_kv_binding: Optional[str] = None
    search_cache_ttl_seconds: int = Field(default=600, ge=0)
    allowed_origins: Sequence[str] = Field(default_factory=list)
    feature_flags: Sequence[str] = Field(default_factory=list)
    fts: D1FTSConfig = Field(default_factory=D1FTSConfig)
    queue: QueuePipelineConfig = Field(default_factory=QueuePipelineConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    answer: AnswerConfig = Field(default_factory=AnswerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    experimental: Sequence[str] = Field(default_factory=list)


__all__ = ["CloudflareProjectsConfig"]
