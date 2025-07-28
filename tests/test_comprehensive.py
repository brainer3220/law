"""
Comprehensive test suite for Legal RAG API
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from pathlib import Path
import json
import time
from typing import Dict, Any, List

# Import application modules
from main import app, initialize_retrievers
from data_loader import DataLoader
from cache_manager import CacheManager
from retrievers import TFIDFRetriever, EmbeddingRetriever, FAISSRetriever
from config import settings
from models import QueryRequest, QueryResponse, HealthResponse


class TestConfig:
    """Test configuration"""
    TEST_QUERIES = [
        "계약 해지에 관한 판례를 알려줘",
        "민사소송 절차는 어떻게 되나요?",
        "손해배상 책임에 대해 설명해주세요",
        "부동산 매매계약의 효력",
        "소멸시효 완성의 효과"
    ]
    
    SAMPLE_DOCUMENTS = [
        {
            "content": "민사소송은 개인 간의 분쟁을 해결하는 법적 절차입니다.",
            "source": "court_decisions",
            "metadata": {"case_id": "2023가합12345"}
        },
        {
            "content": "계약의 해지는 당사자 일방의 의사표시로 이루어집니다.",
            "source": "statutes", 
            "metadata": {"law_name": "민법"}
        },
        {
            "content": "손해배상책임은 고의 또는 과실로 인한 위법행위를 요건으로 합니다.",
            "source": "legal_interpretations",
            "metadata": {"interpretation_id": "법제처-2023-001"}
        }
    ]


@pytest.fixture
def test_client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_data_loader():
    """Mock data loader with sample data"""
    mock_loader = Mock(spec=DataLoader)
    mock_loader.is_loaded = True
    mock_loader.get_data.return_value = (
        [doc["content"] for doc in TestConfig.SAMPLE_DOCUMENTS],
        [doc["source"] for doc in TestConfig.SAMPLE_DOCUMENTS],
        TestConfig.SAMPLE_DOCUMENTS
    )
    mock_loader.get_stats.return_value = {
        "total_sentences": len(TestConfig.SAMPLE_DOCUMENTS),
        "total_documents": len(TestConfig.SAMPLE_DOCUMENTS),
        "document_type_counts": {"court_decisions": 1, "statutes": 1, "legal_interpretations": 1}
    }
    return mock_loader


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager"""
    mock_cache = Mock(spec=CacheManager)
    mock_cache.get_cache_info.return_value = {
        "cache_enabled": True,
        "total_files": 3,
        "total_cache_size_mb": 10.5
    }
    return mock_cache


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


class TestModels:
    """Test Pydantic models"""
    
    def test_query_request_valid(self):
        """Test valid QueryRequest"""
        request = QueryRequest(
            query="test query",
            method="faiss",
            top_k=5,
            min_score=0.1
        )
        assert request.query == "test query"
        assert request.method == "faiss"
        assert request.top_k == 5
        assert request.min_score == 0.1
    
    def test_query_request_defaults(self):
        """Test QueryRequest with defaults"""
        request = QueryRequest(query="test")
        assert request.method == "faiss"
        assert request.top_k == settings.DEFAULT_TOP_K
        assert request.min_score == settings.MIN_SIMILARITY_SCORE
    
    def test_query_request_validation(self):
        """Test QueryRequest validation"""
        # Empty query
        with pytest.raises(ValueError):
            QueryRequest(query="")
        
        # Invalid method
        with pytest.raises(ValueError):
            QueryRequest(query="test", method="invalid")
        
        # Invalid top_k
        with pytest.raises(ValueError):
            QueryRequest(query="test", top_k=0)
        
        with pytest.raises(ValueError):
            QueryRequest(query="test", top_k=settings.MAX_TOP_K + 1)
        
        # Invalid min_score
        with pytest.raises(ValueError):
            QueryRequest(query="test", min_score=-0.1)
        
        with pytest.raises(ValueError):
            QueryRequest(query="test", min_score=1.1)
    
    def test_query_response_structure(self):
        """Test QueryResponse structure"""
        response = QueryResponse(
            query="test",
            method_used="faiss",
            total_results=5,
            execution_time_ms=150.5,
            faiss_results=[]
        )
        assert response.query == "test"
        assert response.method_used == "faiss"
        assert response.total_results == 5
        assert response.execution_time_ms == 150.5


