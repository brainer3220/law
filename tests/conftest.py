"""
Test configuration and fixtures for the test suite
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import requests
import time


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture"""
    return {
        "base_url": "http://localhost:8000",
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1,
        "test_queries": [
            "계약 해지에 관한 판례를 알려줘",
            "민사소송 절차는 어떻게 되나요?", 
            "손해배상 책임에 대해 설명해주세요",
            "부동산 매매계약의 효력",
            "소멸시효 완성의 효과"
        ]
    }


@pytest.fixture(scope="session")
def temp_directory():
    """Create temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_legal_documents():
    """Sample legal documents for testing"""
    return [
        {
            "content": "민사소송은 개인 간의 분쟁을 해결하는 법적 절차입니다. 당사자는 법원에 소를 제기하여 분쟁을 해결할 수 있습니다.",
            "source": "court_decisions",
            "metadata": {
                "case_id": "2023가합12345",
                "court": "서울중앙지방법원",
                "date": "2023-01-15",
                "case_type": "민사"
            }
        },
        {
            "content": "계약의 해지는 당사자 일방의 의사표시로 계약관계를 소급적으로 소멸시키는 것입니다. 민법 제543조에 의하면 상대방의 채무불이행이 있을 때 해지할 수 있습니다.",
            "source": "statutes",
            "metadata": {
                "law_name": "민법",
                "article": "제543조",
                "chapter": "제3편 채권"
            }
        },
        {
            "content": "손해배상책임은 고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자가 그 손해를 배상할 책임을 말합니다. 민법 제750조가 근거조문입니다.",
            "source": "legal_interpretations",
            "metadata": {
                "interpretation_id": "법제처-2023-001",
                "topic": "손해배상",
                "date": "2023-03-10"
            }
        },
        {
            "content": "부동산 매매계약의 효력은 당사자 간의 합의가 있으면 성립합니다. 등기는 제3자에 대한 대항요건일 뿐 계약의 성립요건은 아닙니다.",
            "source": "administrative_decisions",
            "metadata": {
                "decision_id": "국세청-2023-456",
                "category": "부동산",
                "agency": "국세청"
            }
        },
        {
            "content": "소멸시효의 완성은 권리자가 권리를 행사할 수 있는 때로부터 일정기간이 경과함으로써 발생합니다. 일반적으로 10년의 소멸시효가 적용됩니다.",
            "source": "court_decisions",
            "metadata": {
                "case_id": "2022다987654",
                "court": "대법원",
                "date": "2022-12-05",
                "case_type": "민사"
            }
        }
    ]


@pytest.fixture
def mock_search_results():
    """Mock search results for testing"""
    return [
        {
            "sentence": "민사소송은 개인 간의 분쟁을 해결하는 법적 절차입니다.",
            "source": "court_decisions",
            "score": 0.95,
            "document": {
                "case_id": "2023가합12345",
                "court": "서울중앙지방법원"
            },
            "rank": 1
        },
        {
            "sentence": "계약의 해지는 당사자 일방의 의사표시로 이루어집니다.",
            "source": "statutes",
            "score": 0.87,
            "document": {
                "law_name": "민법",
                "article": "제543조"
            },
            "rank": 2
        },
        {
            "sentence": "손해배상책임은 고의 또는 과실로 인한 위법행위를 요건으로 합니다.",
            "source": "legal_interpretations",
            "score": 0.82,
            "document": {
                "interpretation_id": "법제처-2023-001"
            },
            "rank": 3
        }
    ]


def wait_for_server(base_url: str, max_wait: int = 60, check_interval: int = 2):
    """Wait for server to be available"""
    end_time = time.time() + max_wait
    
    while time.time() < end_time:
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("data_loaded"):
                    return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception:
            pass
        
        time.sleep(check_interval)
    
    return False


@pytest.fixture(scope="session", autouse=True)
def ensure_server():
    """Ensure server is running for integration tests"""
    base_url = "http://localhost:8000"
    
    # Check if server is already running
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("data_loaded"):
                print("✅ Server is already running and ready")
                yield
                return
    except:
        pass
    
    print("⚠️ Server not running or not ready.")
    print("To run integration tests, start the server first:")
    print("  python manage.py start")
    print("or:")  
    print("  python main.py")
    
    # Skip integration tests if server is not available
    pytest.skip("Server not available for integration tests")


class TestDataGenerator:
    """Generate test data for various scenarios"""
    
    @staticmethod
    def generate_queries(count: int = 10) -> list:
        """Generate test queries"""
        base_queries = [
            "계약 해지",
            "민사소송 절차", 
            "손해배상 책임",
            "부동산 매매",
            "소멸시효",
            "법정이율",
            "임대차계약",
            "불법행위",
            "물권법",
            "채권법"
        ]
        
        queries = []
        for i in range(count):
            base = base_queries[i % len(base_queries)]
            if i < len(base_queries):
                queries.append(f"{base}에 관한 판례")
            else:
                queries.append(f"{base} 관련 법령")
        
        return queries
    
    @staticmethod
    def generate_invalid_requests() -> list:
        """Generate invalid request payloads for testing"""
        return [
            {"query": ""},  # Empty query
            {"query": "test", "method": "invalid"},  # Invalid method
            {"query": "test", "top_k": 0},  # Invalid top_k
            {"query": "test", "top_k": 1000},  # Too large top_k
            {"query": "test", "min_score": -0.1},  # Invalid min_score
            {"query": "test", "min_score": 1.5},  # Invalid min_score
            {},  # Missing query
            {"method": "faiss"},  # Missing query
            {"query": "a" * 2000},  # Too long query
        ]


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Add custom markers
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test (requires running server)"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance test (may take longer)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers",
        "stress: mark test as stress test"
    )
    config.addinivalue_line(
        "markers",
        "exceptions: mark test as exception handling test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Auto-mark integration tests
        if "e2e" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Auto-mark performance tests  
        if "performance" in item.nodeid or "load" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        
        # Auto-mark unit tests
        if "test_comprehensive" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Auto-mark stress tests
        if "stress" in item.nodeid or "load" in item.nodeid:
            item.add_marker(pytest.mark.stress)
            item.add_marker(pytest.mark.slow)
        
        # Auto-mark exception tests
        if "exception" in item.nodeid:
            item.add_marker(pytest.mark.exceptions)
        
        # Mark slow tests
        if any(keyword in item.name.lower() for keyword in ["stress", "load", "memory", "large"]):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.slow)
