from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from collections import Counter
from scripts.full_data_to_datasets import create_huggingface_dataset
from datasets import Dataset, load_from_disk
import pickle
import os
import hashlib
from pathlib import Path
from tqdm.auto import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import faiss

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Legal RAG API", description="Korean Legal Document RAG System")

# Cache configuration
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Data directories for preprocessing (same as in scripts/full_data_to_datasets.py)
DATA_DIRECTORIES = [
    "full_data/Training/01.원천데이터/TS_01. 민사법_001. 판결문/",
    "full_data/Training/01.원천데이터/TS_01. 민사법_002. 법령/",
    "full_data/Training/01.원천데이터/TS_01. 민사법_003. 심결례/",
    "full_data/Training/01.원천데이터/TS_01. 민사법_004. 유권해석/",
]

# Directory where the preprocessed HuggingFace dataset is stored
DATASET_DIR = Path("korean_legal_dataset")

# Global variables for storing data and models
dataset = None
sentences = []
sentence_sources = []
sentence_docs = []  # 각 sentence가 속한 원본 문서 전체
tfidf_matrix = None
vectorizer = None
embedding_model = None
sentence_embeddings = None
faiss_index = None

class QueryRequest(BaseModel):
    query: str
    method: str = "faiss"  # "tfidf", "embedding", "faiss", or "both"
    top_k: int = 5

class RetrievalResult(BaseModel):
    sentence: str
    source: str
    score: float
    document: dict  # 문서 전체 반환

class QueryResponse(BaseModel):
    query: str
    tfidf_results: Optional[List[RetrievalResult]] = None
    embedding_results: Optional[List[RetrievalResult]] = None
    faiss_results: Optional[List[RetrievalResult]] = None

def get_data_hash(sentences: List[str]) -> str:
    """Generate hash for the current dataset to detect changes"""
    data_str = "".join(sentences)
    return hashlib.md5(data_str.encode()).hexdigest()

