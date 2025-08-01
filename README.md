# Legal RAG API v2.0

A high-performance FastAPI-based Retrieval-Augmented Generation (RAG) system for Korean legal documents with improved architecture, comprehensive testing, and intelligent caching.

## 🚀 Features

- **Multiple Retrieval Methods**: TF-IDF, sentence embeddings, and FAISS index
- **Korean Legal Documents**: Supports 판결문, 법령, 심결례, 유권해석
- **High Performance**: FAISS-based fast similarity search
- **Smart Caching**: Automatic caching of models and embeddings
- **RESTful API**: Easy-to-use HTTP endpoints with comprehensive validation
- **Modular Architecture**: Clean separation of concerns with dependency injection
- **Configuration Management**: Environment-based configuration with validation
- **Comprehensive Logging**: Detailed logging with configurable levels
- **Advanced Testing**: Unit tests, integration tests, performance tests, and stress testing
- **UV Package Management**: Ultra-fast dependency management with modern Python tooling

## 📋 Requirements

- Python 3.10+
- [UV](https://docs.astral.sh/uv/) (Ultra-fast Python package manager)
- CUDA (optional, for GPU acceleration)
- 8GB+ RAM (recommended for large datasets)

## 🛠️ Installation

### 1. Install UV (if not already installed)

**Windows:**
```bash
winget install --id=astral-sh.uv
```

**macOS:**
```bash
brew install uv
```

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd law

# Setup environment and install dependencies
python manage.py setup
python manage.py install

# For GPU support (optional)
python manage.py install --gpu

# For development (optional)
python manage.py install --dev
```

## 🎯 Quick Start

### Start the API Server

```bash
# Using the management script (recommended)
python manage.py start

# With custom host/port
python manage.py start --host 127.0.0.1 --port 8080

# Without auto-reload
python manage.py start --no-reload
```

The API will be available at `http://localhost:8000`

### Check API Health

```bash
python manage.py health
```

### Run Tests

```bash
# Run all tests
python manage.py test

# Run specific test types
uv run python -m pytest tests/ -m unit           # Unit tests only
uv run python -m pytest tests/ -m integration    # Integration tests only
uv run python -m pytest tests/ -m performance    # Performance tests only
uv run python -m pytest tests/ -m stress         # Stress tests only

# Run tests with coverage
uv run python -m pytest tests/ --cov=. --cov-report=html

# Run enhanced test suite
./run_enhanced_tests.sh --all --coverage --html
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

The `manage.py` script provides convenient UV-powered commands:

```bash
# Setup and Installation
python manage.py setup                    # Setup development environment
python manage.py install                  # Install dependencies
python manage.py install --gpu            # Install with GPU support
python manage.py install --dev            # Install development dependencies

# Server Management
python manage.py start                    # Start server
python manage.py start --host 0.0.0.0     # Custom host
python manage.py start --port 8080        # Custom port
python manage.py start --no-reload        # Disable auto-reload

# Development Tools
python manage.py test                     # Run basic tests
python manage.py health                   # Check API health
python manage.py format                   # Format code (black + isort)
python manage.py lint                     # Lint code (flake8 + mypy)

# Enhanced Testing (UV-based)
uv run python -m pytest tests/            # Run all tests
uv run python -m pytest tests/ -m unit    # Unit tests only
uv run python -m pytest tests/ -m integration  # Integration tests
uv run python -m pytest tests/ -m performance  # Performance tests
uv run python -m pytest tests/ -m stress       # Stress tests
uv run python -m pytest tests/ --cov=.         # With coverage
./run_enhanced_tests.sh --all --coverage       # Enhanced test runner

# Data Management
python manage.py clear-cache              # Clear application cache
python manage.py reload                   # Reload data and models
```

## ⚡ Why UV?

UV is an extremely fast Python package installer and resolver, written in Rust. Benefits include:

- **🚀 Speed**: 10-100x faster than pip
- **🔒 Reliability**: More consistent dependency resolution
- **📦 Better Caching**: Efficient package caching
- **🛡️ Security**: Better security features
- **⚙️ Modern**: Built for modern Python development

### UV vs Traditional Tools

| Feature | UV | pip | Poetry |
|---------|----|----|---------|
| Install Speed | ⚡ Ultra Fast | 🐌 Slow | 🐢 Moderate |
| Dependency Resolution | ✅ Excellent | ❌ Basic | ✅ Good |
| Virtual Environments | ✅ Built-in | ❌ Manual | ✅ Built-in |
| Lock Files | ✅ Yes | ❌ No | ✅ Yes |
| Memory Usage | ✅ Low | ✅ Low | ❌ High |

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
- **`config.py`**: Configuration management with Pydantic validation
- **`models.py`**: Pydantic models for API request/response validation
- **`data_loader.py`**: Data loading and preprocessing from HuggingFace datasets
- **`cache_manager.py`**: Intelligent caching utilities with hash-based keys
- **`retrievers.py`**: Search algorithms (TF-IDF, Embedding, FAISS)

### Testing Infrastructure

- **`tests/test_unit.py`**: Unit tests for individual components
- **`tests/test_comprehensive.py`**: Integration tests
- **`tests/test_e2e.py`**: End-to-end workflow tests
- **`tests/test_performance.py`**: Performance benchmarking
- **`tests/test_stress.py`**: Load testing and stress tests
- **`tests/test_exceptions.py`**: Exception handling and edge cases
- **`tests/test_utils.py`**: Testing utilities and helpers
- **`run_enhanced_tests.sh`**: Advanced test runner with UV integration
- **`pytest.ini`**: Test configuration and markers

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

The project includes a comprehensive test suite with multiple testing strategies:

### Test Types

- **Unit Tests** (`tests/test_unit.py`): Individual component testing
- **Integration Tests** (`tests/test_comprehensive.py`): Component interaction testing  
- **End-to-End Tests** (`tests/test_e2e.py`): Complete workflow testing
- **Performance Tests** (`tests/test_performance.py`): Performance benchmarking
- **Stress Tests** (`tests/test_stress.py`): Load testing and resource limits
- **Exception Tests** (`tests/test_exceptions.py`): Error handling and edge cases

### Running Tests

```bash
# Quick test run
python manage.py test

# Comprehensive testing with UV
uv run python -m pytest tests/ -v

# Specific test categories
uv run python -m pytest tests/ -m unit           # Unit tests
uv run python -m pytest tests/ -m integration    # Integration tests
uv run python -m pytest tests/ -m performance    # Performance tests
uv run python -m pytest tests/ -m stress         # Stress tests

# Coverage reporting
uv run python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# Enhanced test runner with detailed reporting
chmod +x run_enhanced_tests.sh
./run_enhanced_tests.sh --all --coverage --html
```

### Test Configuration

Tests are configured via `pytest.ini` with markers for different test types:
- `unit`: Fast unit tests
- `integration`: Integration tests requiring running server
- `performance`: Performance benchmarking tests  
- `stress`: Resource-intensive stress tests
- `e2e`: End-to-end workflow tests
- `slow`: Long-running tests
- `critical`: Critical tests that must pass

### Test Reports

After running tests with coverage, check:
- **HTML Report**: `htmlcov/index.html`
- **Terminal**: Coverage summary in terminal output
- **CI/CD**: XML reports in `test_reports/` directory

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

- **Modular Architecture**: Clean separation of concerns with dependency injection
- **Improved Caching**: Hash-based intelligent caching with automatic invalidation
- **Better Error Handling**: Comprehensive error handling and validation with custom exceptions
- **Performance Monitoring**: Request timing and performance metrics with detailed logging
- **Configuration Management**: Environment-based configuration with Pydantic validation
- **Management Scripts**: Convenient UV-powered management commands
- **Enhanced API**: Better request/response models with comprehensive validation
- **Advanced Testing Suite**: Multi-tier testing with unit, integration, performance, and stress tests
- **UV Package Management**: Ultra-fast dependency management and virtual environment handling
- **Test Coverage**: Comprehensive test coverage reporting with HTML output
- **CI/CD Ready**: Enhanced testing infrastructure ready for continuous integration

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

**3. Test Failures**
- Run tests to identify issues: `uv run python -m pytest tests/ -v`
- Check specific test categories: `uv run python -m pytest tests/ -m unit`
- Review test logs and coverage reports in `htmlcov/`

**4. Performance Issues**
- Run performance tests: `uv run python -m pytest tests/ -m performance`
- Monitor resource usage during stress tests
- Check cache hit rates and model initialization times

**5. Cache Issues**
- Clear cache: `python manage.py clear-cache`
- Disable cache: Set `ENABLE_CACHE=false` in `.env`
- Check disk space for cache directory

For more help, check the logs in `legal_rag.log` or create an issue.