class TestDataLoader:
    """Test DataLoader functionality"""
    
    @patch('data_loader.datasets.load_dataset')
    def test_load_from_dataset(self, mock_load_dataset):
        """Test loading from dataset"""
        # Mock dataset response
        mock_dataset = Mock()
        mock_dataset.__iter__ = Mock(return_value=iter([
            {"content": "test content 1", "source": "test_source"},
            {"content": "test content 2", "source": "test_source"}
        ]))
        mock_load_dataset.return_value = mock_dataset
        
        loader = DataLoader()
        success = loader.load_from_dataset("test_dataset")
        
        assert success is True
        assert loader.is_loaded is True
        sentences, sources, documents = loader.get_data()
        assert len(sentences) == 2
        assert sentences[0] == "test content 1"
    
    def test_get_stats(self):
        """Test statistics generation"""
        loader = DataLoader()
        loader.sentences = ["sentence1", "sentence2"]
        loader.sources = ["source1", "source2"] 
        loader.documents = [{"source": "source1"}, {"source": "source2"}]
        loader.is_loaded = True
        
        stats = loader.get_stats()
        assert stats["total_sentences"] == 2
        assert stats["total_documents"] == 2


class TestCacheManager:
    """Test CacheManager functionality"""
    
    def test_cache_manager_init(self, temp_cache_dir):
        """Test cache manager initialization"""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        assert cache_manager.cache_dir == temp_cache_dir
        assert cache_manager.cache_enabled is True
    
    def test_get_cache_path(self, temp_cache_dir):
        """Test cache path generation"""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        cache_path = cache_manager.get_cache_path("test_data", "pkl")
        expected = temp_cache_dir / "test_data.pkl"
        assert cache_path == expected
    
    def test_cache_exists(self, temp_cache_dir):
        """Test cache existence check"""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        # Create a test cache file
        test_file = temp_cache_dir / "test.pkl"
        test_file.touch()
        
        assert cache_manager.cache_exists("test", "pkl") is True
        assert cache_manager.cache_exists("nonexistent", "pkl") is False
    
    def test_clear_cache(self, temp_cache_dir):
        """Test cache clearing"""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        # Create test files
        (temp_cache_dir / "file1.pkl").touch()
        (temp_cache_dir / "file2.index").touch()
        
        result = cache_manager.clear_cache()
        assert result["deleted_files_count"] == 2
        assert len(list(temp_cache_dir.iterdir())) == 0


class TestRetrievers:
    """Test retrieval methods"""
    
    def test_tfidf_retriever_initialization(self, mock_data_loader):
        """Test TF-IDF retriever initialization"""
        sentences, sources, documents = mock_data_loader.get_data()
        retriever = TFIDFRetriever(sentences, sources, documents)
        
        assert retriever.sentences == sentences
        assert retriever.sources == sources
        assert retriever.documents == documents
    
    @patch('retrievers.TfidfVectorizer')
    def test_tfidf_retriever_search(self, mock_vectorizer, mock_data_loader):
        """Test TF-IDF retriever search"""
        # Mock vectorizer
        mock_vectorizer_instance = Mock()
        mock_vectorizer.return_value = mock_vectorizer_instance
        mock_vectorizer_instance.fit_transform.return_value = Mock()
        mock_vectorizer_instance.transform.return_value = Mock()
        
        sentences, sources, documents = mock_data_loader.get_data()
        retriever = TFIDFRetriever(sentences, sources, documents)
        
        # Mock cosine similarity to return predictable results
        with patch('retrievers.cosine_similarity') as mock_cosine:
            mock_cosine.return_value = [[0.8, 0.6, 0.4]]
            
            results = retriever.search("test query", top_k=2, min_score=0.5)
            
            assert len(results) == 2  # Only scores >= 0.5
            assert results[0]["score"] == 0.8
            assert results[1]["score"] == 0.6


