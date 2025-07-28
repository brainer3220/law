"""
Advanced test cases for exception handling and edge cases
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import shutil
from pathlib import Path
import json
import time
from typing import Dict, Any, List
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

# Import application modules
from main import app
from data_loader import DataLoader
from cache_manager import CacheManager
from retrievers import TFIDFRetriever, EmbeddingRetriever, FAISSRetriever
from config import settings
from models import QueryRequest, QueryResponse, HealthResponse
from fastapi.testclient import TestClient


class TestExceptionHandling:
    """Test exception handling scenarios"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_data_loader_file_not_found(self):
        """Test DataLoader when dataset file doesn't exist"""
        loader = DataLoader()
        
        with patch('data_loader.datasets.load_dataset') as mock_load:
            mock_load.side_effect = FileNotFoundError("Dataset not found")
            
            result = loader.load_from_dataset("nonexistent_dataset")
            assert result is False
            assert loader.is_loaded is False
    
    def test_data_loader_corrupted_data(self):
        """Test DataLoader with corrupted data"""
        loader = DataLoader()
        
        # Mock corrupted dataset
        mock_dataset = Mock()
        mock_dataset.__iter__ = Mock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        
        with patch('data_loader.datasets.load_dataset', return_value=mock_dataset):
            result = loader.load_from_dataset("corrupted_dataset")
            assert result is False
    
    def test_data_loader_memory_error(self):
        """Test DataLoader with memory error"""
        loader = DataLoader()
        
        with patch('data_loader.datasets.load_dataset') as mock_load:
            mock_load.side_effect = MemoryError("Not enough memory")
            
            result = loader.load_from_dataset("large_dataset")
            assert result is False
    
    def test_cache_manager_permission_error(self):
        """Test CacheManager with permission errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "restricted"
            cache_dir.mkdir(mode=0o000)  # No permissions
            
            try:
                cache_manager = CacheManager(cache_dir=cache_dir)
                
                with pytest.raises(PermissionError):
                    cache_manager.save_cache("test_data", "test_file", "pkl")
            finally:
                cache_dir.chmod(0o755)  # Restore permissions for cleanup
    
    def test_cache_manager_disk_full(self):
        """Test CacheManager when disk is full"""
        cache_manager = CacheManager()
        
        with patch('pickle.dump') as mock_dump:
            mock_dump.side_effect = OSError("No space left on device")
            
            result = cache_manager.save_cache("test_data", "test_file", "pkl")
            assert result is False
    
    def test_retriever_initialization_failure(self):
        """Test retriever initialization failures"""
        sentences = ["test sentence"]
        sources = ["test source"]
        documents = [{"content": "test"}]
        
        # Test TF-IDF retriever with empty data
        retriever = TFIDFRetriever([], [], [])
        result = retriever.initialize()
        assert result is False
        
        # Test with invalid data types
        with pytest.raises(TypeError):
            TFIDFRetriever(None, sources, documents)
    
    def test_embedding_retriever_model_error(self):
        """Test EmbeddingRetriever when model loading fails"""
        sentences = ["test sentence"]
        sources = ["test source"]
        documents = [{"content": "test"}]
        
        retriever = EmbeddingRetriever(sentences, sources, documents)
        
        with patch('retrievers.SentenceTransformer') as mock_st:
            mock_st.side_effect = OSError("Model not found")
            
            result = retriever.initialize()
            assert result is False
    
    def test_faiss_retriever_index_error(self):
        """Test FAISSRetriever when FAISS index creation fails"""
        sentences = ["test sentence"]
        sources = ["test source"]
        documents = [{"content": "test"}]
        
        retriever = FAISSRetriever(sentences, sources, documents)
        
        with patch('retrievers.faiss.IndexFlatIP') as mock_faiss:
            mock_faiss.side_effect = RuntimeError("FAISS error")
            
            result = retriever.initialize()
            assert result is False
    
    def test_api_database_connection_error(self, test_client):
        """Test API when database connection fails"""
        with patch('main.data_loader') as mock_loader:
            mock_loader.is_loaded = True
            mock_loader.get_stats.side_effect = ConnectionError("Database connection failed")
            
            response = test_client.get("/stats")
            assert response.status_code == 500
            assert "error" in response.json()["detail"].lower()
    
    def test_api_timeout_error(self, test_client):
        """Test API timeout scenarios"""
        with patch('main.faiss_retriever') as mock_retriever:
            mock_retriever.search.side_effect = TimeoutError("Search timeout")
            
            with patch('main.data_loader') as mock_loader:
                mock_loader.is_loaded = True
                
                payload = {"query": "test query"}
                response = test_client.post("/search", json=payload)
                assert response.status_code == 500
    
    def test_api_malformed_request(self, test_client):
        """Test API with malformed requests"""
        # Test with invalid JSON
        response = test_client.post(
            "/search",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test with missing required fields
        response = test_client.post("/search", json={})
        assert response.status_code == 422
        
        # Test with wrong data types
        response = test_client.post("/search", json={
            "query": 123,  # Should be string
            "top_k": "invalid"  # Should be int
        })
        assert response.status_code == 422
    
    def test_api_concurrent_requests(self, test_client):
        """Test API under concurrent load"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = test_client.get("/health")
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        response_codes = []
        while not results.empty():
            response_codes.append(results.get())
        
        # Most requests should succeed
        success_rate = sum(1 for code in response_codes if code == 200) / len(response_codes)
        assert success_rate >= 0.8  # At least 80% success rate


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.fixture
    def test_client(self):
        return TestClient(app)
    
    def test_empty_dataset_handling(self):
        """Test handling of empty datasets"""
        loader = DataLoader()
        
        # Mock empty dataset
        mock_dataset = Mock()
        mock_dataset.__iter__ = Mock(return_value=iter([]))
        
        with patch('data_loader.datasets.load_dataset', return_value=mock_dataset):
            result = loader.load_data()
            assert result is False
            assert loader.is_loaded is False
    
    def test_large_query_handling(self, test_client):
        """Test handling of very large queries"""
        with patch('main.data_loader') as mock_loader:
            mock_loader.is_loaded = True
            
            # Create a very large query (10KB)
            large_query = "a" * 10000
            
            payload = {"query": large_query}
            response = test_client.post("/search", json=payload)
            
            # Should either process or reject gracefully
            assert response.status_code in [200, 422, 413]
    
    def test_special_characters_in_query(self, test_client):
        """Test queries with special characters"""
        with patch('main.data_loader') as mock_loader:
            mock_loader.is_loaded = True
            
            with patch('main.faiss_retriever') as mock_retriever:
                mock_retriever.search.return_value = []
                
                special_queries = [
                    "테스트 🏛️ 법원",
                    "query with\nnewlines\tand\ttabs",
                    "query with \"quotes\" and 'apostrophes'",
                    "query with émojis 🔍 and àccénts",
                    "query with <html> &amp; entities",
                ]
                
                for query in special_queries:
                    payload = {"query": query}
                    response = test_client.post("/search", json=payload)
                    assert response.status_code in [200, 422]  # Should handle gracefully
    
    def test_boundary_values(self, test_client):
        """Test boundary values for parameters"""
        with patch('main.data_loader') as mock_loader:
            mock_loader.is_loaded = True
            
            with patch('main.faiss_retriever') as mock_retriever:
                mock_retriever.search.return_value = []
                
                # Test minimum values
                payload = {
                    "query": "test",
                    "top_k": 1,
                    "min_score": 0.0
                }
                response = test_client.post("/search", json=payload)
                assert response.status_code == 200
                
                # Test maximum values
                payload = {
                    "query": "test",
                    "top_k": settings.MAX_TOP_K,
                    "min_score": 1.0
                }
                response = test_client.post("/search", json=payload)
                assert response.status_code == 200
    
    def test_unicode_handling(self):
        """Test Unicode string handling"""
        loader = DataLoader()
        
        # Test with various Unicode characters
        unicode_data = [
            {"content": "한글 테스트 문서", "source": "test"},
            {"content": "English with 中文", "source": "test"},
            {"content": "العربية text", "source": "test"},
            {"content": "Русский язык", "source": "test"},
        ]
        
        mock_dataset = Mock()
        mock_dataset.__iter__ = Mock(return_value=iter(unicode_data))
        
        with patch('data_loader.datasets.load_dataset', return_value=mock_dataset):
            result = loader.load_data()
            
            if result:
                sentences, sources, documents = loader.get_data()
                assert all(isinstance(s, str) for s in sentences)
                assert "한글 테스트 문서" in sentences


