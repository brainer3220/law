from fastapi import FastAPI, HTTPException
import uvicorn
import logging
import time
import os
from typing import Dict, Any
from contextlib import asynccontextmanager

from config import settings
from models import (
    QueryRequest, QueryResponse, HealthResponse, StatsResponse, 
    CacheResponse, ReloadResponse
)
from data_loader import DataLoader
from cache_manager import CacheManager
from retrievers import TFIDFRetriever, EmbeddingRetriever, FAISSRetriever

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global instances
data_loader = DataLoader()
cache_manager = CacheManager()
tfidf_retriever = None
embedding_retriever = None
faiss_retriever = None

def initialize_retrievers() -> Dict[str, bool]:
    """Initialize all retrieval methods with caching"""
    global tfidf_retriever, embedding_retriever, faiss_retriever
    
    if not data_loader.is_loaded:
        logger.error("Data not loaded, cannot initialize retrievers")
        return {"tfidf": False, "embedding": False, "faiss": False}
    
    sentences, sources, documents = data_loader.get_data()
    data_hash = cache_manager.get_data_hash(sentences)
    cache_files = cache_manager.get_cache_files(data_hash)
    
    results = {}
    
    # Initialize TF-IDF Retriever
    try:
        logger.info("Initializing TF-IDF retriever...")
        tfidf_retriever = TFIDFRetriever(sentences, sources, documents)
        
        # Try to load from cache
        cached_vectorizer = cache_manager.load_pickle(cache_files['vectorizer'])
        cached_matrix = cache_manager.load_pickle(cache_files['tfidf_matrix'])
        
        if cached_vectorizer and cached_matrix:
            logger.info("Loading TF-IDF from cache...")
            tfidf_retriever.vectorizer = cached_vectorizer
            tfidf_retriever.tfidf_matrix = cached_matrix
            tfidf_retriever.is_initialized = True
            results["tfidf"] = True
        else:
            logger.info("Creating new TF-IDF...")
            if tfidf_retriever.initialize():
                # Save to cache
                cache_manager.save_pickle(tfidf_retriever.vectorizer, cache_files['vectorizer'])
                cache_manager.save_pickle(tfidf_retriever.tfidf_matrix, cache_files['tfidf_matrix'])
                results["tfidf"] = True
            else:
                results["tfidf"] = False
    except Exception as e:
        logger.error(f"Error initializing TF-IDF retriever: {e}")
        results["tfidf"] = False
    
    # Initialize Embedding Retriever
    try:
        logger.info("Initializing embedding retriever...")
        embedding_retriever = EmbeddingRetriever(sentences, sources, documents)
        
        # Try to load from cache
        cached_embeddings = cache_manager.load_pickle(cache_files['embeddings'])
        
        if cached_embeddings is not None:
            logger.info("Loading embeddings from cache...")
            # Still need to load the model for queries
            from sentence_transformers import SentenceTransformer
            embedding_retriever.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            embedding_retriever.embeddings = cached_embeddings
            embedding_retriever.is_initialized = True
            results["embedding"] = True
        else:
            logger.info("Creating new embeddings...")
            if embedding_retriever.initialize():
                # Save to cache
                cache_manager.save_pickle(embedding_retriever.embeddings, cache_files['embeddings'])
                results["embedding"] = True
            else:
                results["embedding"] = False
    except Exception as e:
        logger.error(f"Error initializing embedding retriever: {e}")
        results["embedding"] = False
    
    # Initialize FAISS Retriever
    try:
        logger.info("Initializing FAISS retriever...")
        faiss_retriever = FAISSRetriever(sentences, sources, documents)
        
        # Try to load from cache
        cached_index = cache_manager.load_faiss_index(cache_files['faiss_index'])
        cached_embeddings = cache_manager.load_pickle(cache_files['embeddings'])
        
        if cached_index and cached_embeddings is not None:
            logger.info("Loading FAISS from cache...")
            from sentence_transformers import SentenceTransformer
            faiss_retriever.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            faiss_retriever.index = cached_index
            faiss_retriever.embeddings = cached_embeddings
            faiss_retriever.is_initialized = True
            results["faiss"] = True
        else:
            logger.info("Creating new FAISS index...")
            if faiss_retriever.initialize():
                # Save to cache
                cache_manager.save_faiss_index(faiss_retriever.index, cache_files['faiss_index'])
                cache_manager.save_pickle(faiss_retriever.embeddings, cache_files['embeddings'])
                results["faiss"] = True
            else:
                results["faiss"] = False
    except Exception as e:
        logger.error(f"Error initializing FAISS retriever: {e}")
        results["faiss"] = False
    
    return results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI"""
    # Startup
    logger.info("Starting Legal RAG API v2.0...")
    
    # Load data
    if not data_loader.load_data():
        logger.error("Failed to load legal data")
        return
    
    # Initialize retrievers
    results = initialize_retrievers()
    
    logger.info(f"Retriever initialization results: {results}")
    logger.info("Legal RAG API startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal RAG API...")


# FastAPI app with lifespan
app = FastAPI(
    title="Legal RAG API", 
    description="Korean Legal Document RAG System",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with system information"""
    if not data_loader.is_loaded:
        return {"error": "Data not loaded"}
    
    stats = data_loader.get_stats()
    
    return {
        "message": "Legal RAG API v2.0",
        "status": "running",
        "total_sentences": stats.get("total_sentences", 0),
        "total_documents": stats.get("total_documents", 0),
        "document_type_counts": stats.get("document_type_counts", {}),
        "models_ready": {
            "tfidf": tfidf_retriever and tfidf_retriever.is_initialized,
            "embedding": embedding_retriever and embedding_retriever.is_initialized,
            "faiss": faiss_retriever and faiss_retriever.is_initialized
        }
    }
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if not data_loader.is_loaded:
        sentences, sources, documents = [], [], []
        data_hash = "no_data"
    else:
        sentences, sources, documents = data_loader.get_data()
        data_hash = cache_manager.get_data_hash(sentences)
    
    return HealthResponse(
        status="healthy" if data_loader.is_loaded else "no_data",
        data_loaded=data_loader.is_loaded,
        total_sentences=len(sentences),
        total_documents=len(documents),
        models_ready={
            "tfidf": tfidf_retriever and tfidf_retriever.is_initialized,
            "embedding": embedding_retriever and embedding_retriever.is_initialized,
            "faiss": faiss_retriever and faiss_retriever.is_initialized
        },
        cache_info=cache_manager.get_cache_info(data_hash)
    )


