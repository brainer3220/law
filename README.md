# Legal RAG API

A FastAPI-based Retrieval-Augmented Generation (RAG) system for Korean legal documents.

## Features

- **Dual Retrieval Methods**: TF-IDF and sentence embedding-based retrieval
- **Korean Legal Documents**: Supports 판결문, 법령, 심결례, 유권해석
- **RESTful API**: Easy-to-use HTTP endpoints
- **Real-time Search**: Fast document retrieval and ranking

## Installation

1. Install dependencies:
```bash
uv sync
```

2. Activate virtual environment:
```bash
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

## Usage

### Start the API Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Search Documents
```bash
POST /search
```

Request body:
```json
{
  "query": "계약 해지에 관한 판례를 알려줘",
  "method": "both",  // "tfidf", "embedding", or "both"
  "top_k": 5
}
```

#### Get Statistics
```bash
GET /stats
```

### Test the API

Run the test script:
```bash
python test_api.py
```

## Example Usage

```python
import requests

# Search query
response = requests.post("http://localhost:8000/search", json={
    "query": "계약 해지에 관한 판례를 알려줘",
    "method": "both",
    "top_k": 5
})

results = response.json()
print(results)
```

## Data Structure

The system expects legal documents in the following structure:
```
Sample/01.원천데이터/01. 민사법/
├── 001. 판결문/
├── 002. 법령/
├── 003. 심결례/
└── 004. 유권해석/
```

Each document should be a JSON file with a `sentences` field containing an array of text sentences.

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation.