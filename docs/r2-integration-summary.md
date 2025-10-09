# Cloudflare R2 Integration - Implementation Summary

## Overview

`#file:workspace`에 **Cloudflare R2 Object Storage** 통합을 완료했습니다. 파일 업로드/다운로드 기능이 R2를 사용하도록 구현되었으며, S3 호환 API를 통해 boto3로 연동됩니다.

## 구현된 기능

### 1. R2 클라이언트 모듈 (`packages/legal_tools/workspace/storage/`)

**`r2_client.py`**:
- `R2Config`: R2 연결 설정 클래스
  - 환경변수에서 자동 로드 (`from_env()`)
  - 엔드포인트, 액세스 키, 버킷, 파일 크기 제한 등 설정
- `R2Client`: R2 작업 클라이언트 (boto3 S3 API 사용)
  - `upload_file()`: 파일 업로드 + SHA256 체크섬 자동 계산
  - `download_file()`: 파일 다운로드
  - `delete_file()`: 파일 삭제
  - `generate_presigned_upload_url()`: 클라이언트 직접 업로드용 URL 생성
  - `generate_presigned_download_url()`: 다운로드용 임시 URL 생성
  - `get_public_url()`: Public 도메인 URL 생성 (선택)
  - `file_exists()`: 파일 존재 확인
  - `get_file_metadata()`: 파일 메타데이터 조회

### 2. Workspace Service 통합 (`service.py`)

**`WorkspaceSettings`**:
- `r2_config: Optional[R2Config]` 필드 추가
- `from_env()`: R2 설정 자동 로드 (없으면 None, 파일 업로드 비활성화)

**`WorkspaceService`**:
- `r2_client: Optional[R2Client]` 속성 추가
- `create_file()`: 파일 메타데이터 생성 + 선택적 R2 업로드
  - `file_content` 파라미터 추가 (직접 업로드 시)
  - R2 업로드 결과로 체크섬/크기 자동 업데이트
- `delete_file()`: DB 삭제 + R2 파일 삭제
  - R2 삭제 실패 시에도 DB는 삭제 (로그만 남김)
- `generate_upload_url()`: Presigned upload URL 생성 (권한 검사 포함)
- `generate_download_url()`: Presigned download URL 생성 (권한 검사 포함)

### 3. API 엔드포인트 (`api.py`)

**새 엔드포인트**:

1. **`POST /v1/projects/{project_id}/files/presigned-upload`**
   - Presigned upload URL 생성 (클라이언트 직접 업로드)
   - 반환: `upload_url`, `r2_key`, `expires_in`
   - 권장 방식: 큰 파일 업로드 시 서버 부하 감소

2. **`POST /v1/projects/{project_id}/files`**
   - 파일 메타데이터 생성 (Presigned URL 업로드 완료 후)
   - Presigned URL 워크플로우의 마지막 단계

3. **`POST /v1/projects/{project_id}/files/direct-upload`**
   - 서버를 통한 직접 업로드 (multipart/form-data)
   - 소규모 파일에 적합

4. **`GET /v1/files/{file_id}/download-url`**
   - Presigned download URL 생성
   - 쿼리 파라미터: `expiry` (선택, 초 단위)

**업데이트된 엔드포인트**:
- `DELETE /v1/files/{file_id}`: DB + R2에서 파일 삭제

### 4. 스키마 추가 (`schemas.py`)

- `PresignedUploadRequest`: Presigned URL 요청
- `PresignedUploadResponse`: Presigned URL 응답
- `PresignedDownloadResponse`: Presigned 다운로드 URL 응답
- `DirectFileUploadRequest`: 직접 업로드 요청 (form-data)

### 5. 의존성 업데이트 (`pyproject.toml`)

```toml
"boto3>=1.34",           # S3 호환 API 클라이언트
"python-multipart>=0.0.6",  # FastAPI multipart/form-data 지원
```

### 6. 문서화

**`.env.example`**:
- R2 환경 변수 샘플 추가
- Workspace API 설정 추가

**`docs/cloudflare-r2-integration.md`**:
- R2 계정 설정 가이드
- 환경 변수 설정 방법
- 파일 업로드/다운로드 사용 예제 (Python)
- 아키텍처 다이어그램
- 보안 고려사항
- 비용 최적화 팁
- 문제 해결 가이드

### 7. 테스트 (`tests/test_r2_integration.py`)

- `R2Config` 테스트 (환경변수 로드)
- `R2Client` 테스트 (업로드, 삭제, Presigned URL 생성)
- Mock을 사용한 단위 테스트

