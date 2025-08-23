"""
Configuration settings for Legal RAG API
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Dict, Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    
    # Model settings
    EMBEDDING_MODEL: str = "jhgan/ko-sroberta-multitask"
    TFIDF_MAX_FEATURES: int = 10000
    
    # Cache settings
    CACHE_DIR: Path = Path("cache")
    CACHE_ENABLED: bool = True  # Renamed from ENABLE_CACHE
    
    # Data settings
    DATASET_DIR: Path = Path("datasets/korean_legal_dataset")
    DATA_DIRECTORIES: List[str] = [
        "full_data/Training/01.원천데이터/TS_01. 민사법_001. 판결문/",
        "full_data/Training/01.원천데이터/TS_01. 민사법_002. 법령/",
        "full_data/Training/01.원천데이터/TS_01. 민사법_003. 심결례/",
        "full_data/Training/01.원천데이터/TS_01. 민사법_004. 유권해석/",
    ]
    
    # Search settings
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 100
    MIN_SIMILARITY_SCORE: float = 0.1
    
    # Performance settings
    MAX_WORKERS: Optional[int] = None  # Will use os.cpu_count() if None
    BATCH_SIZE: int = 32
    DATA_BATCH_SIZE: int = 1000  # Batch size for data processing
    MAX_SENTENCES_LIMIT: Optional[int] = 5000  # Limit for faster startup (None = no limit)
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "legal_rag.log"

    # Database settings (optional; used by packages/legal_schemas/db)
    DATABASE_URL: str = "sqlite:///./legal.db"  # e.g., postgresql+psycopg://user:pass@localhost:5432/legal
    DB_ECHO: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from environment
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.MAX_WORKERS is None:
            self.MAX_WORKERS = os.cpu_count() or 4


# Global settings instance
settings = Settings()

# Set MAX_WORKERS if None
if settings.MAX_WORKERS is None:
    settings.MAX_WORKERS = os.cpu_count() or 4