@app.post("/search", response_model=QueryResponse)
async def search_documents(request: QueryRequest):
    """Search legal documents using RAG"""
    if not data_loader.is_loaded:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    start_time = time.time()
    response = QueryResponse(
        query=request.query,
        method_used=request.method,
        total_results=0,
        execution_time_ms=0
    )
    
    try:
        all_results = []
        
        if request.method in ["tfidf", "both"]:
            if tfidf_retriever and tfidf_retriever.is_initialized:
                response.tfidf_results = tfidf_retriever.search(
                    request.query, request.top_k, request.min_score
                )
                all_results.extend(response.tfidf_results or [])
            else:
                logger.warning("TF-IDF retriever not available")
        
        if request.method in ["embedding", "both"]:
            if embedding_retriever and embedding_retriever.is_initialized:
                response.embedding_results = embedding_retriever.search(
                    request.query, request.top_k, request.min_score
                )
                all_results.extend(response.embedding_results or [])
            else:
                logger.warning("Embedding retriever not available")
        
        if request.method in ["faiss", "both"]:
            if faiss_retriever and faiss_retriever.is_initialized:
                response.faiss_results = faiss_retriever.search(
                    request.query, request.top_k, request.min_score
                )
                all_results.extend(response.faiss_results or [])
            else:
                logger.warning("FAISS retriever not available")
        
        response.total_results = len(all_results)
        response.execution_time_ms = (time.time() - start_time) * 1000
        
        return response
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get statistics about the loaded data"""
    if not data_loader.is_loaded:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    stats = data_loader.get_stats()
    sentences, _, _ = data_loader.get_data()
    data_hash = cache_manager.get_data_hash(sentences)
    
    return StatsResponse(
        total_sentences=stats.get("total_sentences", 0),
        total_documents=stats.get("total_documents", 0),
        document_type_counts=stats.get("document_type_counts", {}),
        models_ready={
            "tfidf": tfidf_retriever and tfidf_retriever.is_initialized,
            "embedding": embedding_retriever and embedding_retriever.is_initialized,
            "faiss": faiss_retriever and faiss_retriever.is_initialized
        },
        cache_info=cache_manager.get_cache_info(data_hash),
        system_info={
            "cpu_count": os.cpu_count(),
            "cache_enabled": cache_manager.enabled,
            "embedding_model": settings.EMBEDDING_MODEL,
            "tfidf_max_features": settings.TFIDF_MAX_FEATURES
        }
    )


@app.delete("/cache", response_model=CacheResponse)
async def clear_cache():
    """Clear all cache files"""
    try:
        result = cache_manager.clear_cache()
        
        return CacheResponse(
            message="Cache cleared successfully" if result["success"] else "Failed to clear cache",
            deleted_files=result["deleted_files"],
            freed_space_mb=result["freed_space_mb"],
            cache_status={"cleared": result["success"]}
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@app.post("/reload", response_model=ReloadResponse)
async def reload_data():
    """Reload data and reinitialize models"""
    global tfidf_retriever, embedding_retriever, faiss_retriever
    
    try:
        start_time = time.time()
        logger.info("Reloading data and models...")
        
        # Clear current models
        tfidf_retriever = None
        embedding_retriever = None
        faiss_retriever = None
        
        # Reload data
        if not data_loader.reload():
            raise HTTPException(status_code=500, detail="Failed to reload data")
        
        # Reinitialize retrievers
        results = initialize_retrievers()
        
        execution_time = (time.time() - start_time) * 1000
        stats = data_loader.get_stats()
        
        return ReloadResponse(
            message="Data and models reloaded successfully",
            total_sentences=stats.get("total_sentences", 0),
            total_documents=stats.get("total_documents", 0),
            models_initialized=results,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Error reloading data: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload data")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # Use import string for reload support
        host=settings.API_HOST, 
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )