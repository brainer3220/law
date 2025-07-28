"""
End-to-end integration tests for Legal RAG API
"""
import pytest
import requests
import time
import json
from typing import Dict, List, Any
import tempfile
import shutil
from pathlib import Path


class TestE2EIntegration:
    """End-to-end integration tests"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture(scope="class")
    def ensure_server_running(self):
        """Ensure server is running before tests"""
        max_retries = 30
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{self.BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data_loaded"):
                        print(f"✅ Server is ready (attempt {attempt + 1})")
                        return True
                    else:
                        print(f"⏳ Server running but data not loaded (attempt {attempt + 1})")
                else:
                    print(f"⚠️ Server responded with status {response.status_code} (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                print(f"🔄 Waiting for server... (attempt {attempt + 1})")
            except Exception as e:
                print(f"❌ Unexpected error: {e} (attempt {attempt + 1})")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        pytest.fail("Server is not running or not ready. Please start the server first.")
    
    def test_complete_workflow(self, ensure_server_running):
        """Test complete workflow from query to response"""
        # 1. Check server health
        health_response = requests.get(f"{self.BASE_URL}/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert health_data["data_loaded"] is True
        
        # 2. Get statistics
        stats_response = requests.get(f"{self.BASE_URL}/stats")
        assert stats_response.status_code == 200
        
        stats_data = stats_response.json()
        assert stats_data["total_sentences"] > 0
        assert stats_data["total_documents"] > 0
        
        # 3. Perform search
        search_payload = {
            "query": "계약 해지에 관한 판례",
            "method": "faiss",
            "top_k": 5,
            "min_score": 0.1
        }
        
        search_response = requests.post(f"{self.BASE_URL}/search", json=search_payload)
        assert search_response.status_code == 200
        
        search_data = search_response.json()
        assert search_data["query"] == search_payload["query"]
        assert search_data["method_used"] == "faiss"
        assert "execution_time_ms" in search_data
        assert "faiss_results" in search_data
        
        # 4. Validate search results structure
        if search_data["faiss_results"]:
            result = search_data["faiss_results"][0]
            required_fields = ["sentence", "source", "score", "document", "rank"]
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            assert isinstance(result["score"], (int, float))
            assert 0 <= result["score"] <= 1
            assert isinstance(result["rank"], int)
            assert result["rank"] >= 1
    
    def test_multiple_search_methods(self, ensure_server_running):
        """Test all search methods work correctly"""
        query = "민사소송 절차"
        methods = ["tfidf", "embedding", "faiss", "both"]
        
        results = {}
        
        for method in methods:
            payload = {
                "query": query,
                "method": method,
                "top_k": 3,
                "min_score": 0.0
            }
            
            response = requests.post(f"{self.BASE_URL}/search", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                results[method] = {
                    "success": True,
                    "total_results": data["total_results"],
                    "execution_time": data["execution_time_ms"],
                    "has_results": any([
                        data.get("tfidf_results"),
                        data.get("embedding_results"), 
                        data.get("faiss_results")
                    ])
                }
            else:
                results[method] = {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
        
        # Print results for debugging
        print("\\nSearch method results:")
        for method, result in results.items():
            if result["success"]:
                print(f"  {method}: ✅ {result['total_results']} results in {result['execution_time']:.2f}ms")
            else:
                print(f"  {method}: ❌ Failed - {result.get('error', result.get('status_code'))}")
        
        # At least some methods should work
        successful_methods = [m for m, r in results.items() if r.get("success")]
        assert len(successful_methods) > 0, "No search methods are working"
        
        # If 'both' method works, it should return results from multiple methods
        if results.get("both", {}).get("success"):
            both_payload = {"query": query, "method": "both", "top_k": 3}
            both_response = requests.post(f"{self.BASE_URL}/search", json=both_payload)
            both_data = both_response.json()
            
            method_results = [
                both_data.get("tfidf_results"),
                both_data.get("embedding_results"),
                both_data.get("faiss_results")
            ]
            non_empty_results = [r for r in method_results if r]
            assert len(non_empty_results) >= 1, "'both' method should return results from at least one method"
    
    def test_error_handling_e2e(self, ensure_server_running):
        """Test end-to-end error handling"""
        # Test invalid query
        invalid_payloads = [
            {"query": "", "method": "faiss"},  # Empty query
            {"query": "test", "method": "invalid"},  # Invalid method
            {"query": "test", "top_k": 0},  # Invalid top_k
            {"query": "test", "top_k": 1000},  # Too large top_k
            {"query": "test", "min_score": -0.1},  # Invalid min_score
            {"query": "test", "min_score": 1.5},  # Invalid min_score
        ]
        
        for payload in invalid_payloads:
            response = requests.post(f"{self.BASE_URL}/search", json=payload)
            assert response.status_code == 422, f"Expected 422 for payload: {payload}"
        
        # Test malformed JSON
        response = requests.post(
            f"{self.BASE_URL}/search",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test missing content-type
        response = requests.post(f"{self.BASE_URL}/search", data='{"query": "test"}')
        # Should still work or give a specific error
        assert response.status_code in [200, 422, 415]
    
    def test_cache_operations_e2e(self, ensure_server_running):
        """Test cache operations end-to-end"""
        # Get initial cache info
        health_response = requests.get(f"{self.BASE_URL}/health")
        initial_cache = health_response.json().get("cache_info", {})
        
        # Clear cache
        clear_response = requests.delete(f"{self.BASE_URL}/cache")
        assert clear_response.status_code == 200
        
        clear_data = clear_response.json()
        assert "message" in clear_data
        assert "cache" in clear_data["message"].lower()
        
        # Perform a search to regenerate some cache
        search_payload = {"query": "계약 해지", "method": "faiss", "top_k": 3}
        search_response = requests.post(f"{self.BASE_URL}/search", json=search_payload)
        assert search_response.status_code == 200
        
        # Check that cache info is updated
        health_response2 = requests.get(f"{self.BASE_URL}/health")
        final_cache = health_response2.json().get("cache_info", {})
        
        # Cache should be enabled
        assert final_cache.get("cache_enabled") is True
    
    def test_data_reload_e2e(self, ensure_server_running):
        """Test data reload functionality"""
        # Get initial stats
        initial_stats = requests.get(f"{self.BASE_URL}/stats")
        initial_data = initial_stats.json()
        initial_sentences = initial_data["total_sentences"]
        
        # Reload data
        reload_response = requests.post(f"{self.BASE_URL}/reload")
        
        if reload_response.status_code == 200:
            reload_data = reload_response.json()
            assert "message" in reload_data
            assert "total_sentences" in reload_data
            assert "execution_time_ms" in reload_data
            
            # Data should still be loaded after reload
            final_stats = requests.get(f"{self.BASE_URL}/stats")
            final_data = final_stats.json()
            
            # Should have same or similar number of sentences
            assert final_data["total_sentences"] > 0
            print(f"Data reload: {initial_sentences} -> {final_data['total_sentences']} sentences")
        else:
            # Reload might not be implemented or might fail
            assert reload_response.status_code in [501, 500, 404]
            print(f"Data reload not available: {reload_response.status_code}")
    
    def test_search_quality_e2e(self, ensure_server_running):
        """Test search result quality"""
        test_cases = [
            {
                "query": "계약 해지",
                "expected_keywords": ["계약", "해지", "해제", "파기"],
                "method": "faiss"
            },
            {
                "query": "민사소송",
                "expected_keywords": ["민사", "소송", "법원", "판결"],
                "method": "embedding"
            },
            {
                "query": "손해배상",
                "expected_keywords": ["손해", "배상", "책임", "피해"],
                "method": "tfidf"
            }
        ]
        
        for test_case in test_cases:
            payload = {
                "query": test_case["query"],
                "method": test_case["method"],
                "top_k": 5,
                "min_score": 0.1
            }
            
            response = requests.post(f"{self.BASE_URL}/search", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Get results based on method
                results_key = f"{test_case['method']}_results"
                if test_case["method"] == "both":
                    # For 'both', check any available results
                    results = (data.get("faiss_results", []) + 
                             data.get("embedding_results", []) + 
                             data.get("tfidf_results", []))
                else:
                    results = data.get(results_key, [])
                
                if results:
                    # Check if results contain relevant keywords
                    all_text = " ".join([r["sentence"].lower() for r in results[:3]])
                    
                    keyword_matches = sum(1 for keyword in test_case["expected_keywords"] 
                                        if keyword in all_text)
                    
                    print(f"Query '{test_case['query']}' ({test_case['method']}): "
                          f"{keyword_matches}/{len(test_case['expected_keywords'])} keywords found")
                    
                    # At least one keyword should be found in top results
                    assert keyword_matches > 0, f"No relevant keywords found for '{test_case['query']}'"
                else:
                    print(f"No results returned for '{test_case['query']}' with {test_case['method']}")
            else:
                print(f"Search failed for '{test_case['query']}': {response.status_code}")
    
    def test_response_consistency_e2e(self, ensure_server_running):
        """Test response consistency across multiple requests"""
        query = "부동산 매매계약"
        method = "faiss"
        
        responses = []
        for i in range(5):
            payload = {"query": query, "method": method, "top_k": 5}
            response = requests.post(f"{self.BASE_URL}/search", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                responses.append(data)
            
            time.sleep(0.1)  # Small delay between requests
        
        if len(responses) >= 2:
            # Check consistency
            first_response = responses[0]
            
            for i, response in enumerate(responses[1:], 1):
                # Results should be identical for the same query
                assert response["query"] == first_response["query"]
                assert response["method_used"] == first_response["method_used"]
                assert response["total_results"] == first_response["total_results"]
                
                # Result content should be the same
                if first_response.get(f"{method}_results") and response.get(f"{method}_results"):
                    first_results = first_response[f"{method}_results"]
                    current_results = response[f"{method}_results"]
                    
                    assert len(first_results) == len(current_results)
                    
                    for j, (first_result, current_result) in enumerate(zip(first_results, current_results)):
                        assert first_result["sentence"] == current_result["sentence"]
                        assert first_result["source"] == current_result["source"]
                        assert abs(first_result["score"] - current_result["score"]) < 0.001
                        assert first_result["rank"] == current_result["rank"]
            
            print(f"✅ Response consistency verified across {len(responses)} requests")
        else:
            print("⚠️ Not enough successful responses to test consistency")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
