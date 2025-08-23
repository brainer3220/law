# Project Overview

### 목표

* **근거 중심**(statute/판례/문서 ID + pin cite) 법률 도우미 에이전트.
* 계약서 리뷰·소송서면 초안·법령/판례 리서치·증거 검토(e-Discovery) 워크플로우 제공.
* **온프레/클라우드 겸용**, 멀티테넌트, 사건(Matter) 단위 권한 모델, **감사·정책·환각 억제** 내장.

### 핵심 원칙

1. **모든 주장 = 인용 근거 필수** (누락 시 재질의/재검증 루프)
2. **Matter 범위 제한**(OPA/ABAC) + PII/Privilege 자동 마스킹
3. **RAG-First**: 생성은 초안, 사실성은 검색/인용 검증으로 보강
4. **버전 고정**: 모델/프롬프트/인덱스/정책 버전 핀 & 카나리 릴리스
5. **평가 가능성**: Citation P/R, Unsupported Claim Rate, Grounded ROUGE 등 운영 지표 상시 집계

### 주요 기능 (초기 MVP)

* 계약서 리뷰(표준 조항 라이브러리 + 위험도 색상 핫스팟)
* 판례/법령 질의응답(RAG) & 요지/이유 요약
* 인용각주 자동 생성 & 문단-근거 하이라이트
* 법령/판례 변경 감지 알림(구독 키워드)

---

# Folder Structure

```
legal-llm-agent/
├─ apps/                              # 배포 단위 서비스
│  ├─ gateway-api/                    # REST/GraphQL BFF, authz, rate-limit
│  ├─ agent-orchestrator/             # LangGraph/State machine 에이전트 런타임
│  ├─ rag-service/                    # 하이브리드 검색, 인용검증, 재질의
│  ├─ ingest-service/                 # 커넥터·정규화·청크·임베딩·색인 파이프라인
│  ├─ eval-service/                   # 법률 전용 벤치마크/리더보드 API
│  ├─ policy-service/                 # OPA(Rego) 질의, ABAC/RBAC
│  ├─ audit-service/                  # 감사 이벤트, 세션 재현, PII 마스킹 로그
│  └─ notification-service/           # 변경감지/구독(법령·판례·키워드)
├─ packages/                          # 공용 라이브러리
│  ├─ legal-nlp/                      # 토크나이저, 한국어 법률 전처리, cite 파서
│  ├─ legal-prompts/                  # 시스템/도메인 프롬프트, 스타일가이드
│  ├─ legal-tools/                    # retrieve_legal, cite_from_chunks, summarize 등
│  ├─ legal-evals/                    # 평가셋 포맷, 메트릭(Citation P/R, UCR, ROUGE)
│  ├─ legal-guards/                   # Hallucination/Scope/UPL/Privacy 가드
│  └─ legal-schemas/                  # Pydantic/DB/Event/Tool I/O 스키마
├─ data/                              # 샘플/합성 데이터(민감 금지)
├─ infra/
│  ├─ docker/                         # Dockerfile, docker-compose
│  ├─ k8s/                            # Helm 차트(멀티테넌시 네임스페이스)
│  ├─ terraform/                      # 클라우드 IaC(선택)
│  └─ vault/                          # 시크릿/키 관리 가이드
├─ scripts/                           # 배치, 재색인, 통계, 마이그
├─ docs/                              # ADR, 아키텍처, API 스펙, 보안/컴플라이언스
│  ├─ adr/                            # Architecture Decision Records
│  └─ api/                            # OpenAPI/GraphQL 스키마
├─ Makefile                           # 공통 작업 단축키
├─ pyproject.toml                     # poetry/ruff/mypy/pytest 설정
├─ package.json                       # UI/도구 프런트 빌드(선택)
├─ pre-commit-config.yaml
├─ README.md
└─ SECURITY.md / PRIVACY.md / COMPLIANCE.md
```

### ingest-service/connectors (AI-Hub 확장 대비)

```
apps/ingest-service/connectors/
└─ aihub/
   ├─ civil_llm_kit_2024/     # dataSetSn=71841
   │  ├─ reader.py            # 분할 zip 병합/검증 + 스트리밍 로더
   │  ├─ schema.py            # 원천 → 표준 스키마 매핑 (RawExample/ITExample)
   │  └─ map_config.yaml
   ├─ criminal_llm_kit_2024/  # (확장) 형사
   ├─ admin_llm_kit_2024/     # (확장) 행정
   └─ ip_llm_kit_2024/        # (확장) 지재
```

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

* **Typography**:

  * 본문: 15–16px/1.6, 법조문은 고정폭 옵션 제공
  * 각주: 12–13px, 회색 톤, 클릭 시 원문 패널 스크롤 싱크
* **Colors**:

  * Risk: Red(High) / Amber(Med) / Green(Low)
  * Cite 상태: Gray(미확인) → Blue(검증됨) → Red(오류)
* **Cards**:

  * `EvidenceCard`: 출처 유형(statute/case/doc), 제목/번호, 스니펫, pin-cite, “원문 열기”
  * `ClauseDiffCard`: before/after Diff, 위험 태그, 인용각주
* **Tables**:

  * `Claims × Evidence` 매트릭스(열: 주장/문단, 행: 인용 근거, 셀: 정합성/정확성 아이콘)
* **검색 UX**:

  * 고급 필터: 도메인(민사/형사/행정/지재), 코퍼스(법령/판례/문서), 날짜/사건번호
  * 저장 가능한 쿼리(즐겨찾기/알림 구독)
* **알림/구독**:

  * 법령 개정/신규 판례/키워드 트리거 → In-app Toast + Inbox + 이메일 요약
* **접근성(A11y)**:

  * 키보드 내비게이션(Anchor jump: 다음 인용/이전 인용)
  * 색맹 친화 대비(아이콘/패턴로 보조)
  * 스크린리더용 `aria-label`(조문·판례 메타 낭독)
* **국제화(i18n)**:

  * 기본 `ko-KR`, `en-US` 토글(법령/판례 참조명은 원문 유지)
* **보안/프라이버시 UI**:

  * PII/Privilege 마스킹 토글(권한 필요), 반출 시 워터마크/다운로드 잠금
* **오류/정책 피드백**:

  * Unsupported Claim 발견 시 문장 단위로 붉은 경고, “근거 추가 검색” 버튼 제공
  * 정책 거부(예: UPL, 개인정보 포함)는 이유와 해결 가이드 링크 표시

### 프런트 폴더 (예시)

```
apps/web/
├─ app/ (Next.js App Router)
├─ components/
│  ├─ evidence-card.tsx
│  ├─ clause-diff-card.tsx
│  ├─ claim-evidence-matrix.tsx
│  └─ risk-badge.tsx
├─ lib/ (api 클라이언트, i18n, auth)
└─ styles/ (tailwind)
```
