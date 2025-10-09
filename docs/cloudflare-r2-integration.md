# Cloudflare R2 Object Storage Integration

이 프로젝트는 파일 업로드 기능을 위해 **Cloudflare R2 Object Storage**를 사용합니다. R2는 S3 호환 API를 제공하므로 AWS SDK (boto3)를 통해 연동됩니다.

## 설정 방법

### 1. Cloudflare R2 계정 설정

1. [Cloudflare Dashboard](https://dash.cloudflare.com/)에 로그인
2. R2 메뉴로 이동
3. 버킷 생성:
   - 버킷 이름: `law-workspace-files` (또는 원하는 이름)
   - 리전: 자동 선택됨
4. API 토큰 생성:
   - **Manage R2 API Tokens** 클릭
   - **Create API Token** 선택
   - 권한: `Object Read & Write` (또는 `Admin Read & Write`)
   - 생성된 **Access Key ID**, **Secret Access Key**, **Endpoint URL** 저장

### 2. 환경 변수 설정

`.env` 파일에 다음 변수를 추가:

```bash
# Cloudflare R2 설정 (필수)
R2_ENDPOINT_URL="https://<account_id>.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID="<your_access_key_id>"
R2_SECRET_ACCESS_KEY="<your_secret_access_key>"
R2_BUCKET_NAME="law-workspace-files"

# 선택 옵션
R2_PUBLIC_DOMAIN=""                # Public 액세스용 커스텀 도메인 (선택)
R2_MAX_FILE_SIZE="104857600"       # 최대 파일 크기 (bytes, 기본: 100MB)
R2_PRESIGNED_URL_EXPIRY="3600"     # Presigned URL 유효 시간 (초, 기본: 1시간)
```

### 3. 의존성 설치

```bash
uv sync
```

## 사용 방법

### 파일 업로드 워크플로우

#### 방법 1: Presigned URL 사용 (권장 - 큰 파일)

클라이언트가 직접 R2에 업로드하여 서버 부하를 줄입니다.

```python
import requests

# 1. Presigned Upload URL 요청
response = requests.post(
    "http://localhost:8000/v1/projects/{project_id}/files/presigned-upload",
    headers={"X-User-ID": user_id},
    json={
        "name": "document.pdf",
        "mime": "application/pdf",
        "size_bytes": 1024000,
        "sensitivity": "internal"
    }
)
data = response.json()
upload_url = data["upload_url"]
r2_key = data["r2_key"]

# 2. 파일을 R2에 직접 업로드
with open("document.pdf", "rb") as f:
    requests.put(
        upload_url,
        data=f,
        headers={"Content-Type": "application/pdf"}
    )

# 3. 메타데이터를 DB에 저장
requests.post(
    f"http://localhost:8000/v1/projects/{project_id}/files",
    headers={"X-User-ID": user_id},
    json={
        "r2_key": r2_key,
        "name": "document.pdf",
        "mime": "application/pdf",
        "size_bytes": 1024000,
        "sensitivity": "internal"
    }
)
```

#### 방법 2: 직접 업로드 (간단한 파일)

서버를 통해 업로드합니다.

```python
import requests

with open("document.pdf", "rb") as f:
    response = requests.post(
        f"http://localhost:8000/v1/projects/{project_id}/files/direct-upload",
        headers={"X-User-ID": user_id},
        files={"file": ("document.pdf", f, "application/pdf")},
        data={
            "name": "document.pdf",
            "sensitivity": "internal"
        }
    )
```

### 파일 다운로드

```python
# Presigned Download URL 생성
response = requests.get(
    f"http://localhost:8000/v1/files/{file_id}/download-url",
    headers={"X-User-ID": user_id},
    params={"expiry": 3600}  # 1시간 유효
)
download_url = response.json()["download_url"]

# URL로 파일 다운로드
file_data = requests.get(download_url).content
```

### 파일 삭제

```python
# DB 및 R2에서 파일 삭제
requests.delete(
    f"http://localhost:8000/v1/files/{file_id}",
    headers={"X-User-ID": user_id}
)
```

## 아키텍처

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ 1. POST /presigned-upload
       ▼
┌─────────────────┐
│  Workspace API  │
│   (FastAPI)     │
└────────┬────────┘
         │
         │ 2. Generate presigned URL
         ▼
┌──────────────────┐
│  R2Client        │
│  (boto3 S3 API)  │
└────────┬─────────┘
         │
         │ 3. Return presigned URL
         ▼
┌─────────────┐
│   Client    │────────────────────┐
└─────────────┘                    │
                                   │ 4. PUT file directly
                                   ▼
                          ┌──────────────────┐
                          │  Cloudflare R2   │
                          │ Object Storage   │
                          └──────────────────┘
```

## 보안 고려사항

### 권한 관리

- 모든 파일 작업은 프로젝트 권한 검사를 거칩니다 (VIEWER, EDITOR, MAINTAINER, OWNER).
- Presigned URL은 제한된 시간 동안만 유효합니다 (기본 1시간).

### 데이터 민감도

파일은 민감도 수준으로 분류됩니다:
- `public`: 공개 가능
- `internal`: 내부 전용 (기본값)
- `confidential`: 기밀
- `restricted`: 제한적 접근

### PII/Privilege 마스킹

- 업로드된 파일은 자동으로 텍스트 추출 및 인덱싱됩니다.
- PII (개인식별정보) 및 변호사-의뢰인 특권 정보는 자동 감지 및 마스킹됩니다 (향후 구현).

## 비용 최적화

### R2 가격

Cloudflare R2는 egress (다운로드) 비용이 **무료**입니다:
- 저장: $0.015/GB/월
- Class A 작업 (PUT, LIST): $4.50/백만 요청
- Class B 작업 (GET, HEAD): $0.36/백만 요청

### 권장사항

- 대용량 파일(>10MB)은 **Presigned URL** 방식 사용 (서버 부하 감소)
- 자주 접근하는 파일은 CDN 연동 고려
- 오래된 파일은 자동 아카이빙 설정

## 문제 해결

### R2 연결 실패

```
ValueError: R2 storage is not configured
```

→ 환경 변수가 올바르게 설정되었는지 확인하세요.

### 업로드 실패 (403 Forbidden)

```
ClientError: Access Denied
```

→ R2 API 토큰 권한을 확인하세요. `Object Read & Write` 권한이 필요합니다.

### 파일 크기 초과

```
ValueError: File size exceeds maximum
```

→ `R2_MAX_FILE_SIZE` 환경 변수를 늘리세요 (bytes 단위).

## 참고 자료

- [Cloudflare R2 문서](https://developers.cloudflare.com/r2/)
- [boto3 S3 API 문서](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [S3 호환 API 가이드](https://developers.cloudflare.com/r2/api/s3/)
