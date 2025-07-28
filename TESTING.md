# Legal RAG API Testing Guide

## 테스트 개요

이 프로젝트는 포괄적인 테스트 슈트를 제공합니다:

- **Unit Tests**: 개별 컴포넌트 테스트
- **Integration Tests**: API 엔드포인트 통합 테스트  
- **Performance Tests**: 성능 및 부하 테스트
- **End-to-End Tests**: 완전한 워크플로우 테스트

## 테스트 실행 방법

### 1. 기본 사용법 (관리 스크립트)

```bash
# 단위 테스트만 실행
python manage.py test unit

# 통합 테스트 실행 (서버 필요)
python manage.py test integration

# 성능 테스트 실행 (서버 필요)
python manage.py test performance

# E2E 테스트 실행 (서버 필요)
python manage.py test e2e

# 모든 테스트 실행
python manage.py test all

# 커버리지 리포트와 함께 실행
python manage.py test all --coverage
```

### 2. 전용 테스트 러너 사용

```bash
# 다양한 테스트 타입
python run_tests.py unit
python run_tests.py integration
python run_tests.py performance
python run_tests.py e2e
python run_tests.py all

# 상세한 리포트 생성
python run_tests.py report

# 서버 상태 확인
python run_tests.py --check-server
```

### 3. 직접 pytest 사용

```bash
# 개발 의존성 설치
uv sync --extra dev

# 단위 테스트
uv run pytest tests/test_comprehensive.py::TestModels -v

# 통합 테스트
uv run pytest tests/test_e2e.py -v

# 커버리지와 함께
uv run pytest --cov=. --cov-report=html
```

### 4. 레거시 테스트 스크립트

```bash
# 기본 API 테스트 (이전 버전)
python test_api.py
```

## 테스트 전 준비사항

### 단위 테스트
- 서버 실행 불필요
- 모킹된 데이터 사용

### 통합/성능/E2E 테스트
- 서버가 실행 중이어야 함
- 데이터가 로드되어 있어야 함

```bash
# 서버 시작
python manage.py start

# 또는
python main.py
```

## 테스트 구조

```
tests/
├── __init__.py
├── conftest.py              # 테스트 설정 및 픽스처
├── test_comprehensive.py    # 포괄적인 단위/통합 테스트
├── test_performance.py      # 성능 테스트
└── test_e2e.py             # E2E 테스트
```

## 테스트 마커

pytest 마커를 사용하여 특정 테스트만 실행:

```bash
# 통합 테스트만 실행
uv run pytest -m integration

# 성능 테스트만 실행  
uv run pytest -m performance

# 느린 테스트 제외
uv run pytest -m "not slow"
```

## 커버리지 리포트

테스트 커버리지 확인:

```bash
# HTML 리포트 생성
python manage.py test all --coverage

# 리포트 확인
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
```

## CI/CD 통합

GitHub Actions 등에서 사용할 수 있는 명령어:

```yaml
# 단위 테스트 (서버 불필요)
- name: Run unit tests
  run: python manage.py test unit --coverage

# 통합 테스트 (서버 시작 후)
- name: Start server
  run: python manage.py start &
  
- name: Wait for server
  run: python run_tests.py --check-server

- name: Run integration tests
  run: python manage.py test integration
```

## 테스트 작성 가이드

### 새로운 단위 테스트 추가

```python
# tests/test_comprehensive.py에 추가
class TestNewFeature:
    def test_new_functionality(self):
        # 테스트 코드
        assert True
```

### 새로운 통합 테스트 추가

```python
# tests/test_e2e.py에 추가
def test_new_api_endpoint(self, ensure_server_running):
    response = requests.get(f"{self.BASE_URL}/new-endpoint")
    assert response.status_code == 200
```

## 문제 해결

### 일반적인 문제들

1. **서버 연결 실패**
   ```bash
   # 서버 상태 확인
   python run_tests.py --check-server
   
   # 서버 시작
   python manage.py start
   ```

2. **의존성 누락**
   ```bash
   # 개발 의존성 설치
   uv sync --extra dev
   ```

3. **포트 충돌**
   ```bash
   # 다른 포트로 서버 시작
   python manage.py start --port 8001
   
   # 테스트에서도 해당 포트 사용
   # tests/conftest.py에서 base_url 수정
   ```

4. **캐시 문제**
   ```bash
   # 캐시 정리
   python manage.py clear-cache
   ```

## 성능 벤치마크

성능 테스트 기준값:

- **단일 요청**: < 5초
- **동시 요청 (10개)**: 80% 이상 성공
- **평균 응답 시간**: < 10초
- **메모리 증가**: < 100MB

## 테스트 데이터

테스트에 사용되는 샘플 데이터:

- 민사법 관련 문서
- 계약, 소송, 손해배상 등 주요 법률 개념
- 다양한 문서 유형 (판례, 법령, 해석례 등)

## 추가 정보

- 테스트는 실제 데이터셋 없이도 모킹된 데이터로 실행 가능
- 성능 테스트는 서버 부하를 발생시키므로 주의
- E2E 테스트는 전체 시스템 검증을 위해 실제 서버 필요
