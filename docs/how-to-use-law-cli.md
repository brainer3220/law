# Law CLI 사용 방법 가이드

이 가이드는 로컬 환경에서 **Law CLI**를 설치하고, 기본 데이터 미리보기부터 OpenSearch 검색, LangGraph 기반 질의응답까지 순차적으로 수행하는 방법을 안내합니다. 이미 Python 개발 환경이 익숙하다는 전제에서, 필요한 준비물과 실행 절차, 자주 만나는 오류 해결법을 단계별로 정리했습니다.

---

## 1. 준비 사항 확인하기

| 항목 | 필수 여부 | 설명 |
| --- | --- | --- |
| Python 3.10 이상 | ✅ | `python3 --version` 으로 확인합니다. |
| [uv](https://docs.astral.sh/uv/) CLI | ✅ | 빠른 가상환경 및 패키지 관리를 위해 사용합니다. |
| OpenSearch 인스턴스 | 선택 | 검색 기능을 사용하려면 `http://localhost:9200` 에서 실행 중이어야 합니다. |
| PostgreSQL (ParadeDB) | 선택 | BM25 기반 검색을 활성화하려는 경우 준비합니다. |

> **Tip:** macOS/Homebrew 환경이라면 `brew install uv opensearch` 로 손쉽게 준비할 수 있습니다.

---

## 2. 저장소 클론 및 데이터 위치 지정하기

1. 저장소를 클론합니다.
   ```bash
   git clone https://github.com/brainer3220/law.git
   cd law
   ```
2. 데이터 디렉터리를 확인합니다. 기본 경로는 `./data`입니다. 다른 위치를 쓰고 싶다면 환경 변수로 지정합니다.
   ```bash
   export LAW_DATA_DIR="/absolute/path/to/data"
   ```

---

## 3. 의존성 설치 및 환경 구성하기

1. 가상환경을 만들고 필요한 패키지를 설치합니다.
   ```bash
   uv venv
   uv sync
   ```
2. OpenAI 호환 LLM 키가 있다면 `.env` 파일 또는 쉘 환경에 설정합니다.
   ```bash
   export OPENAI_API_KEY="sk-..."
   export LAW_LLM_PROVIDER="openai"  # gemini 등을 사용할 수도 있습니다.
   ```

---

## 4. 기본 기능 체험하기

### 4.1 JSON 미리보기
```bash
uv run main.py preview "data/.../민사법_유권해석_요약_518.json"
```
- 지정한 JSON 파일의 요약 정보를 확인해 데이터 구조를 익힙니다.

### 4.2 통계 확인
```bash
uv run main.py stats
```
- 데이터셋의 문서 수, 토큰 수 등 핵심 통계를 출력합니다.

### 4.3 OpenSearch 검색
1. OpenSearch가 실행 중인지 확인합니다 (`curl http://localhost:9200` 등).
2. CLI에서 검색을 실행합니다.
   ```bash
   uv run main.py opensearch-search "가산금 면제" --limit 5
   ```
- `--limit` 값으로 검색 결과 수를 조절합니다.

### 4.4 LangGraph 기반 질의응답
```bash
uv run main.py ask "근로시간 면제업무 관련 판례 알려줘" --k 5 --max-iters 3
```
- OpenSearch로 검색한 근거를 바탕으로 LangGraph 에이전트가 답변을 생성합니다.
- `--k`는 검색 문서 수, `--max-iters`는 추론 반복 횟수입니다.

---

## 5. OpenAI 호환 API 서버 열기

LangGraph 에이전트를 HTTP API로 노출하려면 다음 명령을 실행합니다.
```bash
uv run main.py serve --host 127.0.0.1 --port 8080
```
- `LAW_CHAT_DB_URL`을 설정하면 Postgres 기반 체크포인트 저장소를 활성화할 수 있습니다.
- 서버가 열리면 OpenAI SDK, curl, Postman 등으로 `/v1/chat/completions` 엔드포인트를 호출해 답변을 받을 수 있습니다.

**예시 (비스트리밍):**
```bash
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5-mini-2025-08-07",
    "messages": [{"role":"user","content":"근로시간 면제업무 관련 판례 알려줘"}],
    "stream": false,
    "top_k": 5,
    "max_iters": 3
  }'
```

---

## 5-1. MCP 서버로 도구 노출하기

Model Context Protocol을 통해 동일한 도구 세트를 다른 클라이언트(Claude Desktop, Cursor, OpenAI Agents 등)에서 재사용할 수 있습니다.

```bash
uv run law-mcp-server  # 기본값: streamable-http, http://127.0.0.1:8000/mcp
```

- `LAW_DATA_DIR`로 데이터 경로를 지정하면 OpenSearch 스니펫 검색이 동일하게 동작합니다.
- `LAW_MCP_TRANSPORT=stdio`로 설정하면 Claude Desktop 설정 파일에 `command: "uv"`, `args: ["run", "law-mcp-server"]` 식으로 등록할 수 있습니다.
- 개발 중에는 `uv run mcp dev packages/legal_tools/mcp_server.py`로 MCP Inspector를 띄워 툴/리소스/프롬프트를 확인하세요.

---

## 6. 선택 기능: PostgreSQL BM25 검색 활성화

BM25 기반 고급 검색이 필요하다면 다음 단계를 따릅니다.

1. ParadeDB 또는 호환 PostgreSQL 인스턴스를 준비합니다.
2. Psycopg 의존성을 설치합니다.
   ```bash
   uv pip install psycopg[binary]
   ```
3. DSN을 환경 변수로 설정합니다.
   ```bash
   export SUPABASE_DB_URL='postgresql://user:pass@host:5432/postgres?sslmode=disable'
   ```
4. 스키마 및 인덱스를 초기화합니다.
   ```bash
   uv run main.py pg-init
   ```
5. JSON 데이터를 적재합니다.
   ```bash
   uv run main.py pg-load --data-dir "$LAW_DATA_DIR"
   ```
6. BM25 검색을 실행합니다.
   ```bash
   uv run main.py pg-search "근로시간 면제" --limit 5
   ```

---

## 7. 문제 해결 및 FAQ

| 증상 | 해결 방법 |
| --- | --- |
| `ModuleNotFoundError` 발생 | `uv sync` 실행 여부와 가상환경 활성화를 확인합니다. |
| OpenSearch 연결 오류 | 포트 `9200`이 열려 있는지, 인증이 필요한지 확인합니다. 필요 시 `OPENSEARCH_URL` 환경 변수를 설정합니다. |
| LLM 호출 실패 | API 키 및 `LAW_LLM_PROVIDER` 설정을 다시 확인합니다. 오프라인 모드는 `--offline` 플래그로 실행할 수 있습니다. |
| PostgreSQL 접속 실패 | DSN 포맷(`postgresql://user:pass@host:port/db`)과 SSL 설정을 확인하고, ParadeDB `pg_search` 확장이 활성화되어 있는지 점검합니다. |

---

## 8. 다음 단계

- `tests/` 폴더의 pytest 스위트를 실행하여 환경 구성을 검증합니다.
  ```bash
  pytest -q
  ```
- LangGraph 프롬프트를 커스터마이즈하려면 `packages/legal_tools/agent_graph.py` 를 참고하세요.
- 데이터셋을 확장하거나 업데이트할 경우, `scripts/` 디렉터리의 도구를 활용해 지표와 인덱스를 재생성하세요.

---

## 체크리스트

- [ ] 준비물(Python, uv, 데이터 경로)을 모두 확인했나요?
- [ ] CLI 기본 명령(`preview`, `stats`, `ask`)을 실행해 보았나요?
- [ ] 필요한 경우 OpenSearch 또는 PostgreSQL BM25 검색을 설정했나요?
- [ ] API 서버를 실행하고 외부 클라이언트로 호출해 보았나요?
- [ ] 테스트 스위트(`pytest -q`)로 구성이 정상 동작하는지 확인했나요?

---

추가로 개선하고 싶은 사용 사례가 있다면 `README.md`에 링크된 CLI 옵션을 참고하여 새로운 자동화 스크립트나 문서를 확장해 보세요.
