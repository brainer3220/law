"""
Cache management utilities
"""
import pickle
import hashlib
from pathlib import Path
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
    
    def get_cache_file(self, name: str, data_hash: str, ext: str = "pkl") -> Path:
        """Generate cache file path based on name and data hash"""
        return self.cache_dir / f"{name}_{data_hash}.{ext}"
    
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
    
    def save_to_cache(self, obj: Any, cache_file: Path) -> bool:
        """Save object to cache file using pickle"""
        if not self.cache_enabled:
            return False
            
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'wb') as f:
                pickle.dump(obj, f)
            logger.info(f"Object saved to cache: {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving to cache {cache_file}: {e}")
            return False
    
    def load_from_cache(self, cache_file: Path) -> Any:
        """Load object from cache file"""
        if not self.cache_enabled or not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'rb') as f:
                obj = pickle.load(f)
            logger.info(f"Object loaded from cache: {cache_file}")
            return obj
        except Exception as e:
            logger.error(f"Error loading from cache {cache_file}: {e}")
            return None
    
    def save_pickle(self, data: Any, cache_file: Path) -> bool:
        """Save data to pickle cache file (alias for save_to_cache)"""
        return self.save_to_cache(data, cache_file)
    
    def load_pickle(self, cache_file: Path) -> Any:
        """Load data from pickle cache file (alias for load_from_cache)"""
        return self.load_from_cache(cache_file)
    
    def save_faiss_index(self, index: Any, cache_file: Path) -> bool:
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
        if not self.cache_enabled or not FAISS_AVAILABLE or not cache_file.exists():
            return None
            
        try:
            index = faiss.read_index(str(cache_file))
            logger.info(f"FAISS index loaded from cache: {cache_file}")
            return index
        except Exception as e:
            logger.error(f"Error loading FAISS index from {cache_file}: {e}")
            return None
    
    def cache_exists(self, cache_file: Path) -> bool:
        """Check if cache file exists"""
        return cache_file.exists() and cache_file.is_file()
    
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
            
            logger.info(f"Deleted {len(deleted_files)} cache files, freed {total_size} bytes")
            return {
                "deleted_files": deleted_files,
                "count": len(deleted_files),
                "freed_bytes": total_size,
                "freed_mb": total_size / (1024 * 1024)
            }
        
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"error": str(e), "count": 0, "freed_bytes": 0}
    
    def get_cache_size(self) -> int:
        """Get total cache size in bytes"""
        total_size = 0
        try:
            for cache_file in self.cache_dir.glob("*"):
                if cache_file.is_file():
                    total_size += cache_file.stat().st_size
        except Exception as e:
            logger.error(f"Error calculating cache size: {e}")
        
        return total_size
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        if not self.cache_dir.exists():
            return {
                "enabled": self.cache_enabled,
                "cache_dir": str(self.cache_dir),
                "file_count": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0
            }
        
        file_count = len(list(self.cache_dir.glob("*")))
        total_size = self.get_cache_size()
        
        return {
            "enabled": self.cache_enabled,
            "cache_dir": str(self.cache_dir),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024)
        }


# Global cache manager instance
cache_manager = CacheManager()
