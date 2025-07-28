"""
Data loader and processor for legal documents
"""
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter
from datasets import Dataset, load_from_disk
import logging

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
    
    def load_data(self) -> bool:
        """Load and preprocess legal documents"""
        try:
            logger.info("Loading legal data...")
            start_time = time.time()
            
            # Check if preprocessed dataset exists
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
            
            # Extract sentences and metadata
            success = self._extract_sentences()
            if not success:
                return False
            
            load_time = time.time() - start_time
            logger.info(f"Data loaded successfully in {load_time:.2f} seconds")
            logger.info(f"Total documents: {len(self.dataset)}")
            logger.info(f"Total sentences: {len(self.sentences)}")
            
            # Log document type distribution
            if "document_type" in self.dataset.column_names:
                type_counts = Counter(self.dataset["document_type"])
                logger.info(f"Document types: {dict(type_counts)}")
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading legal data: {e}")
            return False
    
    def _extract_sentences(self) -> bool:
        """Extract sentences from dataset with proper error handling"""
        try:
            self.sentences.clear()
            self.sources.clear()
            self.documents.clear()
            
            logger.info("Extracting sentences from dataset...")
            
            for idx, item in enumerate(self.dataset):
                try:
                    # Validate item structure
                    if not isinstance(item, dict):
                        logger.warning(f"Item {idx} is not a dictionary, skipping")
                        continue
                    
                    # Extract sentences
                    sentences = item.get('sentences', [])
                    if not isinstance(sentences, list):
                        logger.warning(f"Item {idx} has invalid sentences field, skipping")
                        continue
                    
                    # Get document type with fallback
                    doc_type = item.get('document_type', '').strip()
                    if not doc_type:
                        logger.warning(f"Item {idx} missing document_type, using 'UNKNOWN'")
                        doc_type = 'UNKNOWN'
                    
                    # Process each sentence
                    valid_sentences = 0
                    for sent in sentences:
                        if sent and isinstance(sent, str) and sent.strip():
                            clean_sent = sent.strip()
                            if len(clean_sent) > 10:  # Filter very short sentences
                                self.sentences.append(clean_sent)
                                self.sources.append(doc_type)
                                self.documents.append(item)
                                valid_sentences += 1
                    
                    if valid_sentences == 0:
                        logger.warning(f"Item {idx} has no valid sentences")
                        
                except Exception as e:
                    logger.error(f"Error processing item {idx}: {e}")
                    continue
            
            if not self.sentences:
                logger.error("No valid sentences extracted from dataset")
                return False
            
            logger.info(f"Successfully extracted {len(self.sentences)} sentences")
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
            "avg_sentences_per_doc": len(self.sentences) / len(self.dataset) if self.dataset and len(self.dataset) > 0 else 0,
        }
        
        # Document type distribution
        if self.dataset and "document_type" in self.dataset.column_names:
            stats["document_type_counts"] = dict(Counter(self.dataset["document_type"]))
        
        # Source distribution (for sentences)
        if self.sources:
            stats["source_distribution"] = dict(Counter(self.sources))
        
        # Sample data structure
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
