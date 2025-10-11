# Workspace API 정리 메모 (migration 007 기준)

이 문서는 `packages/legal_tools/workspace` 모듈이 현재 어떤 범위까지 구현되어 있는지 요약합니다. 기본 레이어는 `organizations`, `projects`, `project_members`, `instructions`, `project_update_files`, `updates` 테이블로 제한됩니다.

## 구성요소 요약

| 레이어 | 상태 |
|--------|------|
| SQLAlchemy 모델 | `models/__init__.py`에 organizations, projects, project_members, instructions, project_update_files, updates만 export |
| Pydantic 스키마 | 프로젝트/멤버/지침 CRUD 요청·응답만 정의 (`schemata.Project*`, `Instruction*`) |
| 서비스 | `WorkspaceService`는 프로젝트, 멤버, 지침 로직만 제공. 감사 로그, 메모리, 파일 등 레거시 메서드는 제거됨 |
| FastAPI | `/v1/projects`, `/v1/projects/{id}/members`, `/v1/projects/{id}/instructions` 세 영역의 엔드포인트만 유지 |

## 주요 클래스/함수

- `WorkspaceSettings`
  - `LAW_WORKSPACE_AUTO_CREATE_DEFAULT_ORG=true`인 경우, 프로젝트 생성 시 `Default Organization`을 자동 생성합니다.
  - 감사 로그는 테이블이 제거되었으므로 `_log_audit`는 no-op입니다.
- `WorkspaceService`
  - `create_project`/`update_project`는 `status` 필드를 사용하며 기본값은 `"active"`입니다.
  - `clone_project`는 이름만 새로 받아 동일한 설명·상태를 가진 프로젝트를 생성합니다.
  - 멤버십 메서드(`add_member`, `list_members`, `update_member_role`, `remove_member`)는 역할 계층 검사를 수행합니다.
  - 지침 메서드(`create_instruction`, `list_instructions`, `get_instruction`)는 버전 번호를 오름차순으로 유지합니다.

## 제거된 항목

- `AuditLog`, `Memory`, `File`, `ProjectChat`, `Snapshot`, `ProjectBudget`, `UsageLedger` 등 레거시 모델과 관련 API는 더 이상 사용되지 않습니다.
- Cloudflare R2 클라이언트 의존성(`workspace/storage`)은 남아 있지만 현재 서비스 계층에서 참조하지 않습니다.
- 문서/가이드도 프로젝트·멤버·지침에 초점을 맞춰 갱신되었습니다.

## 테스트 체크리스트

1. `uv run law-cli workspace-serve` 실행 후 `POST /v1/projects` 호출이 201을 반환하는지 확인합니다.
2. 같은 프로젝트에 대해 `POST /v1/projects/{id}/instructions`를 호출해 새 버전을 만들고, `GET /v1/projects/{id}/instructions`로 최신 버전이 노출되는지 확인합니다.
3. 멤버가 아닌 사용자가 `GET /v1/projects/{id}`를 호출하면 403이 반환되는지 확인합니다.

이 범위를 벗어나는 기능을 추가하려면, 먼저 마이그레이션에 해당 테이블과 열을 복원한 뒤 모델·서비스·문서를 순차적으로 확장하세요.
