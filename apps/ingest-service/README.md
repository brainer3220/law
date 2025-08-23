# ingest-service

Ingestion, OCR, chunking, metadata/embedding pipeline.

- Source loaders and cache logic will migrate from `data_loader.py` and `cache_manager.py`.
- Output targets: Postgres (documents/chunks), object storage, and pgvector embeddings.

