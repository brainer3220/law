"""
RAG API service entrypoint.

For now, reuse the root `main.app` to maintain backward compatibility
while the repository transitions to a multi-service layout.
"""

from main import app  # Re-export FastAPI app

__all__ = ["app"]

