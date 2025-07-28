# Test Documentation

이 문서는 Legal RAG API의 테스트 시스템에 대한 종합적인 가이드입니다.

## 📋 테스트 구조

### 테스트 파일 구성

```
tests/
├── __init__.py                 # 테스트 패키지 초기화
├── conftest.py                # 공통 픽스처 및 설정
├── test_comprehensive.py      # 종합 단위 테스트
├── test_e2e.py               # End-to-End 테스트
├── test_performance.py       # 성능 테스트
├── test_exceptions.py        # 예외 처리 테스트 (NEW)
├── test_stress.py           # 스트레스 테스트 (NEW)
├── test_utils.py            # 테스트 유틸리티 (NEW)
└── test_coverage.py         # 커버리지 리포팅 (NEW)
```

### 테스트 카테고리

- **Unit Tests** (`unit`): 개별 컴포넌트의 단위 테스트
- **Integration Tests** (`integration`): 컴포넌트 간 통합 테스트
- **E2E Tests** (`e2e`): 전체 시스템 End-to-End 테스트
- **Performance Tests** (`performance`): 성능 및 응답시간 테스트
- **Stress Tests** (`stress`): 부하 및 스트레스 테스트
- **Exception Tests** (`exceptions`): 예외 상황 처리 테스트
- **Smoke Tests** (`smoke`): 빠른 검증 테스트
- **Critical Tests** (`critical`): 릴리즈 필수 테스트

## 🚀 테스트 실행

### 기본 실행

```bash
# 모든 테스트 실행 (커버리지 포함)
./run_enhanced_tests.sh

# 또는 기존 방식
python -m pytest --cov=. --cov-report=html
```

### 선택적 테스트 실행

```bash
# 단위 테스트만 실행
./run_enhanced_tests.sh unit

# 통합 테스트만 실행
./run_enhanced_tests.sh integration

# 빠른 스모크 테스트
./run_enhanced_tests.sh --smoke-only

# 느린 테스트 제외
./run_enhanced_tests.sh --fast

# 병렬 실행
./run_enhanced_tests.sh -p unit

# 상세 출력
./run_enhanced_tests.sh -v unit
```

### 고급 옵션

```bash
# 커버리지 없이 실행
./run_enhanced_tests.sh --no-coverage

# 리포트 생성 없이 실행
./run_enhanced_tests.sh --no-reports

# 가장 느린 테스트 10개 표시
./run_enhanced_tests.sh -s

# 도움말 보기
./run_enhanced_tests.sh --help
```

## 📊 커버리지 리포팅

### 커버리지 목표
- **최소 커버리지**: 80%
- **목표 커버리지**: 90%+

### 리포트 확인

```bash
# HTML 리포트 (브라우저에서 열기)
open htmlcov/index.html

# 터미널에서 요약 보기
coverage report --show-missing

# 특정 파일 커버리지 확인
coverage report --include="main.py"
```

### 커버리지 제외 규칙

다음 항목들은 커버리지에서 제외됩니다:
- 테스트 파일들 (`tests/*`)
- 가상환경 (`venv/*`, `.venv/*`)
- 관리 스크립트 (`manage.py`, `run_tests.py`)
- `__pycache__` 디렉토리
- `if __name__ == "__main__"` 블록

## 🛠️ 테스트 작성 가이드

### 새 테스트 작성

1. **테스트 파일 명명**: `test_*.py` 형식
2. **테스트 클래스**: `Test*` 형식
3. **테스트 함수**: `test_*` 형식

### 테스트 마커 사용

```python
import pytest

@pytest.mark.unit
def test_data_loading():
    """단위 테스트 예시"""
    pass

@pytest.mark.integration
def test_api_integration():
    """통합 테스트 예시"""
    pass

@pytest.mark.slow
@pytest.mark.stress
def test_high_load():
    """스트레스 테스트 예시"""
    pass
```

### 픽스처 활용

```python
def test_with_mock_data(sample_legal_documents):
    """샘플 데이터를 사용한 테스트"""
    assert len(sample_legal_documents) > 0

def test_with_temp_directory(temp_directory):
    """임시 디렉토리를 사용한 테스트"""
    test_file = temp_directory / "test.txt"
    test_file.write_text("test content")
    assert test_file.exists()
```

## 🔧 고급 테스트 기능

