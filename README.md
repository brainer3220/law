# Legal RAG API v2.0

A high-performance FastAPI-based Retrieval-Augmented Generation (RAG) system for Korean legal documents with improved architecture and caching.

## 🚀 Features

- **Multiple Retrieval Methods**: TF-IDF, sentence embeddings, and FAISS index
- **Korean Legal Documents**: Supports 판결문, 법령, 심결례, 유권해석
- **High Performance**: FAISS-based fast similarity search
- **Smart Caching**: Automatic caching of models and embeddings
- **RESTful API**: Easy-to-use HTTP endpoints with comprehensive validation
- **Modular Architecture**: Clean separation of concerns
- **Configuration Management**: Environment-based configuration
- **Comprehensive Logging**: Detailed logging with configurable levels

## 📋 Requirements

- Python 3.10+
- CUDA (optional, for GPU acceleration)
- 8GB+ RAM (recommended for large datasets)

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd law
```

2. **Install dependencies**:
```bash
# Using the management script
python manage.py install

# Or manually with pip
pip install -e .
```

3. **Setup environment**:
```bash
python manage.py setup
```

4. **Configure settings** (optional):
   Edit `.env` file to customize settings like API port, model parameters, etc.

## 🎯 Quick Start

### Start the API Server

```bash
# Using the management script (recommended)
python manage.py start

# Or directly
python main.py
```

The API will be available at `http://localhost:8000`

### Check API Health

```bash
python manage.py health
```

### Run Tests

```bash
python manage.py test
```

## 📚 API Documentation

Once the server is running:
- **Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔍 API Endpoints

### Health Check
```http
GET /health
```

### Root Information
```http  
GET /
```

### Search Documents
```http
POST /search
```

**Request Body**:
```json
{
  "query": "계약 해지에 관한 판례를 알려줘",
  "method": "faiss",
  "top_k": 5,
  "min_score": 0.1
}
```

**Available Methods**:
- `tfidf`: TF-IDF based search
- `embedding`: Sentence embedding search  
- `faiss`: Fast similarity search (recommended)
- `both`: Run multiple methods

### Statistics
```http
GET /stats
```

### Cache Management
```http
DELETE /cache    # Clear cache
```

### Data Management
```http
POST /reload     # Reload data and models
```

## 🔧 Management Commands

The `manage.py` script provides convenient commands:

```bash
# Start server
python manage.py start [--host HOST] [--port PORT] [--no-reload]

# Check health
python manage.py health

# Run tests
python manage.py test

# Clear cache
python manage.py clear-cache

# Reload data
python manage.py reload

# Install dependencies
python manage.py install

# Setup environment
python manage.py setup
```

## ⚙️ Configuration

Configure the application using environment variables or `.env` file:

```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Model Settings  
EMBEDDING_MODEL=jhgan/ko-sroberta-multitask
TFIDF_MAX_FEATURES=10000

# Cache Settings
CACHE_DIR=cache
ENABLE_CACHE=true

# Search Settings
DEFAULT_TOP_K=5
MAX_TOP_K=100
MIN_SIMILARITY_SCORE=0.1

# Performance Settings
BATCH_SIZE=32

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=legal_rag.log
```

## 📊 Performance

### Benchmarks (on sample data)
- **FAISS Search**: ~10-50ms per query
- **TF-IDF Search**: ~100-200ms per query  
- **Embedding Search**: ~500-1000ms per query

### Memory Usage
- **Base system**: ~2GB
- **With embeddings**: ~4-6GB
- **Cache storage**: ~1-3GB (depends on dataset size)

## 🏗️ Architecture

### Core Components

- **`main.py`**: FastAPI application and endpoints
- **`config.py`**: Configuration management
- **`models.py`**: Pydantic models for API
- **`data_loader.py`**: Data loading and preprocessing
- **`cache_manager.py`**: Caching utilities
- **`retrievers.py`**: Search algorithms (TF-IDF, Embedding, FAISS)

### Data Flow

1. **Data Loading**: Legal documents → HuggingFace Dataset → Sentences
2. **Model Initialization**: TF-IDF vectorizer, sentence embeddings, FAISS index
3. **Caching**: Models and embeddings cached for fast startup
4. **Search**: Query → Retrieval → Ranking → Results

## 🔄 Caching System

The application uses intelligent caching to improve performance:

- **Automatic**: Models and embeddings are cached automatically
- **Hash-based**: Cache keys based on data content hash
- **Persistent**: Cache survives application restarts
- **Manageable**: Clear cache via API or management commands

## 🧪 Testing

Run the comprehensive test suite:

```bash
python manage.py test
```

The test includes:
- Health checks
- API functionality
- Search performance
- Error handling

## 📝 Example Usage

```python
import requests

# Search for legal documents
response = requests.post("http://localhost:8000/search", json={
    "query": "계약 해지에 관한 판례",
    "method": "faiss",
    "top_k": 5,
    "min_score": 0.2
})

results = response.json()
print(f"Found {results['total_results']} results")

# Display FAISS results
for result in results['faiss_results']:
    print(f"Score: {result['score']:.4f}")
    print(f"Source: {result['source']}")
    print(f"Text: {result['sentence'][:200]}...")
    print("-" * 50)
```

## 🔍 Data Structure

The system expects legal documents in this structure:
```
full_data/Training/01.원천데이터/
├── TS_01. 민사법_001. 판결문/
├── TS_01. 민사법_002. 법령/
├── TS_01. 민사법_003. 심결례/
└── TS_01. 민사법_004. 유권해석/
```

Each document should be a JSON file with:
```json
{
  "sentences": ["문장1", "문장2", ...],
  "document_type": "판결문",
  ...
}
```

## 🚀 What's New in v2.0

- **Modular Architecture**: Clean separation of concerns
- **Improved Caching**: Hash-based intelligent caching  
- **Better Error Handling**: Comprehensive error handling and validation
- **Performance Monitoring**: Request timing and performance metrics
- **Configuration Management**: Environment-based configuration
- **Management Scripts**: Convenient management commands
- **Enhanced API**: Better request/response models with validation
- **Comprehensive Testing**: Improved test suite with performance tests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Troubleshooting

### Common Issues

**1. Out of Memory**
- Reduce `BATCH_SIZE` in configuration
- Use CPU instead of GPU for embeddings
- Clear cache: `python manage.py clear-cache`

**2. Slow Startup**
- First startup is slow (model download/embedding creation)
- Subsequent startups use cache and are faster
- Check logs for progress: `tail -f legal_rag.log`

**3. Connection Errors**
- Check if server is running: `python manage.py health`
- Verify port is available: `netstat -an | grep 8000`
- Check firewall settings

**4. Cache Issues**
- Clear cache: `python manage.py clear-cache`
- Disable cache: Set `ENABLE_CACHE=false` in `.env`
- Check disk space for cache directory

For more help, check the logs in `legal_rag.log` or create an issue.