# Law Workspace API

프로젝트 중심 법률 작업 공간을 위한 생존 최소 스키마와 API 계약서입니다.  
`packages/legal_tools/workspace/migrations/007_project_workspace_schema.sql`에 정의된 테이블과만 동작하도록 정리되었습니다.

## 핵심 엔터티

- **organizations**: 프로젝트 상위 조직. `id`, `name`, `created_by`, `created_at`.
- **projects**: 워크스페이스의 주체. `status`(텍스트), `archived`(boolean)만 유지합니다.
- **project_members**: 프로젝트와 사용자 간 RBAC 매핑. `role ∈ {owner, maintainer, editor, commenter, viewer}`.
- **instructions**: 프로젝트별 버전 관리되는 시스템 프롬프트.
- **project_update_files / updates**: 향후 릴리즈를 위해 보존된 업데이트 메타데이터 테이블. 아직 API에서 노출하지 않습니다.

## 지원 기능

1. **프로젝트 수명주기**
   - 생성, 조회, 수정, 삭제(soft/hard)  
   - 기본 상태 값은 `status="active"`이며, 필요 시 임의의 텍스트 값을 저장할 수 있습니다.
   - `archived=true`가 soft delete 역할을 대체합니다.
2. **프로젝트 복제**
   - 이름만 새로 지정하여 동일한 설명/상태를 가진 프로젝트를 생성합니다.
   - 기존 멤버는 복사하지 않으며, 호출자만 OWNER로 배치합니다.
3. **멤버십 관리**
   - 초대/제거/역할 변경
   - 권한 계층: Owner > Maintainer > Editor > Commenter > Viewer
4. **지침(Instructions) 버전 관리**
   - 프로젝트당 버전 정수(primary key) 증가
   - 각 버전은 `content`, `created_by`, `created_at`을 보존합니다.

> 더 이상 제공되지 않는 기능: 메모리, 파일, 채팅, 검색, 스냅샷, 감사 로그, 사용량·예산 API.  
> 관련 모델과 테이블은 migration 007에서 제거되었습니다.

## 권한 매트릭스

| 권한/역할         | Owner | Maintainer | Editor | Commenter | Viewer |
|-------------------|:-----:|:----------:|:------:|:---------:|:------:|
| 프로젝트 생성/삭제 | ✅    | ✅ (soft)   | ❌     | ❌        | ❌     |
| 프로젝트 수정     | ✅    | ✅         | ✅     | ❌        | ❌     |
| 멤버 초대/변경    | ✅    | ✅         | ❌     | ❌        | ❌     |
| 지침 버전 추가    | ✅    | ✅         | ✅     | ❌        | ❌     |
| 지침 열람         | ✅    | ✅         | ✅     | ✅        | ✅     |

## REST 엔드포인트

### 프로젝트

| 메서드 | 경로                                 | 설명 |
|--------|--------------------------------------|------|
| `POST` | `/v1/projects`                       | 프로젝트 생성 |
| `GET`  | `/v1/projects`                       | 로그인 사용자의 프로젝트 목록 (`archived` 필터 지원) |
| `GET`  | `/v1/projects/{project_id}`          | 단일 프로젝트 조회 |
| `PATCH`| `/v1/projects/{project_id}`          | 이름/설명/상태/보관 여부/조직 변경 |
| `DELETE`| `/v1/projects/{project_id}`         | `hard_delete=true` 시 영구 삭제, 기본은 `archived=true` 설정 |
| `POST` | `/v1/projects/{project_id}/clone`    | 동일 설명·상태로 새 프로젝트 복제 (`name`만 입력) |

### 멤버십

| 메서드 | 경로                                                     | 설명 |
|--------|----------------------------------------------------------|------|
| `POST` | `/v1/projects/{project_id}/members`                      | 사용자 초대 (`role` 지정) |
| `GET`  | `/v1/projects/{project_id}/members`                      | 멤버 목록 조회 |
| `PATCH`| `/v1/projects/{project_id}/members/{member_user_id}`     | 역할 변경 |
| `DELETE`| `/v1/projects/{project_id}/members/{member_user_id}`    | 멤버 제거 |

### 지침

| 메서드 | 경로                                                      | 설명 |
|--------|-----------------------------------------------------------|------|
| `POST` | `/v1/projects/{project_id}/instructions`                  | 새 버전 생성 (`content` 필요) |
| `GET`  | `/v1/projects/{project_id}/instructions`                  | 버전 목록 (최신 순) |
| `GET`  | `/v1/projects/{project_id}/instructions/{version}`        | 특정 버전 조회 |

## 예시 페이로드

### 1. 프로젝트 생성

```http
POST /v1/projects
X-User-ID: 00000000-0000-0000-0000-000000000001
Content-Type: application/json

{
  "name": "계약 검토 프로젝트",
  "description": "2025년 1분기 계약서 리뷰",
  "status": "active"
}
```

응답:

```json
{
  "id": "9c9fe4fd-3a4e-4f63-a27c-59a4fa275aa1",
  "name": "계약 검토 프로젝트",
  "description": "2025년 1분기 계약서 리뷰",
  "status": "active",
  "org_id": null,
  "archived": false,
  "created_at": "2025-01-15T02:41:22.481Z",
  "updated_at": "2025-01-15T02:41:22.481Z",
  "created_by": "00000000-0000-0000-0000-000000000001"
}
```

### 2. 지침 버전 관리

```http
POST /v1/projects/9c9fe4fd-3a4e-4f63-a27c-59a4fa275aa1/instructions
X-User-ID: 00000000-0000-0000-0000-000000000001
Content-Type: application/json

{
  "content": "답변은 존댓말로 작성하고, 근거 조문을 명시하세요."
}
```

응답:

```json
{
  "project_id": "9c9fe4fd-3a4e-4f63-a27c-59a4fa275aa1",
  "version": 1,
  "content": "답변은 존댓말로 작성하고, 근거 조문을 명시하세요.",
  "created_by": "00000000-0000-0000-0000-000000000001",
  "created_at": "2025-01-15T02:42:03.771Z"
}
```

## 에러 코드

- `401 Authentication required`: `X-User-ID` 누락 또는 파싱 실패.
- `403 Requires <role> role or higher`: 권한 부족 (예: 멤버가 아닌 사용자).
- `404 Project/Member/Instruction not found`: 리소스 없음.
- `400 ValueError`: 중복 멤버 추가 등 비즈니스 로직 위반.

## 마이그레이션 007과의 정합성

- `audit_logs`, `memories`, `files`, `project_chats`, `snapshots`, `usage_ledger`, `project_budgets` 테이블이 삭제되었습니다.
- `WorkspaceService`는 더 이상 해당 모델을 임포트하거나 조작하지 않습니다.
- 감사 로그 헬퍼 `_log_audit`는 no-op으로 유지되어 과거 호출부와의 호환성을 지키지만 DB를 건드리지 않습니다.

이 문서를 기준으로 API와 서비스 레이어를 확장하면, 다시 테이블을 추가하기 전까지는 migration 007에 정의된 스키마와 충돌하지 않습니다.