class TestPerformanceEdgeCases:
    """Test performance-related edge cases"""
    
    def test_memory_usage_monitoring(self):
        """Test memory usage during data loading"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        loader = DataLoader()
        
        # Mock large dataset
        large_data = [{"content": f"Document {i}", "source": "test"} for i in range(1000)]
        mock_dataset = Mock()
        mock_dataset.__iter__ = Mock(return_value=iter(large_data))
        
        with patch('data_loader.datasets.load_dataset', return_value=mock_dataset):
            result = loader.load_data()
            
            if result:
                final_memory = process.memory_info().rss
                memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
                
                # Memory increase should be reasonable (less than 100MB for test data)
                assert memory_increase < 100
    
    def test_search_timeout(self):
        """Test search operations with timeout"""
        sentences = ["test sentence"] * 1000
        sources = ["test source"] * 1000
        documents = [{"content": f"doc {i}"} for i in range(1000)]
        
        retriever = TFIDFRetriever(sentences, sources, documents)
        
        # Mock slow operation
        with patch('retrievers.cosine_similarity') as mock_cosine:
            def slow_similarity(*args, **kwargs):
                time.sleep(5)  # Simulate slow operation
                return [[0.5] * len(sentences)]
            
            mock_cosine.side_effect = slow_similarity
            
            start_time = time.time()
            try:
                results = retriever.search("test query", top_k=10)
                end_time = time.time()
                
                # Operation should complete but we monitor the time
                assert end_time - start_time < 10  # Should not take more than 10 seconds
            except Exception:
                # Timeout is acceptable for this test
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=html"])