class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
    
    @patch('main.data_loader')
    @patch('main.cache_manager')
    def test_health_endpoint(self, mock_cache, mock_loader, test_client):
        """Test health endpoint"""
        # Mock successful state
        mock_loader.is_loaded = True
        mock_loader.get_stats.return_value = {
            "total_sentences": 100,
            "total_documents": 50
        }
        mock_cache.get_cache_info.return_value = {
            "cache_enabled": True,
            "total_files": 5
        }
        
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["data_loaded"] is True
        assert data["total_sentences"] == 100
    
    @patch('main.data_loader')
    def test_stats_endpoint(self, mock_loader, test_client):
        """Test statistics endpoint"""
        mock_loader.is_loaded = True
        mock_loader.get_stats.return_value = {
            "total_sentences": 100,
            "total_documents": 50,
            "document_type_counts": {"type1": 30, "type2": 20}
        }
        
        response = test_client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sentences"] == 100
        assert data["total_documents"] == 50
        assert "document_type_counts" in data
    
    @patch('main.faiss_retriever')
    @patch('main.data_loader')
    def test_search_endpoint_faiss(self, mock_loader, mock_retriever, test_client):
        """Test search endpoint with FAISS"""
        mock_loader.is_loaded = True
        
        # Mock FAISS retriever
        mock_results = [
            {
                "sentence": "Test result",
                "source": "test_source",
                "score": 0.95,
                "document": {"id": 1},
                "rank": 1
            }
        ]
        mock_retriever.search.return_value = mock_results
        
        payload = {
            "query": "test query",
            "method": "faiss",
            "top_k": 5,
            "min_score": 0.1
        }
        
        response = test_client.post("/search", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test query"
        assert data["method_used"] == "faiss"
        assert len(data["faiss_results"]) == 1
        assert data["faiss_results"][0]["score"] == 0.95
    
    def test_search_endpoint_invalid_payload(self, test_client):
        """Test search endpoint with invalid payload"""
        # Empty query
        response = test_client.post("/search", json={"query": ""})
        assert response.status_code == 422
        
        # Invalid method
        response = test_client.post("/search", json={
            "query": "test",
            "method": "invalid"
        })
        assert response.status_code == 422
        
        # Invalid top_k
        response = test_client.post("/search", json={
            "query": "test",
            "top_k": 0
        })
        assert response.status_code == 422
    
    @patch('main.data_loader')
    def test_search_endpoint_data_not_loaded(self, mock_loader, test_client):
        """Test search endpoint when data is not loaded"""
        mock_loader.is_loaded = False
        
        payload = {"query": "test query"}
        response = test_client.post("/search", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "not loaded" in data["detail"].lower()
    
    @patch('main.cache_manager')
    def test_clear_cache_endpoint(self, mock_cache, test_client):
        """Test clear cache endpoint"""
        mock_cache.clear_cache.return_value = {
            "deleted_files_count": 5,
            "freed_space_mb": 25.5
        }
        
        response = test_client.delete("/cache")
        assert response.status_code == 200
        data = response.json()
        assert "cleared" in data["message"].lower()
        assert data["freed_space_mb"] == 25.5


class TestIntegration:
    """Integration tests"""
    
    def test_full_search_pipeline(self, test_client, mock_data_loader, mock_cache_manager):
        """Test complete search pipeline"""
        with patch('main.data_loader', mock_data_loader), \
             patch('main.cache_manager', mock_cache_manager):
            
            # Mock retrievers
            mock_faiss = Mock()
            mock_faiss.search.return_value = [
                {
                    "sentence": "민사소송은 개인 간의 분쟁을 해결하는 법적 절차입니다.",
                    "source": "court_decisions",
                    "score": 0.95,
                    "document": TestConfig.SAMPLE_DOCUMENTS[0],
                    "rank": 1
                }
            ]
            
            with patch('main.faiss_retriever', mock_faiss):
                payload = {
                    "query": "민사소송 절차",
                    "method": "faiss",
                    "top_k": 5
                }
                
                response = test_client.post("/search", json=payload)
                assert response.status_code == 200
                
                data = response.json()
                assert data["query"] == "민사소송 절차"
                assert data["total_results"] == 1
                assert len(data["faiss_results"]) == 1
                assert data["faiss_results"][0]["score"] == 0.95
    
    def test_performance_under_load(self, test_client):
        """Test API performance under load"""
        # This would typically use async testing
        # For now, we'll simulate multiple requests
        
        responses = []
        for i in range(10):
            response = test_client.get("/health")
            responses.append(response)
            assert response.status_code == 200
        
        # All requests should succeed
        assert len(responses) == 10
        assert all(r.status_code == 200 for r in responses)


class TestErrorHandling:
    """Test error handling"""
    
    def test_server_error_handling(self, test_client):
        """Test server error handling"""
        with patch('main.data_loader') as mock_loader:
            mock_loader.is_loaded = True
            mock_loader.get_stats.side_effect = Exception("Database error")
            
            response = test_client.get("/stats")
            assert response.status_code == 500
    
    def test_validation_error_handling(self, test_client):
        """Test validation error handling"""
        # Invalid JSON
        response = test_client.post("/search", 
                                  data="invalid json",
                                  headers={"Content-Type": "application/json"})
        assert response.status_code == 422


class TestUtilities:
    """Test utility functions"""
    
    def test_query_preprocessing(self):
        """Test query preprocessing"""
        # This would test any query preprocessing functions
        # Currently not implemented in the main code
        pass
    
    def test_result_postprocessing(self):
        """Test result postprocessing"""
        # This would test any result postprocessing functions
        pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
