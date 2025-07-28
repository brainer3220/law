"""
Performance and load testing for Legal RAG API
"""
import pytest
import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from typing import List, Dict, Any
import json


class TestPerformance:
    """Performance testing suite"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def sample_queries(self):
        """Sample queries for testing"""
        return [
            "계약 해지에 관한 판례를 알려줘",
            "민사소송 절차는 어떻게 되나요?", 
            "손해배상 책임에 대해 설명해주세요",
            "부동산 매매계약의 효력",
            "소멸시효 완성의 효과",
            "법정이율의 적용",
            "임대차계약 해지",
            "불법행위 손해배상",
            "계약의 성립 요건",
            "물권법의 기본 원칙"
        ]
    
    def test_single_request_performance(self):
        """Test single request performance"""
        query = "계약 해지 판례"
        payload = {
            "query": query,
            "method": "faiss",
            "top_k": 5,
            "min_score": 0.1
        }
        
        start_time = time.time()
        response = requests.post(f"{self.BASE_URL}/search", json=payload, timeout=30)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time < 5000  # Should respond within 5 seconds
        
        data = response.json()
        assert "execution_time_ms" in data
        print(f"Single request: {response_time:.2f}ms (Server: {data['execution_time_ms']:.2f}ms)")
    
    def test_concurrent_requests(self, sample_queries):
        """Test concurrent request handling"""
        def make_request(query: str) -> Dict[str, Any]:
            payload = {
                "query": query,
                "method": "faiss", 
                "top_k": 5
            }
            start_time = time.time()
            try:
                response = requests.post(f"{self.BASE_URL}/search", json=payload, timeout=30)
                end_time = time.time()
                
                return {
                    "status_code": response.status_code,
                    "response_time": (end_time - start_time) * 1000,
                    "success": response.status_code == 200,
                    "query": query
                }
            except Exception as e:
                return {
                    "status_code": 0,
                    "response_time": 0,
                    "success": False,
                    "error": str(e),
                    "query": query
                }
        
        # Test with 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, query) for query in sample_queries]
            results = [future.result() for future in as_completed(futures)]
        
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        assert len(successful_requests) >= len(sample_queries) * 0.8  # At least 80% success rate
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"Concurrent requests: {len(successful_requests)}/{len(sample_queries)} successful")
            print(f"Response times - Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
            
            assert avg_time < 10000  # Average should be under 10 seconds
            assert max_time < 30000  # Max should be under 30 seconds
        
        if failed_requests:
            print(f"Failed requests: {len(failed_requests)}")
            for req in failed_requests:
                print(f"  {req['query']}: {req.get('error', 'Unknown error')}")
    
    def test_load_testing(self, sample_queries):
        """Test system under sustained load"""
        def burst_requests(queries: List[str], burst_count: int = 3) -> List[Dict]:
            results = []
            for _ in range(burst_count):
                for query in queries[:5]:  # Use first 5 queries
                    payload = {"query": query, "method": "faiss", "top_k": 3}
                    start_time = time.time()
                    try:
                        response = requests.post(f"{self.BASE_URL}/search", json=payload, timeout=15)
                        end_time = time.time()
                        results.append({
                            "success": response.status_code == 200,
                            "response_time": (end_time - start_time) * 1000,
                            "status_code": response.status_code
                        })
                    except Exception as e:
                        results.append({
                            "success": False,
                            "response_time": 0,
                            "error": str(e)
                        })
                time.sleep(0.1)  # Small delay between bursts
            return results
        
        results = burst_requests(sample_queries, burst_count=5)
        
        successful = [r for r in results if r["success"]]
        success_rate = len(successful) / len(results)
        
        assert success_rate >= 0.75  # At least 75% success rate under load
        
        if successful:
            avg_time = statistics.mean([r["response_time"] for r in successful])
            print(f"Load test: {len(successful)}/{len(results)} successful ({success_rate*100:.1f}%)")
            print(f"Average response time: {avg_time:.2f}ms")
    
    def test_memory_usage(self):
        """Test memory usage during operations"""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make multiple requests
        queries = ["계약 해지", "민사소송", "손해배상", "부동산", "소멸시효"] * 5
        
        for query in queries:
            payload = {"query": query, "method": "faiss", "top_k": 5}
            try:
                requests.post(f"{self.BASE_URL}/search", json=payload, timeout=10)
            except:
                pass  # Ignore failures, we're testing memory
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_increase:.1f}MB)")
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100
    
    def test_different_methods_performance(self):
        """Test performance of different retrieval methods"""
        query = "계약 해지 관련 판례"
        methods = ["tfidf", "embedding", "faiss", "both"]
        
        results = {}
        
        for method in methods:
            payload = {
                "query": query,
                "method": method,
                "top_k": 5
            }
            
            start_time = time.time()
            try:
                response = requests.post(f"{self.BASE_URL}/search", json=payload, timeout=30)
                end_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    results[method] = {
                        "response_time": (end_time - start_time) * 1000,
                        "server_time": data.get("execution_time_ms", 0),
                        "total_results": data.get("total_results", 0),
                        "success": True
                    }
                else:
                    results[method] = {"success": False, "status_code": response.status_code}
                    
            except Exception as e:
                results[method] = {"success": False, "error": str(e)}
        
        # Print results
        print("Method performance comparison:")
        for method, result in results.items():
            if result.get("success"):
                print(f"  {method}: {result['response_time']:.2f}ms (server: {result['server_time']:.2f}ms)")
            else:
                print(f"  {method}: FAILED - {result.get('error', result.get('status_code'))}")
        
        # At least one method should work
        successful_methods = [m for m, r in results.items() if r.get("success")]
        assert len(successful_methods) > 0
    
    def test_large_query_handling(self):
        """Test handling of large queries"""
        # Test different query sizes
        base_query = "계약 해지에 관한 판례를 알려주세요. "
        
        query_sizes = [
            (10, base_query * 10),    # ~300 characters
            (50, base_query * 50),    # ~1500 characters  
            (100, base_query * 100),  # ~3000 characters
        ]
        
        for size, query in query_sizes:
            payload = {
                "query": query[:1000],  # Truncate to max allowed
                "method": "faiss",
                "top_k": 3
            }
            
            start_time = time.time()
            response = requests.post(f"{self.BASE_URL}/search", json=payload, timeout=30)
            response_time = (time.time() - start_time) * 1000
            
            print(f"Query size {len(payload['query'])} chars: {response_time:.2f}ms")
            
            if len(payload["query"]) <= 1000:  # Within limits
                assert response.status_code == 200
            # Longer queries should still not crash the server
            assert response.status_code in [200, 422]  # 422 for validation error
    
    def test_api_health_under_load(self):
        """Test if health endpoint remains responsive under load"""
        def check_health():
            try:
                response = requests.get(f"{self.BASE_URL}/health", timeout=5)
                return response.status_code == 200
            except:
                return False
        
        # Generate some load
        def generate_load():
            for i in range(10):
                payload = {"query": f"test query {i}", "method": "faiss", "top_k": 3}
                try:
                    requests.post(f"{self.BASE_URL}/search", json=payload, timeout=10)
                except:
                    pass
        
        # Start load generation in background
        with ThreadPoolExecutor(max_workers=3) as executor:
            load_futures = [executor.submit(generate_load) for _ in range(3)]
            
            # Check health multiple times during load
            health_checks = []
            for _ in range(10):
                health_checks.append(check_health())
                time.sleep(0.5)
            
            # Wait for load to complete
            for future in as_completed(load_futures):
                future.result()
        
        success_rate = sum(health_checks) / len(health_checks)
        print(f"Health endpoint availability under load: {success_rate*100:.1f}%")
        
        # Health endpoint should remain mostly available
        assert success_rate >= 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
