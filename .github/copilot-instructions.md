# Project Overview

### 핵심 원칙

1. **모든 주장 = 인용 근거 필수** (누락 시 재질의/재검증 루프)
2. **Matter 범위 제한**(OPA/ABAC) + PII/Privilege 자동 마스킹
3. **RAG-First**: 생성은 초안, 사실성은 검색/인용 검증으로 보강
4. **버전 고정**: 모델/프롬프트/인덱스/정책 버전 핀 & 카나리 릴리스
5. **평가 가능성**: Citation P/R, Unsupported Claim Rate, Grounded ROUGE 등 운영 지표 상시 집계

---

# Libraries and Frameworks

### Backend / Orchestration

* **Python 3.11+**
* **UV**
* **FastAPI** (gateway-api, rag-service, eval-service)
* **LangGraph / LangChain** (에이전트 상태기계·툴 호출)
* **Pydantic v2** (엄격 스키마, 데이터 계약 테스트)
* **PostgreSQL 16 + pgvector** (문서/청크/인용/ITExamples, 하이브리드 검색의 벡터)
* **Elasticsearch/OpenSearch** (BM25, 구조화 질의·필터)
* **OPA (Open Policy Agent)** + **Rego** (ABAC/RBAC 정책)
* **OpenTelemetry + Prometheus + Grafana** (관측성/모니터링)
* **Celery/RQ + Redis** (비동기 인덱스/배치)

### NLP / ML

* **HuggingFace Transformers / PEFT(LoRA)** (SFT/적응튜닝)
* **SentencePiece / fugashi + mecab-ko** (한국어 전처리, 옵션)
* **Faiss(옵션)**: 고속 오프라인 유사도 탐색 및 분석
* **Evaluate / sacrebleu / rouge-score** (요약·번역 지표)
* **PyTorch** (모델 학습/추론)
* **PyTorch Lightning** (훈련 구조화, 콜백)
* **Tesseract / RapidOCR** (PDF/OCR 필요 시)

### DevOps / Tooling

* **Docker / Docker Compose**
* **Helm / Kubernetes**
* **Terraform** (선택)
* **Poetry** (의존성/빌드)
* **pre-commit** (ruff/black/isort/mypy/commitlint)
* **ruff / black / isort / mypy** (정적 품질)
* **pytest / pytest-cov** (테스트)
* **trivy / grype** (이미지 취약점 스캔)

### Frontend (선택)

* **Next.js (App Router)** + **TypeScript**
* **TailwindCSS** + **shadcn/ui**
* **React Query / TanStack Table**
* **Plotly/VisX** (리포트 차트)

---

# Coding Standards

### 일반 원칙

* **타입 안정성**: Pydantic(BaseModel) + mypy(strict) 사용.
* **불변성/참조 무결성**: 문서→청크→인용 간 FK 보장, 삭제·보존 정책 준수.
* **예외 처리/로깅**: 모든 I/O 경계에서 `try/except` + 구조화 로깅(JSON).
* **테스트 계층**:

  * Unit: 파서/포맷터/도구 단위
  * Integration: 검색↔생성↔인용검증 연동
  * E2E: 계약 리뷰/소송 초안/리서치 시나리오
  * Eval: 법률 전용 메트릭(Citation P/R, UCR, Grounded ROUGE)
* **데이터/모델 버저닝**: 인덱스 빌드, 모델(가중치), 프롬프트, 정책 **버전 핀**.
* **시크릿/키**: 코드 내 하드코딩 금지. Vault/KMS + 최소권한 원칙.

### Python 스타일 (요약)

* **Formatter**: black(라인 100), isort(profile=black)
* **Linter**: ruff(에러 우선), flake8 규칙 상호 충돌 시 ruff 기준
* **Type**: mypy(strict, disallow-any-generics, warn-return-any)
* **Docstring**: Google style, 공용 API에는 예시 포함
* **어설션**: “5줄당 1 assert” 원칙(핵심 로직 가드)
* **로깅 규칙**:

  * `logger.bind(trace_id, tenant_id, matter_id, tool="retrieval").info(...)`
  * PII/Privilege 필드 로그 금지(마스킹 필수), 감사ID(audit\_id) 연결
* **리소스 관리**: 파일/커넥션 컨텍스트 매니저 사용, 배치 임베딩 시 메모리 워터마크 감시
* **훈련 코드 가이드(중요)**:

  * 체크포인트(모델/옵티마이저) **주기 저장**, TQDM 진행률, 로깅
  * **K-Fold 또는 Group Split**(사건/문서ID 기반 누수 방지)
  * 데이터 증강/정규화 옵션 플래그화
  * 실험 설정 YAML 고정 + seed 고정
  * 실패 복구 재현 스크립트 제공(`scripts/repro_*.sh`)
