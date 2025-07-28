"""
Test utilities and helpers for improved testing
"""
import time
import asyncio
import psutil
import os
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import Mock, patch
import requests
from contextlib import contextmanager


class UtilTimer:
    """Context manager for measuring test execution time"""
    
    def __init__(self, test_name: str = "Test"):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        print(f"⏱️ {self.test_name} completed in {duration:.3f}s")
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


class MemoryMonitor:
    """Monitor memory usage during tests"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.initial_memory = None
        self.peak_memory = None
    
    def start(self):
        """Start monitoring memory"""
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory
    
    def update_peak(self):
        """Update peak memory usage"""
        current_memory = self.process.memory_info().rss
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
    
    def get_stats(self) -> Dict[str, float]:
        """Get memory statistics in MB"""
        current_memory = self.process.memory_info().rss
        return {
            "initial_mb": self.initial_memory / 1024 / 1024,
            "current_mb": current_memory / 1024 / 1024,
            "peak_mb": self.peak_memory / 1024 / 1024,
            "increase_mb": (current_memory - self.initial_memory) / 1024 / 1024
        }


class UtilServerHealthChecker:
    """Utility to check server health and readiness"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def is_server_running(self, timeout: int = 5) -> bool:
        """Check if server is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=timeout)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def wait_for_server(self, max_wait: int = 60, check_interval: int = 2) -> bool:
        """Wait for server to be ready"""
        elapsed = 0
        while elapsed < max_wait:
            if self.is_server_running():
                # Additional check for data loaded
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    data = response.json()
                    if data.get("data_loaded", False):
                        return True
                except:
                    pass
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        return False
    
    def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """Get server statistics"""
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return None


class MockDataFactory:
    """Factory for creating mock data for tests"""
    
    @staticmethod
    def create_legal_documents(count: int = 10) -> List[Dict[str, Any]]:
        """Create mock legal documents"""
        documents = []
        for i in range(count):
            doc_type = ["court_decisions", "statutes", "legal_interpretations", "administrative_decisions"][i % 4]
            documents.append({
                "content": f"법률 문서 내용 {i+1}: 이것은 {doc_type}에 관한 내용입니다.",
                "source": doc_type,
                "metadata": {
                    "id": f"doc_{i+1}",
                    "type": doc_type,
                    "date": f"2024-01-{(i % 28) + 1:02d}"
                }
            })
        return documents
    
    @staticmethod
    def create_search_queries() -> List[str]:
        """Create realistic search queries"""
        return [
            "계약 해지 조건",
            "민사소송 절차",
            "손해배상 책임",
            "부동산 매매계약",
            "소멸시효 완성",
            "노동계약 해지",
            "저작권 침해",
            "행정처분 취소",
            "상속재산 분할",
            "회사법 개정"
        ]
    
    @staticmethod
    def create_mock_retriever_results(query: str, count: int = 5) -> List[Dict[str, Any]]:
        """Create mock retriever results"""
        results = []
        for i in range(count):
            score = 0.9 - (i * 0.1)  # Decreasing scores
            results.append({
                "sentence": f"{query}에 관한 법률 조항 {i+1}",
                "source": "mock_source",
                "score": max(score, 0.1),
                "document": {
                    "id": f"mock_doc_{i+1}",
                    "content": f"Mock document content for {query}",
                    "metadata": {"mock": True}
                },
                "rank": i + 1
            })
        return results


@contextmanager
def mock_retrievers():
    """Context manager to mock all retrievers"""
    mock_results = MockDataFactory.create_mock_retriever_results("test query")
    
    with patch('main.tfidf_retriever') as mock_tfidf, \
         patch('main.embedding_retriever') as mock_embedding, \
         patch('main.faiss_retriever') as mock_faiss:
        
        mock_tfidf.search.return_value = mock_results
        mock_embedding.search.return_value = mock_results
        mock_faiss.search.return_value = mock_results
        
        yield {
            'tfidf': mock_tfidf,
            'embedding': mock_embedding,
            'faiss': mock_faiss
        }


@contextmanager
def mock_data_loader(loaded: bool = True, documents: Optional[List[Dict]] = None):
    """Context manager to mock data loader"""
    if documents is None:
        documents = MockDataFactory.create_legal_documents()
    
    mock_loader = Mock()
    mock_loader.is_loaded = loaded
    mock_loader.get_data.return_value = (
        [doc["content"] for doc in documents],
        [doc["source"] for doc in documents],
        documents
    )
    mock_loader.get_stats.return_value = {
        "total_sentences": len(documents),
        "total_documents": len(documents),
        "document_type_counts": {
            "court_decisions": sum(1 for d in documents if d["source"] == "court_decisions"),
            "statutes": sum(1 for d in documents if d["source"] == "statutes"),
            "legal_interpretations": sum(1 for d in documents if d["source"] == "legal_interpretations"),
            "administrative_decisions": sum(1 for d in documents if d["source"] == "administrative_decisions")
        }
    }
    
    with patch('main.data_loader', mock_loader):
        yield mock_loader


class UtilMetrics:
    """Collect and analyze test metrics"""
    
    def __init__(self):
        self.metrics = {
            "execution_times": [],
            "memory_usage": [],
            "api_response_times": [],
            "error_rates": {}
        }
    
    def record_execution_time(self, test_name: str, duration: float):
        """Record test execution time"""
        self.metrics["execution_times"].append({
            "test": test_name,
            "duration": duration
        })
    
    def record_memory_usage(self, test_name: str, memory_mb: float):
        """Record memory usage"""
        self.metrics["memory_usage"].append({
            "test": test_name,
            "memory_mb": memory_mb
        })
    
    def record_api_response_time(self, endpoint: str, response_time: float):
        """Record API response time"""
        self.metrics["api_response_times"].append({
            "endpoint": endpoint,
            "response_time": response_time
        })
    
    def record_error(self, test_name: str, error_type: str):
        """Record test error"""
        if test_name not in self.metrics["error_rates"]:
            self.metrics["error_rates"][test_name] = {}
        if error_type not in self.metrics["error_rates"][test_name]:
            self.metrics["error_rates"][test_name][error_type] = 0
        self.metrics["error_rates"][test_name][error_type] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            "total_tests": len(self.metrics["execution_times"]),
            "avg_execution_time": sum(t["duration"] for t in self.metrics["execution_times"]) / max(len(self.metrics["execution_times"]), 1),
            "max_memory_usage": max((m["memory_mb"] for m in self.metrics["memory_usage"]), default=0),
            "avg_api_response_time": sum(r["response_time"] for r in self.metrics["api_response_times"]) / max(len(self.metrics["api_response_times"]), 1),
            "total_errors": sum(sum(errors.values()) for errors in self.metrics["error_rates"].values())
        }


def performance_test(func: Callable) -> Callable:
    """Decorator to add performance monitoring to tests"""
    def wrapper(*args, **kwargs):
        timer = TestTimer(func.__name__)
        memory_monitor = MemoryMonitor()
        
        memory_monitor.start()
        
        with timer:
            result = func(*args, **kwargs)
        
        memory_stats = memory_monitor.get_stats()
        
        # Log performance metrics
        print(f"📊 Performance metrics for {func.__name__}:")
        print(f"   ⏱️ Duration: {timer.duration:.3f}s")
        print(f"   🧠 Memory increase: {memory_stats['increase_mb']:.2f}MB")
        print(f"   📈 Peak memory: {memory_stats['peak_mb']:.2f}MB")
        
        return result
    
    return wrapper


# Global test metrics instance
test_metrics = TestMetrics()


def pytest_configure(config):
    """Pytest configuration hook"""
    print("🧪 Starting test suite with enhanced monitoring...")


def pytest_runtest_teardown(item, nextitem):
    """Pytest teardown hook"""
    # Clean up any test artifacts
    pass


def pytest_sessionfinish(session, exitstatus):
    """Pytest session finish hook"""
    summary = test_metrics.get_summary()
    print("\n📊 Test Session Summary:")
    print(f"   Total tests: {summary['total_tests']}")
    print(f"   Average execution time: {summary['avg_execution_time']:.3f}s")
    print(f"   Max memory usage: {summary['max_memory_usage']:.2f}MB")
    print(f"   Average API response time: {summary['avg_api_response_time']:.3f}s")
    print(f"   Total errors: {summary['total_errors']}")
