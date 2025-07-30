# Legal RAG API - AI Coding Agent Instructions

## Project Architecture Overview

This is a Korean Legal Document RAG System built with FastAPI, featuring a sophisticated multi-layer caching architecture and three retrieval methods (TF-IDF, Embeddings, FAISS).

### Core Components & Data Flow

**Singleton Pattern with Caching**: The system uses a `ModelManager` singleton (`model_manager.py`) that provides two-level caching:
- Memory cache for embeddings and models (hash-based keys)
- Disk cache via `CacheManager` for persistent storage across restarts

**Retriever Initialization Chain**: In `main.py`, `initialize_retrievers()` follows this pattern:
1. Load data via `DataLoader` → generate data hash
2. Check disk cache first (pickle files named with data hash)
3. If cache miss, initialize retriever which uses `ModelManager` for embeddings
4. Save results back to disk cache

**Three Retrieval Strategies**: All inherit from `BaseRetriever` in `retrievers.py`:
- `TFIDFRetriever`: Traditional keyword search
- `EmbeddingRetriever`: Semantic search using sentence transformers
- `FAISSRetriever`: High-performance vector search with normalized embeddings

## Development Workflows

### UV Package Manager Commands
```bash
# Primary management script - USE THIS
python manage.py install [--gpu] [--dev]
python manage.py start [--host HOST] [--port PORT]
python manage.py test [unit|integration|performance|e2e|all]
python manage.py health  # Check API status
python manage.py clear-cache  # Clear disk cache

# Direct UV commands (alternative)
uv sync  # Install dependencies
uv run python main.py  # Start server
uv run python -m pytest tests/ -m unit  # Run specific test categories
```

### Test Categories & Markers
- `unit`: Fast, isolated tests (`test_comprehensive.py`)
- `integration`: Requires running server (`-m integration`)
- `performance`: Benchmarking tests (`test_performance.py`)
- `e2e`: Full workflow tests (`test_e2e.py`)

**Critical**: Integration tests require server to be running first!

## Project-Specific Patterns

### Cache Management Pattern
```python
# Always use data hash for cache keys
data_hash = cache_manager.get_data_hash(sentences)
cache_files = cache_manager.get_cache_files(data_hash)

# Check disk cache before creating
if cached_data := cache_manager.load_pickle(cache_files['embeddings']):
    # Load from cache
else:
    # Create new, then save
    cache_manager.save_pickle(new_data, cache_files['embeddings'])
```

### ModelManager Usage Pattern
```python
# Use convenience functions, not direct instantiation
from model_manager import get_embedding_model, get_embeddings

# Automatic caching handled internally
embeddings = get_embeddings(texts, use_cache=True)
model = get_embedding_model("jhgan/ko-sroberta-multitask")
```

### Configuration System
- Environment-based via `pydantic_settings` in `config.py`
- Settings accessed via global `settings` object
- Key paths: `CACHE_DIR`, `DATASET_DIR`, `MAX_SENTENCES_LIMIT`

### Logging Levels
- Large batches (>100 texts): INFO level with "(cache miss)" annotation
- Small batches (≤100 texts): DEBUG level to reduce noise
- Cache hits: INFO for large batches, DEBUG for small

## Common Development Tasks

### Adding New Retrieval Method
1. Inherit from `BaseRetriever` in `retrievers.py`
2. Implement `initialize()` and `search()` methods
3. Add to `initialize_retrievers()` in `main.py` with caching logic
4. Add API endpoint support in `search_documents()`

### Working with Embeddings
- Always use `ModelManager` functions, never instantiate `SentenceTransformer` directly
- Embedding model is Korean-specific: `"jhgan/ko-sroberta-multitask"`
- Use `BATCH_SIZE=32` for processing (configurable in settings)

### Data Loading Patterns
- HuggingFace Datasets integration for Korean legal documents
- Automatic dataset creation if not found in `DATASET_DIR`
- Document types: court_decision, legal_interpretation, administrative_decision, statute

### Performance Considerations
- FAISS search: ~10-50ms (fastest, for real-time)
- TF-IDF search: ~100-200ms (keyword-based)
- Embedding search: ~500-1000ms (semantic, slower)
- Memory usage: 2GB base, 4-6GB with embeddings

## File Structure Significance

- `main.py`: FastAPI app with lifespan management for retriever initialization
- `model_manager.py`: Thread-safe singleton for ML model caching
- `cache_manager.py`: Disk-based caching with hash-based invalidation
- `data_loader.py`: HuggingFace dataset integration with preprocessing
- `retrievers.py`: Pluggable retrieval strategies with common interface
- `manage.py`: UV-based development workflow automation
- `tests/`: Pytest with markers for different test categories

## Integration Points

### API Endpoints Pattern
All follow FastAPI + Pydantic models in `models.py`:
- Request/Response validation
- Comprehensive error handling with HTTPException
- Logging for debugging and monitoring

### External Dependencies
- HuggingFace `datasets` for data management
- `sentence-transformers` for Korean embeddings
- `faiss-cpu/gpu` for vector search
- `uvicorn` ASGI server with hot reload

### Environment Dependencies
- CUDA optional for GPU acceleration
- 8GB+ RAM recommended for full dataset
- Python 3.10+ required (uses newer typing features)