### 성능 모니터링

```python
from tests.test_utils import performance_test, TestTimer, MemoryMonitor

@performance_test
def test_with_performance_monitoring():
    """성능 모니터링이 포함된 테스트"""
    # 테스트 코드
    pass

def test_with_manual_timing():
    """수동 타이밍 측정"""
    with TestTimer("Custom test") as timer:
        # 테스트 코드
        pass
    print(f"Test took {timer.duration:.3f}s")
```

### Mock 및 Patch 사용

```python
from tests.test_utils import mock_data_loader, mock_retrievers

def test_with_mocked_components():
    """Mock을 사용한 테스트"""
    with mock_data_loader(loaded=True) as loader:
        with mock_retrievers() as retrievers:
            # 테스트 코드
            pass
```

### 예외 처리 테스트

```python
def test_exception_handling():
    """예외 상황 테스트"""
    with pytest.raises(ValueError, match="Invalid input"):
        # 예외를 발생시키는 코드
        pass
```

## 📈 테스트 품질 메트릭

### 자동 품질 평가

테스트 실행 후 자동으로 다음 메트릭이 표시됩니다:

- **성공률**: 전체 테스트 중 통과한 비율
- **커버리지**: 코드 커버리지 비율
- **성능**: 평균 응답시간 및 메모리 사용량
- **품질 등급**: Excellent → Very Good → Good → Fair → Needs Improvement

### 품질 기준

- **Excellent**: 95% 이상 성공률
- **Very Good**: 90-94% 성공률
- **Good**: 80-89% 성공률
- **Fair**: 70-79% 성공률
- **Needs Improvement**: 70% 미만

## 🚨 CI/CD 통합

### GitHub Actions용 설정

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev
      - name: Run tests
        run: ./run_enhanced_tests.sh --no-reports
      - name: Upload coverage
        uses: codecov/codecov-action@v1
        with:
          file: ./test_reports/coverage.xml
```

## 🐛 트러블슈팅

### 일반적인 문제

1. **서버 연결 실패**
   ```bash
   # 서버 시작
   python manage.py start-server
   
   # 헬스 체크
   curl http://localhost:8000/health
   ```

2. **메모리 부족**
   ```bash
   # 가벼운 테스트만 실행
   ./run_enhanced_tests.sh --fast
   
   # 단위 테스트만 실행
   ./run_enhanced_tests.sh unit
   ```

3. **의존성 문제**
   ```bash
   # 의존성 재설치
   uv sync --dev
   
   # 캐시 정리
   pip cache purge
   ```

### 디버깅 팁

```bash
# 상세 로그와 함께 실행
./run_enhanced_tests.sh -v

# 실패한 테스트만 재실행
python -m pytest --lf

# 특정 테스트만 실행
python -m pytest tests/test_comprehensive.py::TestModels::test_query_request_valid

# PDB 디버거와 함께 실행
python -m pytest --pdb
```

## 📝 리포트 및 문서

### 생성되는 리포트

- **HTML 커버리지 리포트**: `htmlcov/index.html`
- **XML 커버리지 리포트**: `test_reports/coverage.xml`
- **HTML 테스트 리포트**: `test_reports/report.html`
- **테스트 요약**: `test_reports/summary.json`

### 지속적인 모니터링

```bash
# 커버리지 트렌드 모니터링
echo "$(date): $(coverage report --format=total)" >> coverage_history.txt

# 성능 벤치마크 저장
./run_enhanced_tests.sh performance > performance_$(date +%Y%m%d).log
```

---

## 💡 베스트 프랙티스

1. **테스트 독립성**: 각 테스트는 독립적으로 실행 가능해야 함
2. **명확한 명명**: 테스트 이름으로 목적을 명확히 표현
3. **적절한 마커**: 테스트 유형에 맞는 마커 사용
4. **Mock 활용**: 외부 의존성은 Mock으로 처리
5. **성능 고려**: 긴 테스트는 `slow` 마커 추가
6. **문서화**: 복잡한 테스트는 주석으로 설명
7. **정기 실행**: CI/CD에서 자동 실행 설정
8. **커버리지 유지**: 새 코드 추가시 테스트도 함께 작성

이 테스트 시스템을 통해 Legal RAG API의 품질과 안정성을 지속적으로 보장할 수 있습니다.
