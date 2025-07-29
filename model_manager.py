"""
Model manager for reusable embedding models and other ML components
"""
import logging
import threading
import hashlib
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from sentence_transformers import SentenceTransformer
from config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Singleton class to manage reusable ML models"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._models: Dict[str, Any] = {}
            self._model_configs: Dict[str, Dict[str, Any]] = {}
            self._embedding_cache: Dict[str, np.ndarray] = {}  # Cache for embeddings
            self._lock = threading.Lock()
            self._initialized = True
            logger.info("ModelManager initialized with embedding cache")
    
    def get_embedding_model(self, model_name: str = None) -> Optional[SentenceTransformer]:
        """
        Get or create embedding model instance
        
        Args:
            model_name: Name of the model to load. If None, uses default from settings
            
        Returns:
            SentenceTransformer instance or None if loading fails
        """
        if model_name is None:
            model_name = settings.EMBEDDING_MODEL
        
        # Check if model is already loaded
        if model_name in self._models:
            logger.debug(f"Reusing cached embedding model: {model_name}")
            return self._models[model_name]
        
        # Load model with thread safety
        with self._lock:
            # Double-check pattern
            if model_name in self._models:
                return self._models[model_name]
            
            try:
                logger.info(f"Loading embedding model: {model_name}")
                model = SentenceTransformer(model_name)
                
                # Store model and its config
                self._models[model_name] = model
                self._model_configs[model_name] = {
                    'model_name': model_name,
                    'max_seq_length': getattr(model, 'max_seq_length', 512),
                    'embedding_dimension': model.get_sentence_embedding_dimension(),
                    'loaded_at': logger.info.__self__.handlers[0].formatter.formatTime(
                        logging.LogRecord('', 0, '', 0, '', (), None)
                    ) if logger.handlers else 'unknown'
                }
                
                logger.info(f"Successfully loaded embedding model: {model_name}")
                logger.info(f"Model config: {self._model_configs[model_name]}")
                
                return model
                
            except Exception as e:
                logger.error(f"Failed to load embedding model {model_name}: {e}")
                return None
    
    def _get_text_hash(self, texts: List[str], model_name: str) -> str:
        """Generate hash for text list and model combination"""
        text_content = "|".join(texts)
        combined = f"{model_name}:{text_content}"
        return hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()
    
    def get_embeddings(self, texts: List[str], model_name: str = None, 
                      batch_size: int = None, use_cache: bool = True) -> Optional[np.ndarray]:
        """
        Get embeddings for texts with caching support
        
        Args:
            texts: List of texts to embed
            model_name: Name of embedding model to use
            batch_size: Batch size for encoding
            use_cache: Whether to use embedding cache
            
        Returns:
            Numpy array of embeddings or None if failed
        """
        if model_name is None:
            model_name = settings.EMBEDDING_MODEL
        
        if batch_size is None:
            batch_size = getattr(settings, 'BATCH_SIZE', 32)
        
        # Check cache first
        if use_cache:
            cache_key = self._get_text_hash(texts, model_name)
            if cache_key in self._embedding_cache:
                logger.debug(f"Retrieved embeddings from cache for {len(texts)} texts")
                return self._embedding_cache[cache_key]
        
        # Get model
        model = self.get_embedding_model(model_name)
        if model is None:
            logger.error(f"Failed to get model {model_name} for embedding generation")
            return None
        
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts with model {model_name}")
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,  # Only show progress for large batches
                convert_to_numpy=True
            )
            
            # Cache the embeddings if requested
            if use_cache:
                cache_key = self._get_text_hash(texts, model_name)
                self._embedding_cache[cache_key] = embeddings
                logger.debug(f"Cached embeddings for {len(texts)} texts")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings with model {model_name}: {e}")
            return None
    
    def clear_embedding_cache(self) -> int:
        """Clear all cached embeddings and return count of cleared items"""
        with self._lock:
            count = len(self._embedding_cache)
            self._embedding_cache.clear()
            logger.info(f"Cleared {count} cached embeddings")
            return count
    
    def get_model_info(self, model_name: str = None) -> Optional[Dict[str, Any]]:
        """Get information about a loaded model"""
        if model_name is None:
            model_name = settings.EMBEDDING_MODEL
        
        return self._model_configs.get(model_name)
    
    def list_loaded_models(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded models and their configurations"""
        return self._model_configs.copy()
    
    def clear_model(self, model_name: str = None) -> bool:
        """
        Clear a specific model from cache
        
        Args:
            model_name: Name of model to clear. If None, uses default
            
        Returns:
            True if model was cleared, False if not found
        """
        if model_name is None:
            model_name = settings.EMBEDDING_MODEL
        
        with self._lock:
            if model_name in self._models:
                del self._models[model_name]
                if model_name in self._model_configs:
                    del self._model_configs[model_name]
                
                # Clear related embedding cache
                keys_to_remove = [key for key in self._embedding_cache.keys() 
                                 if key.startswith(f"{model_name}:")]
                for key in keys_to_remove:
                    del self._embedding_cache[key]
                
                logger.info(f"Cleared model and {len(keys_to_remove)} cached embeddings: {model_name}")
                return True
            return False
    
    def clear_all_models(self) -> int:
        """
        Clear all models from cache
        
        Returns:
            Number of models cleared
        """
        with self._lock:
            model_count = len(self._models)
            embedding_count = len(self._embedding_cache)
            
            self._models.clear()
            self._model_configs.clear()
            self._embedding_cache.clear()
            
            logger.info(f"Cleared {model_count} models and {embedding_count} cached embeddings")
            return model_count
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information for loaded models and cached embeddings"""
        import sys
        
        total_model_size = 0
        model_sizes = {}
        
        # Calculate model sizes
        for model_name, model in self._models.items():
            try:
                # Estimate model size (rough approximation)
                model_size = sys.getsizeof(model)
                if hasattr(model, 'state_dict'):
                    # For PyTorch models, get parameter size
                    param_size = sum(p.numel() * p.element_size() for p in model.parameters())
                    model_size = max(model_size, param_size)
                
                model_sizes[model_name] = model_size
                total_model_size += model_size
                
            except Exception as e:
                logger.warning(f"Could not calculate size for model {model_name}: {e}")
                model_sizes[model_name] = 0
        
        # Calculate embedding cache sizes
        total_embedding_size = 0
        embedding_cache_info = {}
        
        for cache_key, embeddings in self._embedding_cache.items():
            try:
                size = embeddings.nbytes if hasattr(embeddings, 'nbytes') else sys.getsizeof(embeddings)
                embedding_cache_info[cache_key[:50] + "..."] = {  # Truncate long keys
                    'size_bytes': size,
                    'shape': embeddings.shape if hasattr(embeddings, 'shape') else 'unknown'
                }
                total_embedding_size += size
            except Exception as e:
                logger.warning(f"Could not calculate size for cached embeddings {cache_key}: {e}")
        
        return {
            'total_models': len(self._models),
            'total_model_size_bytes': total_model_size,
            'total_model_size_mb': total_model_size / (1024 * 1024),
            'model_sizes': model_sizes,
            'total_embedding_cache_items': len(self._embedding_cache),
            'total_embedding_cache_size_bytes': total_embedding_size,
            'total_embedding_cache_size_mb': total_embedding_size / (1024 * 1024),
            'embedding_cache_info': embedding_cache_info,
            'total_memory_mb': (total_model_size + total_embedding_size) / (1024 * 1024)
        }


# Global singleton instance
model_manager = ModelManager()


def get_embedding_model(model_name: str = None) -> Optional[SentenceTransformer]:
    """Convenience function to get embedding model"""
    return model_manager.get_embedding_model(model_name)


def get_embeddings(texts: List[str], model_name: str = None, 
                  batch_size: int = None, use_cache: bool = True) -> Optional[np.ndarray]:
    """Convenience function to get embeddings with caching"""
    return model_manager.get_embeddings(texts, model_name, batch_size, use_cache)


def clear_model_cache():
    """Convenience function to clear all model cache"""
    return model_manager.clear_all_models()


def clear_embedding_cache():
    """Convenience function to clear embedding cache"""
    return model_manager.clear_embedding_cache()
