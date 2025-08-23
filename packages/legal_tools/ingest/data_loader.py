"""
Data loader and processor for legal documents (shared).
"""
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter
from datasets import Dataset, load_from_disk
import logging
from tqdm import tqdm

from scripts.full_data_to_datasets import create_huggingface_dataset
from config import settings

logger = logging.getLogger(__name__)


class DataLoader:
    """Handles loading and preprocessing of legal documents"""

    def __init__(self):
        self.dataset: Dataset = None
        self.sentences: List[str] = []
        self.sources: List[str] = []
        self.documents: List[Dict[str, Any]] = []
        self.is_loaded = False
        self.max_sentences = getattr(settings, "MAX_SENTENCES_LIMIT", None)

    def load_data(self) -> bool:
        """Load and preprocess legal documents"""
        try:
            logger.info("Loading legal data...")
            start_time = time.time()

            if settings.DATASET_DIR.exists():
                logger.info(f"Loading dataset from {settings.DATASET_DIR}")
                self.dataset = load_from_disk(str(settings.DATASET_DIR))
            else:
                logger.info("Preprocessed dataset not found, creating new one...")
                self.dataset = create_huggingface_dataset(
                    data_dirs=settings.DATA_DIRECTORIES,
                    output_dir=str(settings.DATASET_DIR),
                    push_to_hub=False,
                    max_workers=settings.MAX_WORKERS or os.cpu_count(),
                )

            if self.dataset is None:
                logger.error("Dataset creation failed")
                return False

            success = self._extract_sentences()
            if not success:
                return False

            load_time = time.time() - start_time
            logger.info(f"Data loaded successfully in {load_time:.2f} seconds")
            logger.info(f"Total documents: {len(self.dataset)}")
            logger.info(f"Total sentences: {len(self.sentences)}")

            if "document_type" in self.dataset.column_names:
                type_counts = Counter(self.dataset["document_type"])
                logger.info(f"Document types: {dict(type_counts)}")

            self.is_loaded = True
            return True

        except Exception as e:
            logger.error(f"Error loading legal data: {e}")
            return False

    def _extract_sentences(self) -> bool:
        """Extract sentences from dataset with proper error handling and optimization"""
        try:
            self.sentences.clear()
            self.sources.clear()
            self.documents.clear()

            logger.info("Extracting sentences from dataset...")

            dataset_size = len(self.dataset)
            logger.info(f"Processing {dataset_size} documents...")

            batch_size = getattr(settings, "DATA_BATCH_SIZE", 1000)
            total_sentences = 0

            for batch_start in tqdm(range(0, dataset_size, batch_size), desc="Processing documents"):
                batch_end = min(batch_start + batch_size, dataset_size)

                for idx in range(batch_start, batch_end):
                    try:
                        item = self.dataset[idx]
                        if not isinstance(item, dict):
                            continue

                        sentences = item.get("sentences", [])
                        if not isinstance(sentences, list):
                            continue

                        doc_type = item.get("document_type", "").strip() or "UNKNOWN"

                        valid_sentences_in_doc = 0
                        for sent in sentences:
                            if sent and isinstance(sent, str) and sent.strip():
                                clean_sent = sent.strip()
                                if len(clean_sent) > 10:
                                    self.sentences.append(clean_sent)
                                    self.sources.append(doc_type)
                                    self.documents.append(item)
                                    valid_sentences_in_doc += 1
                                    total_sentences += 1

                                    if self.max_sentences and total_sentences >= self.max_sentences:
                                        logger.info(
                                            f"Reached sentence limit of {self.max_sentences}, stopping extraction"
                                        )
                                        break

                        if self.max_sentences and total_sentences >= self.max_sentences:
                            break

                    except Exception as e:
                        logger.debug(f"Error processing item {idx}: {e}")
                        continue

                if self.max_sentences and total_sentences >= self.max_sentences:
                    break

                if (batch_start // batch_size) % 5 == 0:
                    logger.debug(f"Processed {batch_end} documents, extracted {total_sentences} sentences")

            if not self.sentences:
                logger.error("No valid sentences extracted from dataset")
                return False

            logger.info(
                f"Successfully extracted {len(self.sentences)} sentences from {dataset_size} documents"
            )
            return True

        except Exception as e:
            logger.error(f"Error extracting sentences: {e}")
            return False

    def get_data(self) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        """Get the loaded data"""
        if not self.is_loaded:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        return self.sentences, self.sources, self.documents

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded data"""
        if not self.is_loaded:
            return {"error": "Data not loaded"}

        stats = {
            "total_documents": len(self.dataset) if self.dataset else 0,
            "total_sentences": len(self.sentences),
            "avg_sentences_per_doc":
                len(self.sentences) / len(self.dataset) if self.dataset and len(self.dataset) > 0 else 0,
        }

        if self.dataset and "document_type" in self.dataset.column_names:
            stats["document_type_counts"] = dict(Counter(self.dataset["document_type"]))

        if self.sources:
            stats["source_distribution"] = dict(Counter(self.sources))

        if self.dataset and len(self.dataset) > 0:
            stats["sample_fields"] = list(self.dataset.features.keys())

        return stats

    def reload(self) -> bool:
        """Reload data from scratch"""
        logger.info("Reloading data...")
        self.is_loaded = False
        self.dataset = None
        self.sentences.clear()
        self.sources.clear()
        self.documents.clear()
        return self.load_data()

