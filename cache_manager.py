"""
Cache management utilities
"""
import pickle
import hashlib
from p    def save_faiss_index(self, index: Any, cache_file: Path) -> bool:
        """Save FAISS index to cache file"""
        if not self.cache_enabled or not FAISS_AVAILABLE:
            return False
            
        try:
            faiss.write_index(index, str(cache_file))
            logger.info(f"FAISS index saved to {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving FAISS index to {cache_file}: {e}")
            return False
    
    def load_faiss_index(self, cache_file: Path) -> Any:
        """Load FAISS index from cache file"""
        if not self.cache_enabled or not FAISS_AVAILABLE:
            return Noneh
from typing import Any, Dict, List, Union
import logging
from config import settings

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for models and data"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or settings.CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_enabled = settings.CACHE_ENABLED
        # Add enabled property for compatibility
        self.enabled = self.cache_enabled
    
    def get_data_hash(self, data: List[str]) -> str:
        """Generate hash for the current dataset to detect changes"""
        data_str = "".join(data) if data else ""
        return hashlib.md5(data_str.encode(), usedforsecurity=False).hexdigest()
    
    def get_cache_files(self, data_hash: str) -> Dict[str, Path]:
        """Get cache file paths for current data hash"""
        return {
            'tfidf_matrix': self.cache_dir / f"tfidf_matrix_{data_hash}.pkl",
            'vectorizer': self.cache_dir / f"vectorizer_{data_hash}.pkl",
            'embeddings': self.cache_dir / f"embeddings_{data_hash}.pkl",
            'faiss_index': self.cache_dir / f"faiss_index_{data_hash}.index",
            'sentences': self.cache_dir / f"sentences_{data_hash}.pkl",
            'sources': self.cache_dir / f"sources_{data_hash}.pkl",
            'metadata': self.cache_dir / f"metadata_{data_hash}.pkl"
        }
    
    def save_pickle(self, data: Any, cache_file: Path) -> bool:
        """Save data to pickle cache file"""
        if not self.enabled:
            return False
            
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Cache saved to {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving cache to {cache_file}: {e}")
            return False
    
    def load_pickle(self, cache_file: Path) -> Any:
        """Load data from pickle cache file"""
        if not self.enabled:
            return None
            
        try:
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"Cache loaded from {cache_file}")
                return data
            return None
        except Exception as e:
            logger.error(f"Error loading cache from {cache_file}: {e}")
            return None
    
    def save_faiss_index(self, index: faiss.Index, cache_file: Path) -> bool:
        """Save FAISS index to cache file"""
        if not self.enabled:
            return False
            
        try:
            faiss.write_index(index, str(cache_file))
            logger.info(f"FAISS index saved to {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving FAISS index to {cache_file}: {e}")
            return False
    
    def load_faiss_index(self, cache_file: Path) -> faiss.Index:
        """Load FAISS index from cache file"""
        if not self.enabled:
            return None
            
        try:
            if cache_file.exists():
                index = faiss.read_index(str(cache_file))
                logger.info(f"FAISS index loaded from {cache_file}")
                return index
            return None
        except Exception as e:
            logger.error(f"Error loading FAISS index from {cache_file}: {e}")
            return None
    
    def clear_cache(self, data_hash: str = None) -> Dict[str, Any]:
        """Clear cache files"""
        try:
            deleted_files = []
            total_size = 0
            
            if data_hash:
                # Clear specific hash cache
                cache_files = self.get_cache_files(data_hash)
                for cache_file in cache_files.values():
                    if cache_file.exists():
                        size = cache_file.stat().st_size
                        cache_file.unlink()
                        deleted_files.append(cache_file.name)
                        total_size += size
            else:
                # Clear all cache files
                for cache_file in self.cache_dir.glob("*"):
                    if cache_file.is_file():
                        size = cache_file.stat().st_size
                        cache_file.unlink()
                        deleted_files.append(cache_file.name)
                        total_size += size
            
            logger.info(f"Cleared {len(deleted_files)} cache files, freed {total_size / (1024*1024):.2f} MB")
            
            return {
                "deleted_files": deleted_files,
                "freed_space_mb": round(total_size / (1024*1024), 2),
                "success": True
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {
                "deleted_files": [],
                "freed_space_mb": 0,
                "success": False,
                "error": str(e)
            }
    
    def get_cache_info(self, data_hash: str) -> Dict[str, Any]:
        """Get information about cache files"""
        cache_files = self.get_cache_files(data_hash)
        cache_info = {}
        total_size = 0
        
        for cache_type, cache_path in cache_files.items():
            exists = cache_path.exists()
            size = cache_path.stat().st_size if exists else 0
            cache_info[cache_type] = {
                "exists": exists,
                "size_mb": round(size / (1024*1024), 2),
                "path": str(cache_path)
            }
            total_size += size
        
        return {
            "data_hash": data_hash,
            "cache_files": cache_info,
            "total_cache_size_mb": round(total_size / (1024*1024), 2),
            "cache_enabled": self.enabled
        }