def save_cache(data: any, cache_file: Path) -> bool:
    """Save data to cache file"""
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Cache saved to {cache_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving cache to {cache_file}: {e}")
        return False

def load_cache(cache_file: Path) -> any:
    """Load data from cache file"""
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

def get_cache_files(data_hash: str) -> Dict[str, Path]:
    """Get cache file paths for current data hash"""
    return {
        'tfidf_matrix': CACHE_DIR / f"tfidf_matrix_{data_hash}.pkl",
        'vectorizer': CACHE_DIR / f"vectorizer_{data_hash}.pkl",
        'embeddings': CACHE_DIR / f"embeddings_{data_hash}.pkl",
        'faiss_index': CACHE_DIR / f"faiss_index_{data_hash}.index",
        'sentences': CACHE_DIR / f"sentences_{data_hash}.pkl",
        'sources': CACHE_DIR / f"sources_{data_hash}.pkl"
    }

def save_faiss_index(index: faiss.Index, cache_file: Path) -> bool:
    """Save FAISS index to cache file"""
    try:
        faiss.write_index(index, str(cache_file))
        logger.info(f"FAISS index saved to {cache_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving FAISS index to {cache_file}: {e}")
        return False

def load_faiss_index(cache_file: Path) -> faiss.Index:
    """Load FAISS index from cache file"""
    try:
        if cache_file.exists():
            index = faiss.read_index(str(cache_file))
            logger.info(f"FAISS index loaded from {cache_file}")
            return index
        return None
    except Exception as e:
        logger.error(f"Error loading FAISS index from {cache_file}: {e}")
        return None

def load_legal_data():
    """Load and preprocess legal documents using helper script"""
    global dataset, sentences, sentence_sources, sentence_docs

    try:
        logger.info("Loading legal data with preprocessing...")

        if DATASET_DIR.exists():
            logger.info(f"Loading dataset from {DATASET_DIR} ...")
            dataset = load_from_disk(str(DATASET_DIR))
        else:
            logger.info("Prebuilt dataset not found; creating new one...")
            dataset = create_huggingface_dataset(
                data_dirs=DATA_DIRECTORIES,
                output_dir=str(DATASET_DIR),
                push_to_hub=False,
                max_workers=os.cpu_count(),
            )

        if dataset is None:
            logger.error("Dataset creation failed")
            return False

        # Extract sentences from dataset
        sentences.clear()
        sentence_sources.clear()
        sentence_docs.clear()

        for item in dataset:
            if 'sentences' in item and isinstance(item['sentences'], list):
                for sent in item['sentences']:
                    if sent and sent.strip():
                        sentences.append(sent.strip())
                        sentence_sources.append(item.get('document_type', ''))
                        sentence_docs.append(item)

        logger.info(
            f"Extracted {len(sentences)} sentences from {len(dataset)} documents"
        )
        return True

    except Exception as e:
        logger.error(f"Error loading legal data: {e}")
        return False

def initialize_tfidf():
    """Initialize TF-IDF vectorizer and matrix with caching"""
    global tfidf_matrix, vectorizer
    
    try:
        # Generate hash for current data
        data_hash = get_data_hash(sentences)
        cache_files = get_cache_files(data_hash)
        
        # Try to load from cache
        cached_vectorizer = load_cache(cache_files['vectorizer'])
        cached_matrix = load_cache(cache_files['tfidf_matrix'])
        
        if cached_vectorizer is not None and cached_matrix is not None:
            logger.info("Loading TF-IDF from cache...")
            vectorizer = cached_vectorizer
            tfidf_matrix = cached_matrix
            logger.info("TF-IDF loaded from cache successfully")
            return True
        
        # Create new TF-IDF if cache not available
        logger.info("Creating new TF-IDF (cache not found)...")
        vectorizer = TfidfVectorizer(max_features=10000)
        tfidf_matrix = vectorizer.fit_transform(sentences)
        
        # Save to cache
        save_cache(vectorizer, cache_files['vectorizer'])
        save_cache(tfidf_matrix, cache_files['tfidf_matrix'])
        
        logger.info("TF-IDF initialization completed and cached")
        return True
    except Exception as e:
        logger.error(f"Error initializing TF-IDF: {e}")
        return False

def initialize_embeddings():
    """Initialize sentence embeddings with caching"""
    global embedding_model, sentence_embeddings
    
    try:
        # Generate hash for current data
        data_hash = get_data_hash(sentences)
        cache_files = get_cache_files(data_hash)
        
        # Try to load from cache
        cached_embeddings = load_cache(cache_files['embeddings'])
        
        if cached_embeddings is not None:
            logger.info("Loading sentence embeddings from cache...")
            sentence_embeddings = cached_embeddings
            # Still need to load the model for new queries
            embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
            logger.info("Sentence embeddings loaded from cache successfully")
            return True
        
        # Create new embeddings if cache not available
        logger.info("Creating new sentence embeddings (cache not found)...")
        embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        sentence_embeddings = embedding_model.encode(sentences, convert_to_numpy=True)
        
        # Save to cache
        save_cache(sentence_embeddings, cache_files['embeddings'])
        
        logger.info("Sentence embeddings initialization completed and cached")
        return True
    except Exception as e:
        logger.error(f"Error initializing embeddings: {e}")
        return False

def initialize_faiss():
    """Initialize FAISS index with caching"""
    global faiss_index, sentence_embeddings
    
    try:
        if sentence_embeddings is None:
            logger.error("Sentence embeddings not available for FAISS")
            return False
        
        # Generate hash for current data
        data_hash = get_data_hash(sentences)
        cache_files = get_cache_files(data_hash)
        
        # Try to load from cache
        cached_index = load_faiss_index(cache_files['faiss_index'])
        
        if cached_index is not None:
            logger.info("Loading FAISS index from cache...")
            faiss_index = cached_index
            logger.info("FAISS index loaded from cache successfully")
            return True
        
        # Create new FAISS index if cache not available
        logger.info("Creating new FAISS index (cache not found)...")
        
        # Get embedding dimension
        embedding_dim = sentence_embeddings.shape[1]
        
        # Create FAISS index (using IndexFlatIP for inner product/cosine similarity)
        faiss_index = faiss.IndexFlatIP(embedding_dim)
        
        # Normalize embeddings for cosine similarity
        normalized_embeddings = sentence_embeddings.copy()
        faiss.normalize_L2(normalized_embeddings)
        
        # Add embeddings to index
        faiss_index.add(normalized_embeddings.astype('float32'))
        
        # Save to cache
        save_faiss_index(faiss_index, cache_files['faiss_index'])
        
        logger.info(f"FAISS index initialization completed with {faiss_index.ntotal} vectors")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing FAISS: {e}")
        return False

def retrieve_context_tfidf(query: str, top_k: int = 5) -> List[RetrievalResult]:
    """Retrieve context using TF-IDF"""
    if vectorizer is None or tfidf_matrix is None:
        return []
    
    try:
        query_vec = vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for i in top_indices:
            if similarities[i] > 0:  # Only include non-zero similarities
                results.append(RetrievalResult(
                    sentence=sentences[i],
                    source=sentence_sources[i],
                    score=float(similarities[i]),
                    document=sentence_docs[i]  # 문서 전체 반환
                ))
        
        return results
    except Exception as e:
        logger.error(f"Error in TF-IDF retrieval: {e}")
        return []

def retrieve_context_embedding(query: str, top_k: int = 5) -> List[RetrievalResult]:
    """Retrieve context using sentence embeddings (legacy method)"""
    if embedding_model is None or sentence_embeddings is None:
        return []
    
    try:
        query_emb = embedding_model.encode([query], convert_to_numpy=True)
        similarities = cosine_similarity(query_emb, sentence_embeddings).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for i in top_indices:
            if similarities[i] > 0:  # Only include non-zero similarities
                results.append(RetrievalResult(
                    sentence=sentences[i],
                    source=sentence_sources[i],
                    score=float(similarities[i]),
                    document=sentence_docs[i]  # 문서 전체 반환
                ))
        
        return results
    except Exception as e:
        logger.error(f"Error in embedding retrieval: {e}")
        return []

def retrieve_context_faiss(query: str, top_k: int = 5) -> List[RetrievalResult]:
    """Retrieve context using FAISS index (faster than regular embedding search)"""
    if embedding_model is None or faiss_index is None:
        return []
    
    try:
        # Encode query
        query_emb = embedding_model.encode([query], convert_to_numpy=True)
        
        # Normalize query embedding for cosine similarity
        faiss.normalize_L2(query_emb)
        
        # Search in FAISS index
        scores, indices = faiss_index.search(query_emb.astype('float32'), top_k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx != -1 and score > 0:  # Valid index and positive score
                results.append(RetrievalResult(
                    sentence=sentences[idx],
                    source=sentence_sources[idx],
                    score=float(score),
                    document=sentence_docs[idx]  # 문서 전체 반환
                ))
        
        return results
    except Exception as e:
        logger.error(f"Error in FAISS retrieval: {e}")
        return []

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting Legal RAG API...")
    
    # Load data
    if not load_legal_data():
        logger.error("Failed to load legal data")
        return
    
    if not sentences:
        logger.error("No sentences loaded")
        return
    
    # Initialize TF-IDF
    if not initialize_tfidf():
        logger.error("Failed to initialize TF-IDF")
    
    # Initialize embeddings
    if not initialize_embeddings():
        logger.error("Failed to initialize embeddings")
    
    # Initialize FAISS
    if not initialize_faiss():
        logger.error("Failed to initialize FAISS")
    
    logger.info("Legal RAG API startup completed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Legal RAG API",
        "status": "running",
        "total_sentences": len(sentences),
        "total_documents": len(dataset) if dataset else 0,
        "document_type_counts": Counter(dataset["document_type"]) if dataset and "document_type" in dataset.column_names else {},
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "data_loaded": len(sentences) > 0,
        "tfidf_ready": tfidf_matrix is not None,
        "embeddings_ready": sentence_embeddings is not None,
        "faiss_ready": faiss_index is not None,
        "faiss_total_vectors": faiss_index.ntotal if faiss_index is not None else 0
    }

@app.post("/search", response_model=QueryResponse)
async def search_documents(request: QueryRequest):
    """Search legal documents using RAG"""
    if not sentences:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    response = QueryResponse(query=request.query)
    
    try:
        if request.method in ["tfidf", "both"]:
            if tfidf_matrix is not None:
                response.tfidf_results = retrieve_context_tfidf(request.query, request.top_k)
            else:
                logger.warning("TF-IDF not available")
        
        if request.method in ["embedding", "both"]:
            if sentence_embeddings is not None:
                response.embedding_results = retrieve_context_embedding(request.query, request.top_k)
            else:
                logger.warning("Embeddings not available")
        
        if request.method in ["faiss", "both"]:
            if faiss_index is not None:
                response.faiss_results = retrieve_context_faiss(request.query, request.top_k)
            else:
                logger.warning("FAISS index not available")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/stats")
async def get_stats():
    """Get statistics about the loaded data"""
    if not dataset:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    stats = {
        "total_documents": len(dataset),
        "sample_fields": list(dataset.features.keys()) if len(dataset) > 0 else [],
    }
    if "document_type" in dataset.column_names:
        stats["document_type_counts"] = Counter(dataset["document_type"])
    
    # Get cache info
    data_hash = get_data_hash(sentences) if sentences else "no_data"
    cache_files = get_cache_files(data_hash)
    cache_info = {}
    for cache_type, cache_path in cache_files.items():
        cache_info[cache_type] = {
            "exists": cache_path.exists(),
            "size_mb": round(cache_path.stat().st_size / (1024*1024), 2) if cache_path.exists() else 0
        }
    
    return {
        "total_sentences": len(sentences),
        "document_types": stats,
        "models_ready": {
            "tfidf": tfidf_matrix is not None,
            "embeddings": sentence_embeddings is not None,
            "faiss": faiss_index is not None,
            "faiss_total_vectors": faiss_index.ntotal if faiss_index is not None else 0
        },
        "cache_info": {
            "data_hash": data_hash,
            "cache_files": cache_info,
            "total_cache_size_mb": sum(info["size_mb"] for info in cache_info.values())
        }
    }

@app.delete("/cache")
async def clear_cache():
    """Clear all cache files"""
    try:
        deleted_files = []
        total_size = 0
        
        for cache_file in CACHE_DIR.glob("*.pkl"):
            if cache_file.exists():
                size = cache_file.stat().st_size
                cache_file.unlink()
                deleted_files.append(cache_file.name)
                total_size += size
        
        return {
            "message": "Cache cleared successfully",
            "deleted_files": deleted_files,
            "freed_space_mb": round(total_size / (1024*1024), 2)
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.post("/reload")
async def reload_data():
    """Reload data and reinitialize models (will use cache if available)"""
    global dataset, sentences, sentence_sources, tfidf_matrix, vectorizer, embedding_model, sentence_embeddings, faiss_index
    
    try:
        logger.info("Reloading data...")
        
        # Clear current data
        dataset = None
        sentences.clear()
        sentence_sources.clear()
        sentence_docs.clear()
        tfidf_matrix = None
        vectorizer = None
        embedding_model = None
        sentence_embeddings = None
        faiss_index = None
        
        # Reload everything
        if not load_legal_data():
            raise HTTPException(status_code=500, detail="Failed to load legal data")
        
        if not sentences:
            raise HTTPException(status_code=500, detail="No sentences loaded")
        
        # Initialize models (will use cache if available)
        tfidf_success = initialize_tfidf()
        embedding_success = initialize_embeddings()
        faiss_success = initialize_faiss()
        
        return {
            "message": "Data reloaded successfully",
            "total_sentences": len(sentences),
            "tfidf_initialized": tfidf_success,
            "embeddings_initialized": embedding_success,
            "faiss_initialized": faiss_success,
            "total_documents": len(dataset) if dataset else 0,
            "document_type_counts": Counter(dataset["document_type"]) if dataset and "document_type" in dataset.column_names else {},
        }
        
    except Exception as e:
        logger.error(f"Error reloading data: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload data")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)