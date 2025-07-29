"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Literal, Any
from config import settings


class QueryRequest(BaseModel):
    """Request model for search queries"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    method: Literal["tfidf", "embedding", "faiss", "both"] = Field(
        default="faiss", description="Retrieval method to use"
    )
    top_k: int = Field(
        default=settings.DEFAULT_TOP_K, 
        ge=1, 
        le=settings.MAX_TOP_K, 
        description="Number of results to return"
    )
    min_score: float = Field(
        default=settings.MIN_SIMILARITY_SCORE,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )

    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class RetrievalResult(BaseModel):
    """Single retrieval result"""
    sentence: str = Field(..., description="Retrieved sentence")
    source: str = Field(..., description="Document source type")
    score: float = Field(..., ge=0.0, description="Similarity score")
    document: Dict = Field(..., description="Full source document")
    rank: int = Field(..., ge=1, description="Rank in results")


class QueryResponse(BaseModel):
    """Response model for search queries"""
    query: str = Field(..., description="Original query")
    method_used: str = Field(..., description="Retrieval method(s) used")
    total_results: int = Field(..., ge=0, description="Total number of results")
    execution_time_ms: float = Field(..., ge=0, description="Query execution time in milliseconds")
    
    # Results by method
    tfidf_results: Optional[List[RetrievalResult]] = None
    embedding_results: Optional[List[RetrievalResult]] = None
    faiss_results: Optional[List[RetrievalResult]] = None


class ModelInfo(BaseModel):
    """Information about a loaded model"""
    model_name: str = Field(..., description="Name of the model")
    max_seq_length: int = Field(..., description="Maximum sequence length")
    embedding_dimension: int = Field(..., description="Embedding dimension")
    loaded_at: str = Field(..., description="When the model was loaded")


class ModelManagerResponse(BaseModel):
    """Response for model manager operations"""
    message: str = Field(..., description="Operation result message")
    loaded_models: Dict[str, ModelInfo] = Field(..., description="Currently loaded models")
    memory_usage: Dict[str, Any] = Field(..., description="Memory usage information")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    data_loaded: bool
    total_sentences: int
    total_documents: int
    models_ready: Dict[str, bool]
    cache_info: Dict[str, Any]
    model_manager_info: Optional[Dict[str, Any]] = None


class StatsResponse(BaseModel):
    """Statistics response"""
    total_sentences: int
    total_documents: int
    document_type_counts: Dict[str, int]
    models_ready: Dict[str, bool]
    cache_info: Dict[str, Any]
    system_info: Dict[str, Any]
    model_manager_info: Optional[Dict[str, Any]] = None


class CacheResponse(BaseModel):
    """Cache operation response"""
    message: str
    deleted_files: Optional[List[str]] = None
    freed_space_mb: Optional[float] = None
    cache_status: Dict[str, Any]


class ReloadResponse(BaseModel):
    """Data reload response"""
    message: str
    total_sentences: int
    total_documents: int
    models_initialized: Dict[str, bool]
    execution_time_ms: float
