# Share Service Architecture Overview

이 문서는 대화형 AI 공유(share) 기능을 구현한 `packages/legal_tools/share` 모듈군을 빠르게 이해하고, 비즈니스 요구사항과 코드 구성을 연결해 보기 위한 안내서입니다. 공유 가능한 리소스, 권한 모델, 토큰 설계, 그리고 주요 API 흐름을 요약합니다.

## 1. 모듈 구성

| 경로 | 설명 |
| --- | --- |
| `packages/legal_tools/share/models.py` | 공유 대상(`Resource`), 공유 설정(`Share`), 링크(`ShareLink`), ACL(`Permission`), 레다크션(`Redaction`), 감사 로그(`AuditLog`), 임베드(`Embed`)를 정의한 SQLAlchemy 모델. 기본 UUID 키, 생성/갱신 시각, 주요 인덱스까지 포함합니다. |
| `packages/legal_tools/share/schemas.py` | FastAPI 요청/응답용 Pydantic 스키마. 공유 생성/회수, 링크 발급, 토큰 접근, 레다크션 요청/응답, 감사 로그 페이징 등에 사용합니다. |
| `packages/legal_tools/share/service.py` | `ShareService`에서 레다크션 → 스냅샷 생성 → 공유 생성 → 링크 발급 → ACL 반영 → 감사 로그 적재를 담당합니다. DB 세션팩토리(`ShareDatabase`)와 설정(`ShareSettings`)도 여기 정의됩니다. |
| `packages/legal_tools/share/api.py` | `/v1/shares`, `/v1/s/{token}` 등 HTTP 엔드포인트를 FastAPI로 노출합니다. 예외 처리, DI, 응답 변환까지 포함합니다. |
| `packages/legal_tools/share/tokens.py` | 링크/임베드 토큰 Base62 생성, SHA-256 해시, JWT 서명 검증 등 공유 토큰 관련 유틸리티. |
| `packages/legal_tools/share/redaction.py` | 정규식·NER 기반 레다크션 파이프라인. 미리보기/적용 시 사용합니다. |

## 2. 데이터 모델 ↔ 요구사항 매핑

| 요구사항 | 모델 속성 |
| --- | --- |
| 공유 가능한 리소스 메타데이터, 버전, 스냅샷 | `Resource.type`, `version`, `snapshot_of`, `tags`, `created_at`, `updated_at` |
| 공유 모드(비공개/조직/링크/공개/임베드) | `Share.mode` (Enum `ShareMode`) |
| 링크 만료·해지 | `Share.expires_at`, `Share.revoked_at`, `ShareLink.revoked_at` |
| ACL 역할(Owner/Editor/Commenter/Viewer/Guest) | `Permission.role` (Enum `PermissionRole`) |
| 링크 도메인 화이트리스트 | `ShareLink.domain_whitelist` |
| 감사 로그(IP/UA 포함) | `AuditLog.ip`, `AuditLog.user_agent`, `AuditLog.context` |
| 임베드 서명 관리 | `Embed.domain`, `Embed.jwt_kid`, `Embed.last_used_at` |

## 3. 주요 서비스 플로우

1. **레다크션 미리보기 (`ShareService.preview_redaction`)**  
   `RedactionEngine`으로 감지된 민감 정보를 하이라이트하고 미리보기 응답을 생성합니다.
2. **레다크션 적용 (`ShareService.apply_redaction`)**  
   스냅샷 리소스를 별도 `Resource` 행으로 저장하고, 레다크션 diff를 `Redaction`에 기록합니다.
3. **공유 생성 (`ShareService.create_share`)**  
   스냅샷 리소스를 기준으로 `Share` 행을 생성하고, `Permission` 엔트리를 갱신합니다. 만료 TTL은 `ShareSettings.default_link_ttl_days`로 초기화됩니다.
4. **링크 발급 (`ShareService.create_share_link`)**  
   `generate_token`으로 Base62 토큰을 만들고 해시를 저장합니다. 요청에 따라 도메인 화이트리스트와 만료일을 적용합니다.
5. **토큰 접근 (`ShareService.access_via_token`)**  
   토큰 해시를 조회하고, 만료/도메인 제한/회수 여부를 검사합니다. 성공 시 감사 로그를 남깁니다.
6. **감사 로그 조회 (`ShareService.list_audit_logs`)**  
   리소스 ID, 액션 조건으로 필터링 후 타임라인을 반환합니다.

각 단계마다 `_log` 헬퍼가 `AuditLog` 레코드를 적재하여 접속 감사 요건을 충족합니다.

## 4. HTTP API 개요

| 메서드/경로 | 설명 |
| --- | --- |
| `POST /v1/redactions/preview` | 공유 전 민감정보 감지 및 미리보기 |
| `POST /v1/redactions/apply` | 스냅샷 생성 및 레다크션 확정 |
| `POST /v1/shares` | 공유 생성 (리소스, 모드, 권한 설정) |
| `GET /v1/shares/{share_id}` | 공유 메타데이터 조회 |
| `POST /v1/shares/{share_id}/revoke` | 공유 해지 및 회수 |
| `POST /v1/shares/{share_id}/links` | 링크 토큰 발급/재발급 |
| `POST /v1/permissions/bulk` | ACL 일괄 설정 |
| `GET /v1/audit` | 감사 로그 조회 |
| `GET /v1/s/{token}` | 토큰 기반 공유 열람 (도메인/IP 감사 포함) |

FastAPI 라우터는 모두 `ShareService` 의존성을 주입받아 위 플로우를 재사용합니다.

## 5. 보안·컴플라이언스 체크리스트

- **비밀정보 차단**: `RedactionEngine`에 정규식/NER 룰을 추가하면 스냅샷에 반영됩니다.
- **만료/회수**: `Share.revoke_share`, `ShareLink.revoked_at`을 통해 즉시 링크를 무효화할 수 있습니다.
- **도메인 제한/임베드**: 링크 생성 시 `domain_whitelist`를 설정하거나, 임베드 시 JWT 검증을 강제합니다.
- **감사 추적**: 공유 생성/열람/다운로드 등 모든 이벤트는 `_log` 호출을 통해 `AuditLog`에 저장됩니다.
- **학습 옵트인**: 스냅샷 리소스의 `tags`나 `context` 필드를 활용해 학습 제외 플래그를 저장하고, 다운스트림 파이프라인에서 필터링할 수 있습니다.

## 6. 로컬 실행 가이드

1. **환경 변수**: `LAW_SHARE_DB_URL`(PostgreSQL), `LAW_SHARE_BASE_URL`, `LAW_SHARE_LINK_TTL_DAYS` 등을 설정합니다.
2. **마이그레이션**: `ShareService.init_engine` 호출 시 SQLAlchemy가 테이블을 자동 생성합니다. 운영 환경에서는 Alembic 마이그레이션을 권장합니다.
3. **서버 기동**:
   ```bash
   uv run uvicorn law_shared.legal_tools.share.api:create_app --factory --reload
   ```
4. **기본 플로우 테스트**:
   ```bash
   http POST :8000/v1/redactions/preview payloads:='[...]'
   http POST :8000/v1/redactions/apply ...
   http POST :8000/v1/shares ...
   ```

이 문서를 바탕으로 팀 내 공유 정책 정의, 권한 테이블 확장, 모더레이션 훅 연계 등을 빠르게 진행할 수 있습니다.
