"""
Unit tests for ModelManager
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from model_manager import ModelManager, get_embedding_model, clear_model_cache
from config import settings


class TestModelManager:
    """Test ModelManager functionality"""
    
    def test_singleton_pattern(self):
        """Test that ModelManager follows singleton pattern"""
        manager1 = ModelManager()
        manager2 = ModelManager()
        assert manager1 is manager2
    
    @patch('model_manager.SentenceTransformer')
    def test_get_embedding_model_success(self, mock_transformer):
        """Test successful model loading"""
        # Mock model
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        # Clear cache first
        manager.clear_all_models()
        
        # Test model loading
        model = manager.get_embedding_model("test-model")
        
        assert model is not None
        assert model is mock_model
        mock_transformer.assert_called_once_with("test-model")
    
    @patch('model_manager.SentenceTransformer')
    def test_get_embedding_model_caching(self, mock_transformer):
        """Test that models are cached properly"""
        # Mock model
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        manager.clear_all_models()
        
        # Load model twice
        model1 = manager.get_embedding_model("test-model")
        model2 = manager.get_embedding_model("test-model")
        
        # Should be the same instance (cached)
        assert model1 is model2
        # SentenceTransformer should only be called once
        mock_transformer.assert_called_once_with("test-model")
    
    @patch('model_manager.SentenceTransformer')
    def test_get_embedding_model_failure(self, mock_transformer):
        """Test model loading failure"""
        mock_transformer.side_effect = Exception("Model loading failed")
        
        manager = ModelManager()
        manager.clear_all_models()
        
        model = manager.get_embedding_model("invalid-model")
        assert model is None
    
    def test_clear_model(self):
        """Test clearing specific model"""
        manager = ModelManager()
        
        # Mock a loaded model
        mock_model = Mock()
        manager._models["test-model"] = mock_model
        manager._model_configs["test-model"] = {"test": "config"}
        
        # Clear the model
        success = manager.clear_model("test-model")
        assert success is True
        assert "test-model" not in manager._models
        assert "test-model" not in manager._model_configs
        
        # Try to clear non-existent model
        success = manager.clear_model("non-existent")
        assert success is False
    
    def test_clear_all_models(self):
        """Test clearing all models"""
        manager = ModelManager()
        
        # Mock some loaded models
        manager._models["model1"] = Mock()
        manager._models["model2"] = Mock()
        manager._model_configs["model1"] = {"test": "config1"}
        manager._model_configs["model2"] = {"test": "config2"}
        
        # Clear all models
        count = manager.clear_all_models()
        assert count == 2
        assert len(manager._models) == 0
        assert len(manager._model_configs) == 0
    
    def test_list_loaded_models(self):
        """Test listing loaded models"""
        manager = ModelManager()
        manager.clear_all_models()
        
        # Mock some models
        manager._model_configs["model1"] = {"name": "model1", "dim": 768}
        manager._model_configs["model2"] = {"name": "model2", "dim": 384}
        
        models = manager.list_loaded_models()
        assert len(models) == 2
        assert "model1" in models
        assert "model2" in models
        assert models["model1"]["name"] == "model1"
    
    def test_get_model_info(self):
        """Test getting model info"""
        manager = ModelManager()
        
        # Mock model config
        test_config = {"name": "test-model", "dim": 768}
        manager._model_configs["test-model"] = test_config
        
        info = manager.get_model_info("test-model")
        assert info == test_config
        
        # Test non-existent model
        info = manager.get_model_info("non-existent")
        assert info is None
    
    def test_get_memory_usage(self):
        """Test memory usage calculation"""
        manager = ModelManager()
        manager.clear_all_models()
        
        # Mock some models
        mock_model1 = Mock()
        mock_model2 = Mock()
        manager._models["model1"] = mock_model1
        manager._models["model2"] = mock_model2
        
        usage = manager.get_memory_usage()
        
        assert "total_models" in usage
        assert "total_size_bytes" in usage
        assert "total_size_mb" in usage
        assert "model_sizes" in usage
        assert usage["total_models"] == 2


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @patch('model_manager.model_manager')
    def test_get_embedding_model_function(self, mock_manager):
        """Test get_embedding_model convenience function"""
        mock_model = Mock()
        mock_manager.get_embedding_model.return_value = mock_model
        
        result = get_embedding_model("test-model")
        
        assert result is mock_model
        mock_manager.get_embedding_model.assert_called_once_with("test-model")
    
    @patch('model_manager.model_manager')
    def test_clear_model_cache_function(self, mock_manager):
        """Test clear_model_cache convenience function"""
        mock_manager.clear_all_models.return_value = 3
        
        result = clear_model_cache()
        
        assert result == 3
        mock_manager.clear_all_models.assert_called_once()


@pytest.fixture
def cleanup_model_manager():
    """Fixture to clean up model manager after tests"""
    yield
    # Clean up after test
    manager = ModelManager()
    manager.clear_all_models()
