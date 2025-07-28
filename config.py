"""
Configuration settings for Legal RAG API
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Dict


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
    ENABLE_CACHE: bool = True
    
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
    MAX_WORKERS: int = None  # Will use os.cpu_count()
    BATCH_SIZE: int = 32
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "legal_rag.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
