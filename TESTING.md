# Legal RAG API v2.0 Testing Guide

## 📋 테스트 개요

Legal RAG API v2.0은 포괄적인 다층 테스트 전략을 제공합니다:

- **Unit Tests** (`test_unit.py`): 개별 컴포넌트 테스트
- **Integration Tests** (`test_comprehensive.py`): API 엔드포인트 통합 테스트  
- **Performance Tests** (`test_performance.py`): 성능 및 부하 테스트
- **End-to-End Tests** (`test_e2e.py`): 완전한 워크플로우 테스트
- **Stress Tests** (`test_stress.py`): 스트레스 테스트 및 리소스 한계 테스트
- **Exception Tests** (`test_exceptions.py`): 예외 처리 및 엣지 케이스 테스트

## 🛠️ 테스트 실행 방법

### 1. UV 기반 테스트 실행 (권장)

```bash
# 모든 테스트 실행
uv run python -m pytest tests/

# 특정 테스트 카테고리
uv run python -m pytest tests/ -m unit           # 단위 테스트만
uv run python -m pytest tests/ -m integration    # 통합 테스트만
uv run python -m pytest tests/ -m performance    # 성능 테스트만
uv run python -m pytest tests/ -m stress         # 스트레스 테스트만
uv run python -m pytest tests/ -m e2e            # E2E 테스트만
uv run python -m pytest tests/ -m exceptions     # 예외 테스트만

# 커버리지 리포트와 함께 실행
uv run python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# 특정 테스트 파일 실행
uv run python -m pytest tests/test_unit.py -v
```

### 2. 향상된 테스트 러너 사용

```bash
# 실행 권한 부여
chmod +x run_enhanced_tests.sh

# 모든 테스트 실행 (커버리지 포함)
./run_enhanced_tests.sh --all --coverage --html

# 특정 테스트 타입
./run_enhanced_tests.sh --unit --coverage
./run_enhanced_tests.sh --integration --verbose
./run_enhanced_tests.sh --performance --detailed
./run_enhanced_tests.sh --stress --timeout 300

# 빠른 검증 (critical 테스트만)
./run_enhanced_tests.sh --smoke --fast
```

### 3. 기본 관리 스크립트 사용

```bash
# 기본 테스트
python manage.py test

# 특정 테스트 타입 (레거시)
python manage.py test unit
python manage.py test integration
python manage.py test performance
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
