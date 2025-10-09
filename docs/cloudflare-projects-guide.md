# Cloudflare “Projects” Toolkit Guide

This document explains how to use the new `packages.cloudflare_projects` tooling to ship a Cloudflare-only Projects experience built on D1 FTS5 search, Queues based indexing, and AI Gateway reranking/answer generation.

## Package Overview

```
packages/cloudflare_projects/
├── __init__.py                 # Re-exports primary entry points
├── api.py                      # High-level ProjectsService facade
├── audit.py                    # Logpush-friendly audit logger
├── bindings.py                 # Protocols for Workers bindings (D1, R2, Queue, AI, KV, DO)
├── config.py                   # Pydantic configs for FTS, queues, reranker, security
├── d1_repository.py            # D1 data access + FTS candidate retrieval
├── queues_pipeline.py          # Upload → extract → chunk → index consumer
├── reranker.py                 # AI Gateway reranker + answer generator
├── search.py                   # End-to-end search orchestration with optional cache
└── security.py                 # Zero Trust / webhook / IP validation helpers
```

All modules are dependency-light so they can run inside Workers using Python-on-Workers or a compatible runtime with the same bindings.

## Configuration (`config.py`)

`CloudflareProjectsConfig` centralizes binding names, table identifiers, and tuning parameters. Key sections:

- **D1 / Tables**: `doc_chunks_fts`, `doc_chunks_meta`, `instructions`, `memories`, etc. Update these fields if your schema names differ.
- **FTS (D1FTSConfig)**: Candidate limit, snippet formatting, boost weights for recency and click feedback.
- **Queue (QueuePipelineConfig)**: Allowed MIME types, extraction timeout, chunk sizing, overlap characters.
- **Reranker / Answer**: AI Gateway models, top-k limits, system prompt, response language, guardrail tags.
- **Security / Logging**: Zero Trust aud claims, webhook header/secret, trusted IP CIDRs, Logpush dataset and redaction list.

Load it from environment or a static file and inject into your Workers handlers.

```python
from packages.cloudflare_projects import CloudflareProjectsConfig

cfg = CloudflareProjectsConfig()
```

Adjust any field (`cfg.model_dump()`) before wiring the services.

## Bindings (`bindings.py`)

Instead of tying to concrete SDKs, we accept Protocols that mirror Cloudflare bindings:

- `D1Binding` with `prepare()` + optional `batch()`
- `R2Binding` with `get()`/`put()`
- `QueueBinding` for `send()`
- `AIGatewayBinding` for `rerank()` + `complete()`
- `CacheBinding` (KV cache) optional
- Durable Object helpers if you later extend locking or fan-out logic

Provide your Workers `env` objects or mocks that satisfy these interfaces.

## Indexing Pipeline (`queues_pipeline.py`)

`IndexingPipeline` consumes messages from Cloudflare Queues:

1. Downloads the source file from R2 (`r2_key`).
2. Runs a pluggable `TextExtractor` to emit `ExtractionResult` (pages, headings, metadata).
3. Splits text into overlapped chunks (configurable size/overlap).
4. Inserts chunk bodies into `doc_chunks_fts`.

`IndexingMessage` schema:

```json
{
  "projectId": "...",
  "r2Key": "docs/123.pdf",
  "mime": "application/pdf",
  "docId": "optional-explicit-doc-id",
  "metadata": {"source": "..."}
}
```

### Hook Points

- Swap in a WASM-based extractor (PDF, DOCX, PPTX) by implementing `TextExtractor`.
- Extend the pipeline to persist metadata into `docs` table or populate `doc_chunks_meta` with recency/click weights.

## Search Flow (`d1_repository.py`, `reranker.py`, `search.py`)

1. **Candidate Fetch**: `D1Repository.search_candidates()` generates an escaped MATCH query with boosts (`"token" OR token*`) and returns up to `max_candidates` results with snippet, bm25 score, recency/click adjustments.
2. **LLM Rerank**: `AIGatewayReranker.rerank()` calls AI Gateway to score each snippet for relevance.
3. **Answer Generation**: `AIGatewayReranker.build_answer()` composes a system prompt with project instructions + memories, injects top snippets, and requests a guided answer, returning text and citation list.
4. **Caching (Optional)**: `SearchService` can store serialized results in KV for repeated queries (`search_cache_ttl_seconds`).

Use `ProjectsService.search(project_id, query)` to execute the entire workflow.

## Security & Audit

- `security.verify_zero_trust_token()` checks JWT audience values (after upstream signature validation).
- `security.verify_webhook_signature()` validates HMAC signatures for upload callbacks.
- `security.is_trusted_ip()` guards administrative endpoints with CIDR allowlists.
- `audit.AuditLogger` emits structured events with redaction support and optional Logpush dataset tagging.

## High-Level Usage (`api.py`)

```python
from packages.cloudflare_projects import ProjectsService, CloudflareProjectsConfig
from your_project.extractors import PdfExtractor

service = ProjectsService.from_bindings(
    cfg=CloudflareProjectsConfig(),
    d1=env.DB,
    r2=env.DOCS_BUCKET,
    queue=env.INDEX_QUEUE,
    ai=env.AI,
    extractor=PdfExtractor(),
    cache=getattr(env, "CACHE_KV", None),
)

# Enqueue after upload
await service.enqueue_indexing(IndexingMessage(project_id="proj-1", r2_key="docs/foo.pdf"))

# Queue consumer Worker
await service.consume_queue(QueueEnvelope(body=ctx.body))  # ctx.body from Queue message

# Search endpoint
result = await service.search(project_id="proj-1", query="전자소송 절차")
```

If you need more control (e.g., custom citation payloads), wire the repository/reranker classes directly.

## Deployment Checklist

1. **Workers Bindings**: Configure `wrangler.toml` with `[[d1_databases]]`, `[[queues.producers]]`, `[[queues.consumers]]`, `[[r2_buckets]]`, `[[ai]]`, optional `[[kv_namespaces]]`.
2. **Schema Migration**: Apply the D1 schema defined in the architecture doc (projects, doc_chunks_fts, doc_chunks_meta, etc.).
3. **Queue Consumer Worker**: Create a worker that listens to the queue and calls `ProjectsService.consume_queue`.
4. **API Worker**: Expose routes (REST, GraphQL, etc.) that run `ProjectsService.search`.
5. **Security**: Enforce Zero Trust access, Turnstile, and WAF policies as described.
6. **Logpush**: Point `AuditLogger` to the target dataset and ensure Turnstile/Zero Trust logs are retained.

## Local Simulation & Testing

- Use `uv sync` to install dependencies.
- Supply mock bindings for D1/R2/Queues/AI Gateway to unit test the services.
- Run lint: `ruff check packages/cloudflare_projects`.
- Add `pytest` suites that stub the bindings and assert the `SearchResponse` contents when you flesh out extractors or queue handlers.

## Next Steps

- Implement a production-grade `TextExtractor` (PDF, PPTX, DOCX).
- Extend `D1Repository` with document metadata upserts and click/recency heuristics tuned to your usage.
- Wire Durable Objects for project-level locking if simultaneous uploads become an issue.
- Add integration tests around queue consumption and AI reranking once the Cloudflare Workers runtime components are in place.