* **커밋/PR**:

  * Conventional Commits (`feat:`, `fix:`, `chore:` …)
  * PR 템플릿: 목적, 변경, 테스트, 보안 영향, 롤백 방법
* **보안/컴플라이언스**:

  * 외부 반출 시 산출물에 **provenance(코퍼스 해시·버전·모델·프롬프트)** 포함
  * 온프레 모드: Egress Allowlist, 외부 API 기본 차단
  * 데이터 보존기간/폐기 잡 설정(법적 요구 준수)

### 예시 설정 스니펫

```toml
# pyproject.toml (발췌)
[tool.black]
line-length = 100
[tool.ruff]
select = ["E","F","I","B","UP","PL"]
ignore = ["E203","E501"]
[tool.mypy]
strict = true
disallow_any_generics = true
warn_return_any = true
```

```yaml
# pre-commit-config.yaml (발췌)
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.5
    hooks: [{id: ruff}, {id: ruff-format}]
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks: [{id: black}]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks: [{id: mypy}]
```

---

# UI guidelines

### UX 원칙

* **근거가 보이는 UI**: 문단과 인용 근거를 양방향 하이라이트(호버/클릭 시 팝오버로 조문·판례·pin cite 표시).
* **법률 문서 친화 레이아웃**:

  * 좌: 결과 문서(초안/Diff)
  * 우: 근거 패널(법령/판례/문서 스니펫)
  * 하: 리스크/정책 패널(경고/거부 사유 및 해결 제안)
* **상태 명시**: Draft ↔ CiteCheck ↔ PolicyCheck ↔ Approved 단계 뱃지.
* **Human-in-the-Loop**: 조항별 “수정 제안” → 시스템 재검증(인용/정책) → 승인.
* **투명성/Provenance**: 모델·프롬프트·인덱스 버전, 감사ID 표시(툴팁).

### 컴포넌트 규격 (Next.js + Tailwind + shadcn/ui)

# Repository Guidelines

## Project Structure & Module Organization
- `main.py` drives the CLI entry points (`preview`, `stats`, `ask`, `serve`) and wires shared services.
- Domain logic and adapters live under `packages/legal_tools/`; statute and 해석례 flows concentrate in `law_go_kr.py` and `agent_graph.py`.
- Shared payload schemas reside in `packages/legal_schemas/`; bump their version whenever request/response shapes change.
- Offline corpora, fixtures, and retrieval indexes belong in `data/`, while tests sit in `tests/` and utility scripts in `scripts/`.

## Build, Test, and Development Commands
- `uv venv && uv sync` provisions the Python ≥3.10 environment with all LangChain/LangGraph dependencies.
- `uv run main.py ask "질문" --offline` exercises the agent locally without remote API calls.
- `uv run main.py serve --host 127.0.0.1 --port 8080` launches the OpenAI-compatible HTTP endpoint for manual QA.
- `pytest -q` runs the offline unit and integration suite; add `-k pattern` to scope execution.
- `ruff check .` and `ruff format .` keep code style consistent—run them before submitting changes.

## Coding Style & Naming Conventions
- Follow Black-style formatting (≈100 columns, 4-space indentation) enforced through `ruff format`.
- Prefer snake_case for modules and functions, PascalCase for classes, and UPPER_SNAKE_CASE for constants and environment variables.
- Annotate public functions, avoid wildcard imports, and keep comments focused on intent rather than mechanics.

## Testing Guidelines
- Write pytest cases under `tests/test_*.py`; mirror new fixtures in `data/` so offline runs stay deterministic.
- Mock LLM or network integrations to keep tests reliable; assert retrieval ranks or citation payloads when modifying agent flows.
- Aim for comprehensive coverage on schema changes and critical retrieval logic before opening a pull request.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat(agent): add statute parser fallback`) and group related changes logically.
- PR descriptions should state intent, major touch points, linked issues, and list the `uv run` and `pytest` commands exercised.
- Include CLI or API before/after samples when behavior or logging changes, and highlight schema version bumps.

## Security & Configuration Tips
- Never commit secrets; document defaults in `.env.example` and rely on environment variables like `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, and `OPENAI_*`.
- Install `psycopg[binary]` or system `libpq` for Postgres-backed BM25 search, enforcing SSL in DSNs.
- Keep retrieval indexes under `data/` and regenerate them via project scripts rather than manual edits to ensure reproducibility.
