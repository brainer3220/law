"""
Unit tests for individual components
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import tempfile
from pathlib import Path

# Import modules to test
from data_loader import DataLoader
from cache_manager import CacheManager
from retrievers import TFIDFRetriever, EmbeddingRetriever, FAISSRetriever
from models import QueryRequest, QueryResponse, HealthResponse, StatsResponse
from config import settings


class TestDataLoaderUnit:
    """Unit tests for DataLoader class"""
    
    def test_initialization(self):
        """Test DataLoader initialization"""
        loader = DataLoader()
        assert loader.sentences == []
        assert loader.sources == []
        assert loader.documents == []
        assert loader.is_loaded is False
    
    @patch('data_loader.datasets.load_dataset')
    def test_load_from_dataset_success(self, mock_load_dataset):
        """Test successful dataset loading"""
        # Mock dataset
        mock_data = [
            {"content": "Content 1", "source": "source1"},
            {"content": "Content 2", "source": "source2"}
        ]
        mock_dataset = Mock()
        mock_dataset.__iter__ = Mock(return_value=iter(mock_data))
        mock_load_dataset.return_value = mock_dataset
        
        loader = DataLoader()
        result = loader.load_from_dataset("test_dataset")
        
        assert result is True
        assert loader.is_loaded is True
        assert len(loader.sentences) == 2
        assert loader.sentences[0] == "Content 1"
        assert loader.sources[0] == "source1"
    
    @patch('data_loader.datasets.load_dataset')
    def test_load_from_dataset_failure(self, mock_load_dataset):
        """Test dataset loading failure"""
        mock_load_dataset.side_effect = Exception("Loading failed")
        
        loader = DataLoader()
        result = loader.load_from_dataset("test_dataset")
        
        assert result is False
        assert loader.is_loaded is False
    
    def test_get_data_when_loaded(self):
        """Test get_data when data is loaded"""
        loader = DataLoader()
        loader.sentences = ["sentence1", "sentence2"]
        loader.sources = ["source1", "source2"]
        loader.documents = [{"id": 1}, {"id": 2}]
        loader.is_loaded = True
        
        sentences, sources, documents = loader.get_data()
        
        assert sentences == ["sentence1", "sentence2"]
        assert sources == ["source1", "source2"]
        assert documents == [{"id": 1}, {"id": 2}]
    
    def test_get_data_when_not_loaded(self):
        """Test get_data when data is not loaded"""
        loader = DataLoader()
        
        sentences, sources, documents = loader.get_data()
        
        assert sentences == []
        assert sources == []
        assert documents == []
    
    def test_get_stats(self):
        """Test statistics generation"""
        loader = DataLoader()
        loader.sentences = ["s1", "s2", "s3"]
        loader.sources = ["court", "statute", "court"]
        loader.documents = [
            {"source": "court"}, 
            {"source": "statute"}, 
            {"source": "court"}
        ]
        loader.is_loaded = True
        
        stats = loader.get_stats()
        
        assert stats["total_sentences"] == 3
        assert stats["total_documents"] == 3
        assert stats["document_type_counts"]["court"] == 2
        assert stats["document_type_counts"]["statute"] == 1
    
    def test_reload(self):
        """Test data reload functionality"""
        loader = DataLoader()
        loader.sentences = ["old_data"]
        loader.is_loaded = True
        
        with patch.object(loader, 'load_data', return_value=True) as mock_load:
            result = loader.reload()
            
            assert result is True
            mock_load.assert_called_once()


class TestCacheManagerUnit:
    """Unit tests for CacheManager class"""
    
    def test_initialization(self):
        """Test CacheManager initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            assert cache_manager.cache_dir == Path(temp_dir)
            assert cache_manager.cache_enabled is True
    
    def test_get_cache_path(self):
        """Test cache path generation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            cache_path = cache_manager.get_cache_path("test_file", "pkl")
            expected_path = Path(temp_dir) / "test_file.pkl"
            
            assert cache_path == expected_path
    
    def test_cache_exists_true(self):
        """Test cache existence check - file exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Create test file
            test_file = Path(temp_dir) / "test.pkl"
            test_file.touch()
            
            assert cache_manager.cache_exists("test", "pkl") is True
    
    def test_cache_exists_false(self):
        """Test cache existence check - file doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            assert cache_manager.cache_exists("nonexistent", "pkl") is False
    
    @patch('pickle.dump')
    @patch('builtins.open', new_callable=MagicMock)
    def test_save_cache_success(self, mock_open, mock_pickle_dump):
        """Test successful cache saving"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            result = cache_manager.save_cache("test_data", "test_file", "pkl")
            
            assert result is True
            mock_open.assert_called_once()
            mock_pickle_dump.assert_called_once()
    
    @patch('pickle.dump')
    @patch('builtins.open', new_callable=MagicMock)
    def test_save_cache_failure(self, mock_open, mock_pickle_dump):
        """Test cache saving failure"""
        mock_pickle_dump.side_effect = Exception("Save failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            result = cache_manager.save_cache("test_data", "test_file", "pkl")
            
            assert result is False
    
    def test_clear_cache(self):
        """Test cache clearing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Create test files
            (Path(temp_dir) / "file1.pkl").touch()
            (Path(temp_dir) / "file2.index").touch()
            (Path(temp_dir) / "file3.txt").touch()  # Should not be deleted
            
            result = cache_manager.clear_cache()
            
            assert result["deleted_files_count"] == 2
            assert (Path(temp_dir) / "file3.txt").exists()  # Non-cache file preserved


class TestRetrieversUnit:
    """Unit tests for retriever classes"""
    
    def test_tfidf_retriever_initialization(self):
        """Test TFIDFRetriever initialization"""
        sentences = ["sentence 1", "sentence 2"]
        sources = ["source1", "source2"]
        documents = [{"id": 1}, {"id": 2}]
        
        retriever = TFIDFRetriever(sentences, sources, documents)
        
        assert retriever.sentences == sentences
        assert retriever.sources == sources
        assert retriever.documents == documents
        assert retriever.vectorizer is None
        assert retriever.tfidf_matrix is None
    
    @patch('retrievers.TfidfVectorizer')
    def test_tfidf_retriever_initialization_success(self, mock_vectorizer_class):
        """Test successful TFIDFRetriever initialization"""
        mock_vectorizer = Mock()
        mock_matrix = Mock()
        mock_vectorizer.fit_transform.return_value = mock_matrix
        mock_vectorizer_class.return_value = mock_vectorizer
        
        sentences = ["sentence 1", "sentence 2"]
        sources = ["source1", "source2"]
        documents = [{"id": 1}, {"id": 2}]
        
        retriever = TFIDFRetriever(sentences, sources, documents)
        result = retriever.initialize()
        
        assert result is True
        assert retriever.vectorizer == mock_vectorizer
        assert retriever.tfidf_matrix == mock_matrix
    
    def test_embedding_retriever_initialization(self):
        """Test EmbeddingRetriever initialization"""
        sentences = ["sentence 1", "sentence 2"]
        sources = ["source1", "source2"]
        documents = [{"id": 1}, {"id": 2}]
        
        retriever = EmbeddingRetriever(sentences, sources, documents)
        
        assert retriever.sentences == sentences
        assert retriever.sources == sources
        assert retriever.documents == documents
        assert retriever.model is None
        assert retriever.embeddings is None
    
    def test_faiss_retriever_initialization(self):
        """Test FAISSRetriever initialization"""
        sentences = ["sentence 1", "sentence 2"]
        sources = ["source1", "source2"]
        documents = [{"id": 1}, {"id": 2}]
        
        retriever = FAISSRetriever(sentences, sources, documents)
        
        assert retriever.sentences == sentences
        assert retriever.sources == sources
        assert retriever.documents == documents
        assert retriever.model is None
        assert retriever.index is None
        assert retriever.embeddings is None


class TestModelsUnit:
    """Unit tests for Pydantic models"""
    
    def test_query_request_valid(self):
        """Test valid QueryRequest creation"""
        request = QueryRequest(
            query="test query",
            method="faiss",
            top_k=5,
            min_score=0.5
        )
        
        assert request.query == "test query"
        assert request.method == "faiss"
        assert request.top_k == 5
        assert request.min_score == 0.5
    
    def test_query_request_defaults(self):
        """Test QueryRequest with default values"""
        request = QueryRequest(query="test")
        
        assert request.query == "test"
        assert request.method == "faiss"
        assert request.top_k == settings.DEFAULT_TOP_K
        assert request.min_score == settings.MIN_SIMILARITY_SCORE
    
    def test_query_request_validation_empty_query(self):
        """Test QueryRequest validation with empty query"""
        with pytest.raises(ValueError, match="Query must not be empty"):
            QueryRequest(query="")
    
    def test_query_request_validation_invalid_method(self):
        """Test QueryRequest validation with invalid method"""
        with pytest.raises(ValueError, match="Method must be one of"):
            QueryRequest(query="test", method="invalid")
    
    def test_query_request_validation_invalid_top_k(self):
        """Test QueryRequest validation with invalid top_k"""
        with pytest.raises(ValueError, match="top_k must be between"):
            QueryRequest(query="test", top_k=0)
        
        with pytest.raises(ValueError, match="top_k must be between"):
            QueryRequest(query="test", top_k=settings.MAX_TOP_K + 1)
    
    def test_query_request_validation_invalid_min_score(self):
        """Test QueryRequest validation with invalid min_score"""
        with pytest.raises(ValueError, match="min_score must be between"):
            QueryRequest(query="test", min_score=-0.1)
        
        with pytest.raises(ValueError, match="min_score must be between"):
            QueryRequest(query="test", min_score=1.1)
    
    def test_query_response_creation(self):
        """Test QueryResponse creation"""
        response = QueryResponse(
            query="test query",
            method_used="faiss",
            total_results=5,
            execution_time_ms=150.5
        )
        
        assert response.query == "test query"
        assert response.method_used == "faiss"
        assert response.total_results == 5
        assert response.execution_time_ms == 150.5
        assert response.tfidf_results == []
        assert response.embedding_results == []
        assert response.faiss_results == []
    
    def test_health_response_creation(self):
        """Test HealthResponse creation"""
        response = HealthResponse(
            status="healthy",
            data_loaded=True,
            total_sentences=1000,
            total_documents=500
        )
        
        assert response.status == "healthy"
        assert response.data_loaded is True
        assert response.total_sentences == 1000
        assert response.total_documents == 500
    
    def test_stats_response_creation(self):
        """Test StatsResponse creation"""
        response = StatsResponse(
            total_sentences=1000,
            total_documents=500,
            document_type_counts={"type1": 300, "type2": 200}
        )
        
        assert response.total_sentences == 1000
        assert response.total_documents == 500
        assert response.document_type_counts == {"type1": 300, "type2": 200}


class TestConfigUnit:
    """Unit tests for configuration"""
    
    @pytest.mark.unit
    def test_settings_defaults(self):
        """Test default settings values"""
        assert settings.DEFAULT_TOP_K > 0
        assert settings.MAX_TOP_K > settings.DEFAULT_TOP_K
        assert 0 <= settings.MIN_SIMILARITY_SCORE <= 1
        assert settings.CACHE_ENABLED in [True, False]
    
    @pytest.mark.unit
    def test_settings_types(self):
        """Test settings types"""
        assert isinstance(settings.DEFAULT_TOP_K, int)
        assert isinstance(settings.MAX_TOP_K, int)
        assert isinstance(settings.MIN_SIMILARITY_SCORE, float)
        assert isinstance(settings.CACHE_ENABLED, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=term-missing"])