## 환경 변수

```bash
# 필수
R2_ENDPOINT_URL="https://<account_id>.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID="<your_access_key_id>"
R2_SECRET_ACCESS_KEY="<your_secret_access_key>"
R2_BUCKET_NAME="law-workspace-files"

# 선택
R2_PUBLIC_DOMAIN=""              # Public 액세스용 커스텀 도메인
R2_MAX_FILE_SIZE="104857600"     # 최대 파일 크기 (bytes, 기본: 100MB)
R2_PRESIGNED_URL_EXPIRY="3600"   # Presigned URL 유효 시간 (초, 기본: 1시간)
```

## 사용 예시

### Presigned URL 방식 (권장)

```python
import requests

# 1. Presigned URL 요청
response = requests.post(
    "http://localhost:8000/v1/projects/{project_id}/files/presigned-upload",
    headers={"X-User-ID": user_id},
    json={"name": "doc.pdf", "mime": "application/pdf"}
)
upload_url = response.json()["upload_url"]
r2_key = response.json()["r2_key"]

# 2. 파일 직접 업로드
with open("doc.pdf", "rb") as f:
    requests.put(upload_url, data=f, headers={"Content-Type": "application/pdf"})

# 3. 메타데이터 저장
requests.post(
    f"http://localhost:8000/v1/projects/{project_id}/files",
    headers={"X-User-ID": user_id},
    json={"r2_key": r2_key, "name": "doc.pdf", "mime": "application/pdf"}
)
```

### 직접 업로드 방식

```python
with open("doc.pdf", "rb") as f:
    requests.post(
        f"http://localhost:8000/v1/projects/{project_id}/files/direct-upload",
        headers={"X-User-ID": user_id},
        files={"file": ("doc.pdf", f, "application/pdf")},
        data={"name": "doc.pdf"}
    )
```

## 보안 특징

1. **권한 검사**: 모든 파일 작업은 프로젝트 권한 기반 (VIEWER, EDITOR, etc.)
2. **민감도 분류**: `public`, `internal`, `confidential`, `restricted`
3. **시간 제한**: Presigned URL은 기본 1시간만 유효
4. **체크섬 검증**: SHA256 체크섬 자동 계산 및 저장
5. **감사 로깅**: 모든 파일 작업은 audit log에 기록

## 아키텍처 개선 포인트

### 현재 구현
- ✅ S3 호환 API (boto3) 사용
- ✅ Presigned URL 지원 (서버 부하 감소)
- ✅ 직접 업로드 지원 (소규모 파일)
- ✅ 권한 기반 접근 제어
- ✅ 체크섬 검증

### 향후 개선 가능
- 🔄 멀티파트 업로드 (매우 큰 파일 >100MB)
- 🔄 CDN 연동 (자주 접근하는 파일 캐싱)
- 🔄 자동 아카이빙 (오래된 파일 정리)
- 🔄 바이러스 스캔 (업로드 파일 검사)
- 🔄 텍스트 추출 + 벡터 인덱싱 (검색 통합)

## 변경된 파일

```
pyproject.toml                                     # boto3 의존성 추가
.env.example                                        # R2 환경 변수 샘플
packages/legal_tools/workspace/
  ├── storage/
  │   ├── __init__.py                              # 신규
  │   └── r2_client.py                             # 신규
  ├── service.py                                   # R2 통합
  ├── api.py                                       # 새 엔드포인트
  └── schemas.py                                   # 새 스키마
docs/
  └── cloudflare-r2-integration.md                 # 신규 문서
tests/
  └── test_r2_integration.py                       # 신규 테스트
```

## 다음 단계

1. **의존성 설치**:
   ```bash
   uv sync
   ```

2. **R2 계정 설정** (문서 참조):
   - Cloudflare 대시보드에서 버킷 생성
   - API 토큰 발급
   - `.env` 파일에 설정 추가

3. **테스트 실행**:
   ```bash
   pytest tests/test_r2_integration.py -v
   ```

4. **API 서버 실행**:
   ```bash
   # R2가 설정되지 않으면 파일 업로드 비활성화 (다른 기능은 정상 동작)
   python -m packages.legal_tools.workspace.api
   ```

## 참고 자료

- [Cloudflare R2 문서](https://developers.cloudflare.com/r2/)
- [boto3 S3 API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [프로젝트 문서](docs/cloudflare-r2-integration.md)
