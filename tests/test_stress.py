"""
Stress testing and load testing for the Legal RAG API
"""
import pytest
import asyncio
import aiohttp
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import statistics
from unittest.mock import patch

from tests.test_utils import (
    UtilTimer, MemoryMonitor, UtilServerHealthChecker, 
    MockDataFactory, performance_test, test_metrics
)


class TestStressAndLoad:
    """Stress and load testing scenarios"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture(scope="class")
    def server_checker(self):
        return UtilServerHealthChecker(self.BASE_URL)
    
    @performance_test
    def test_concurrent_search_requests(self, server_checker):
        """Test multiple concurrent search requests"""
        if not server_checker.is_server_running():
            pytest.skip("Server not running")
        
        queries = MockDataFactory.create_search_queries()
        num_concurrent = 10
        results = queue.Queue()
        
        def make_search_request(query: str):
            import requests
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.BASE_URL}/search",
                    json={"query": query, "top_k": 3},
                    timeout=30
                )
                end_time = time.time()
                
                results.put({
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "query": query,
                    "success": response.status_code == 200
                })
            except Exception as e:
                results.put({
                    "status_code": 500,
                    "response_time": 30.0,
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        # Launch concurrent requests
        threads = []
        for i in range(num_concurrent):
            query = queries[i % len(queries)]
            thread = threading.Thread(target=make_search_request, args=(query,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Analyze results
        response_times = []
        success_count = 0
        
        while not results.empty():
            result = results.get()
            response_times.append(result["response_time"])
            if result["success"]:
                success_count += 1
        
        # Assertions
        success_rate = success_count / num_concurrent
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        print(f"📊 Concurrent request results:")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Average response time: {avg_response_time:.3f}s")
        print(f"   Max response time: {max_response_time:.3f}s")
        
        assert success_rate >= 0.8  # At least 80% success rate
        assert avg_response_time < 5.0  # Average response under 5 seconds
        assert max_response_time < 15.0  # No request takes more than 15 seconds
    
    @performance_test
    def test_rapid_sequential_requests(self, server_checker):
        """Test rapid sequential requests"""
        if not server_checker.is_server_running():
            pytest.skip("Server not running")
        
        import requests
        
        num_requests = 50
        response_times = []
        success_count = 0
        
        for i in range(num_requests):
            try:
                start_time = time.time()
                response = requests.get(f"{self.BASE_URL}/health", timeout=10)
                end_time = time.time()
                
                response_times.append(end_time - start_time)
                if response.status_code == 200:
                    success_count += 1
                    
            except Exception as e:
                response_times.append(10.0)  # Timeout value
                print(f"Request {i} failed: {e}")
        
        success_rate = success_count / num_requests
        avg_response_time = statistics.mean(response_times)
        
        print(f"📊 Rapid sequential request results:")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Average response time: {avg_response_time:.3f}s")
        
        assert success_rate >= 0.9  # At least 90% success rate
        assert avg_response_time < 2.0  # Fast response times
    
    @performance_test
    def test_memory_leak_detection(self, server_checker):
        """Test for memory leaks during repeated operations"""
        if not server_checker.is_server_running():
            pytest.skip("Server not running")
        
        import requests
        
        memory_monitor = MemoryMonitor()
        memory_monitor.start()
        
        # Perform many requests to detect memory leaks
        num_iterations = 100
        memory_samples = []
        
        for i in range(num_iterations):
            try:
                response = requests.post(
                    f"{self.BASE_URL}/search",
                    json={"query": f"테스트 쿼리 {i}", "top_k": 5},
                    timeout=10
                )
                
                if i % 10 == 0:  # Sample memory every 10 requests
                    memory_monitor.update_peak()
                    stats = memory_monitor.get_stats()
                    memory_samples.append(stats["current_mb"])
                    
            except Exception as e:
                print(f"Request {i} failed: {e}")
        
        # Analyze memory trend
        if len(memory_samples) >= 3:
            # Check if memory is consistently increasing
            trend = statistics.linear_regression(range(len(memory_samples)), memory_samples)
            
            print(f"📊 Memory leak detection:")
            print(f"   Initial memory: {memory_samples[0]:.2f}MB")
            print(f"   Final memory: {memory_samples[-1]:.2f}MB")
            print(f"   Memory trend slope: {trend.slope:.4f}MB per sample")
            
            # Memory should not increase significantly
            assert trend.slope < 1.0, f"Potential memory leak detected: {trend.slope:.4f}MB per sample"
    
    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self, server_checker):
        """Test async concurrent requests"""
        if not server_checker.is_server_running():
            pytest.skip("Server not running")
        
        async def make_async_request(session, query):
            try:
                start_time = time.time()
                async with session.post(
                    f"{self.BASE_URL}/search",
                    json={"query": query, "top_k": 3},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    return {
                        "status": response.status,
                        "response_time": end_time - start_time,
                        "success": response.status == 200
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "response_time": 30.0,
                    "success": False,
                    "error": str(e)
                }
        
        queries = MockDataFactory.create_search_queries()
        num_concurrent = 20
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_concurrent):
                query = queries[i % len(queries)]
                task = make_async_request(session, query)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
        
        # Analyze results
        success_count = sum(1 for r in results if r["success"])
        response_times = [r["response_time"] for r in results]
        
        success_rate = success_count / num_concurrent
        avg_response_time = statistics.mean(response_times)
        
        print(f"📊 Async concurrent request results:")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Average response time: {avg_response_time:.3f}s")
        
        assert success_rate >= 0.8
        assert avg_response_time < 10.0
    
    def test_large_dataset_simulation(self):
        """Test with simulated large dataset"""
        from data_loader import DataLoader
        from retrievers import FAISSRetriever
        
        # Create large mock dataset
        large_dataset = MockDataFactory.create_legal_documents(count=10000)
        
        memory_monitor = MemoryMonitor()
        memory_monitor.start()
        
        # Test data loading
        loader = DataLoader()
        
        with patch('data_loader.datasets.load_dataset') as mock_load:
            mock_dataset = type('MockDataset', (), {
                '__iter__': lambda self: iter(large_dataset)
            })()
            mock_load.return_value = mock_dataset
            
            with UtilTimer("Large dataset loading"):
                result = loader.load_data()
            
            assert result is True
            
            sentences, sources, documents = loader.get_data()
            assert len(sentences) == 10000
        
        memory_stats = memory_monitor.get_stats()
        print(f"📊 Large dataset simulation:")
        print(f"   Documents loaded: {len(large_dataset)}")
        print(f"   Memory usage: {memory_stats['increase_mb']:.2f}MB")
        
        # Memory usage should be reasonable
        assert memory_stats['increase_mb'] < 500  # Less than 500MB for 10k docs
    
    def test_search_performance_degradation(self):
        """Test search performance with increasing dataset size"""
        from retrievers import TFIDFRetriever
        
        dataset_sizes = [100, 500, 1000, 5000]
        response_times = []
        
        for size in dataset_sizes:
            documents = MockDataFactory.create_legal_documents(count=size)
            sentences = [doc["content"] for doc in documents]
            sources = [doc["source"] for doc in documents]
            
            retriever = TFIDFRetriever(sentences, sources, documents)
            retriever.initialize()
            
            # Measure search time
            with UtilTimer(f"Search with {size} documents") as timer:
                results = retriever.search("계약 해지", top_k=10)
            
            response_times.append(timer.duration)
            print(f"Dataset size: {size}, Search time: {timer.duration:.3f}s")
        
        # Performance should degrade gracefully
        # Search time should not increase exponentially
        for i in range(1, len(response_times)):
            ratio = response_times[i] / response_times[i-1]
            size_ratio = dataset_sizes[i] / dataset_sizes[i-1]
            
            # Search time should not increase more than dataset size ratio
            assert ratio < size_ratio * 2, f"Search performance degraded too much: {ratio:.2f}x"


class TestResourceLimits:
    """Test resource limits and constraints"""
    
    def test_maximum_query_length(self):
        """Test handling of maximum query length"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Test with extremely long query
        long_query = "a" * 10000  # 10KB query
        
        with patch('main.data_loader') as mock_loader:
            mock_loader.is_loaded = True
            
            response = client.post("/search", json={"query": long_query})
            
            # Should either process or reject gracefully
            assert response.status_code in [200, 422, 413]
    
    def test_maximum_top_k_value(self):
        """Test handling of maximum top_k value"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        with patch('main.data_loader') as mock_loader:
            mock_loader.is_loaded = True
            
            # Test with maximum allowed top_k
            response = client.post("/search", json={
                "query": "test",
                "top_k": 1000  # Large value
            })
            
            # Should either process or validate limits
            assert response.status_code in [200, 422]
    
    def test_disk_space_handling(self):
        """Test handling when disk space is low"""
        from cache_manager import CacheManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Mock disk full error
            with patch('pickle.dump') as mock_dump:
                mock_dump.side_effect = OSError("No space left on device")
                
                result = cache_manager.save_cache(["test"], "test_cache", "pkl")
                assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=html", "-m", "not slow"])
