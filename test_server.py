#!/usr/bin/env python3
"""
Quick test server for embedding reuse functionality
"""
import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
import numpy as np
import time

from model_manager import model_manager, get_embedding_model, get_embeddings
from config import settings

# Configure minimal logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Legal RAG API - Test Mode", version="2.0.0-test")

# Sample legal texts for testing
SAMPLE_TEXTS = [
    "법원의 판결에 대한 분석 및 검토가 필요합니다.",
    "헌법상 기본권의 보장은 민주주의의 핵심 요소입니다.",
    "민법상 계약의 성립요건은 의사표시의 합치가 필요합니다.",
    "형법상 고의의 인정 기준에 대한 판례 분석입니다.",
    "행정법상 재량권의 범위와 한계에 대한 논의입니다."
]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Legal RAG API v2.0 - Test Mode",
        "status": "running",
        "mode": "embedding_reuse_test",
        "loaded_models": model_manager.list_loaded_models(),
        "memory_usage": model_manager.get_memory_usage()
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "test_mode": True,
        "embedding_model": settings.EMBEDDING_MODEL,
        "sample_texts_count": len(SAMPLE_TEXTS)
    }

@app.post("/embeddings/test-reuse")
async def test_embedding_reuse():
    """Test embedding reuse functionality with sample texts"""
    try:
        logger.info("Testing embedding reuse functionality...")
        
        start_time = time.time()
        
        # First generation (should be slower)
        logger.info("First embedding generation (cache miss)...")
        embeddings1 = get_embeddings(SAMPLE_TEXTS, use_cache=True)
        first_time = time.time() - start_time
        
        if embeddings1 is None:
            raise HTTPException(status_code=500, detail="Failed to generate embeddings")
        
        # Second generation (should be faster due to cache)
        logger.info("Second embedding generation (cache hit)...")
        start_time2 = time.time()
        embeddings2 = get_embeddings(SAMPLE_TEXTS, use_cache=True)
        second_time = time.time() - start_time2
        
        if embeddings2 is None:
            raise HTTPException(status_code=500, detail="Failed to generate embeddings on second try")
        
        # Verify they are the same
        are_same = np.array_equal(embeddings1, embeddings2)
        speedup = first_time / second_time if second_time > 0 else float('inf')
        
        logger.info(f"Embedding reuse test completed - Speedup: {speedup:.2f}x")
        
        return {
            "message": "Embedding reuse test completed successfully",
            "first_generation_time_ms": first_time * 1000,
            "second_generation_time_ms": second_time * 1000,
            "speedup_factor": speedup,
            "embeddings_identical": are_same,
            "embedding_shape": list(embeddings1.shape),
            "sample_texts_count": len(SAMPLE_TEXTS),
            "cache_hit": second_time < first_time * 0.1,
            "performance_analysis": {
                "cache_effective": speedup > 5.0,
                "model_reused": settings.EMBEDDING_MODEL in model_manager.list_loaded_models(),
                "memory_efficient": are_same
            }
        }
    except Exception as e:
        logger.error(f"Error testing embedding reuse: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test embedding reuse: {str(e)}")

@app.get("/embeddings/cache/info")
async def get_embedding_cache_info():
    """Get information about cached embeddings"""
    try:
        memory_info = model_manager.get_memory_usage()
        return {
            "message": "Embedding cache information retrieved successfully",
            "total_cache_items": memory_info.get("total_embedding_cache_items", 0),
            "total_cache_size_mb": memory_info.get("total_embedding_cache_size_mb", 0),
            "model_info": {
                "total_models": memory_info.get("total_models", 0),
                "total_model_size_mb": memory_info.get("total_model_size_mb", 0)
            },
            "total_memory_mb": memory_info.get("total_memory_mb", 0),
            "cache_details": memory_info.get("embedding_cache_info", {})
        }
    except Exception as e:
        logger.error(f"Error getting embedding cache info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get embedding cache information")

@app.delete("/embeddings/cache")
async def clear_embeddings_cache():
    """Clear cached embeddings"""
    try:
        count = model_manager.clear_embedding_cache()
        return {
            "message": f"Cleared {count} cached embeddings from memory",
            "cleared_count": count
        }
    except Exception as e:
        logger.error(f"Error clearing embedding cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear embedding cache")

@app.post("/models/preload")
async def preload_embedding_model():
    """Preload embedding model"""
    try:
        start_time = time.time()
        model = get_embedding_model(settings.EMBEDDING_MODEL)
        load_time = (time.time() - start_time) * 1000
        
        if model is None:
            raise HTTPException(status_code=500, detail="Failed to preload embedding model")
        
        return {
            "message": f"Embedding model {settings.EMBEDDING_MODEL} preloaded successfully",
            "model_name": settings.EMBEDDING_MODEL,
            "load_time_ms": load_time,
            "embedding_dimension": model.get_sentence_embedding_dimension(),
            "max_seq_length": getattr(model, 'max_seq_length', 'unknown')
        }
    except Exception as e:
        logger.error(f"Error preloading model: {e}")
        raise HTTPException(status_code=500, detail="Failed to preload model")

if __name__ == "__main__":
    logger.info("Starting Legal RAG API Test Server...")
    uvicorn.run(
        "test_server:app",
        host="0.0.0.0",
        port=8001,  # Use different port to avoid conflict
        reload=False  # Disable reload for faster startup
    )
