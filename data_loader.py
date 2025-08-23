"""
Compatibility layer for DataLoader.

Provides legacy methods used by tests while delegating to the shared
implementation in `packages.legal_tools.ingest.data_loader`.
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple
from pathlib import Path
import logging

try:  # Allow tests to patch `data_loader.datasets.load_dataset`
    import datasets  # type: ignore
except Exception:  # pragma: no cover
    class _Dummy:  # minimal placeholder; tests patch load_dataset
        pass

    datasets = _Dummy()  # type: ignore

from packages.legal_tools.ingest.data_loader import DataLoader as _SharedDataLoader

logger = logging.getLogger(__name__)


class DataLoader(_SharedDataLoader):
    """Legacy-compatible DataLoader wrapper."""

    def load_from_dataset(self, name: str) -> bool:
        """Load simple dataset via datasets.load_dataset(name) for unit tests.

        Expects each item to have keys: `content` and `source`.
        """
        try:
            loader = getattr(datasets, "load_dataset")  # patched in tests
            ds = loader(name)
            # Prepare containers
            self.sentences = []
            self.sources = []
            self.documents = []

            for item in ds:
                content = item.get("content")
                source = item.get("source")
                if isinstance(content, str) and isinstance(source, str):
                    self.sentences.append(content)
                    self.sources.append(source)
                    self.documents.append(item)

            self.is_loaded = True
            return True
        except Exception as e:  # pragma: no cover
            logger.debug(f"load_from_dataset failed: {e}")
            self.is_loaded = False
            return False

    def get_data(self) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        """Return data; legacy behavior returns empty lists if not loaded."""
        if not self.is_loaded:
            return [], [], []
        return super().get_data()

    def get_stats(self) -> Dict[str, Any]:
        """Compute minimal stats for legacy tests when loaded from simple dataset."""
        if not self.is_loaded:
            return {"error": "Data not loaded"}
        # Document type counts derived from `sources` when simple dataset used
        from collections import Counter

        return {
            "total_documents": len(self.documents),
            "total_sentences": len(self.sentences),
            "document_type_counts": dict(Counter(self.sources)),
        }


__all__ = ["DataLoader"]
