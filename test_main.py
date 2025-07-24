import sys
import types
import json
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

# Create dummy sentence_transformers module
import numpy as np

class DummySentenceTransformer:
    def __init__(self, name):
        self.name = name

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False, batch_size=None):
        arr = np.array([[0.1, 0.1, 0.1] for _ in texts])
        return arr if convert_to_numpy else arr.tolist()

dummy_module = types.SimpleNamespace(SentenceTransformer=DummySentenceTransformer)
sys.modules['sentence_transformers'] = dummy_module

import main

@pytest.mark.asyncio
async def test_initialize_embeddings_sets_model():
    main.embedding_model = None
    result = await main.initialize_embeddings()
    assert result is True
    assert isinstance(main.embedding_model, DummySentenceTransformer)

@pytest.mark.asyncio
async def test_retrieve_context_vector(monkeypatch):
    main.embedding_model = DummySentenceTransformer('test')

    rows = [
        {
            'sentence': 'example sentence',
            'source': 'src',
            'document': json.dumps({'id': 1}),
            'similarity_score': 0.9,
        }
    ]

    class DummyConn:
        async def fetch(self, *args, **kwargs):
            return rows

    class DummyAcquire:
        async def __aenter__(self):
            return DummyConn()
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class DummyPool:
        def acquire(self):
            return DummyAcquire()

    async def dummy_register_vector(conn):
        pass

    monkeypatch.setattr(main, 'db_pool', DummyPool())
    monkeypatch.setattr(main, 'register_vector', dummy_register_vector)

    results = await main.retrieve_context_vector('query', top_k=1)
    assert len(results) == 1
    res = results[0]
    assert res.sentence == 'example sentence'
    assert res.source == 'src'
    assert pytest.approx(res.score, rel=1e-3) == 0.9

@pytest.mark.asyncio
async def test_retrieve_context_tfidf(monkeypatch):
    # prepare tfidf vectors
    sentences = ['hello world', 'hi there']
    vectorizer = TfidfVectorizer(max_features=10000)
    mat = vectorizer.fit_transform(sentences)
    vectors = [json.dumps(mat[i].toarray().tolist()[0]) for i in range(mat.shape[0])]

    rows = [
        {
            'id': 1,
            'sentence': sentences[0],
            'source': 'A',
            'document': json.dumps({'id': 1}),
            'tfidf_vector': vectors[0],
        },
        {
            'id': 2,
            'sentence': sentences[1],
            'source': 'B',
            'document': json.dumps({'id': 2}),
            'tfidf_vector': vectors[1],
        },
    ]

    class DummyConn:
        async def fetch(self, *args, **kwargs):
            return rows
    class DummyAcquire:
        async def __aenter__(self):
            return DummyConn()
        async def __aexit__(self, exc_type, exc, tb):
            pass
    class DummyPool:
        def acquire(self):
            return DummyAcquire()

    monkeypatch.setattr(main, 'db_pool', DummyPool())

    results = await main.retrieve_context_tfidf('hello', top_k=1)
    assert len(results) == 1
    res = results[0]
    assert res.source in {'A', 'B'}
    assert isinstance(res.score, float)
