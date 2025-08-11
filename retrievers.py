"""
Retrieval methods for legal documents
"""
import time
from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import faiss
import logging

from models import RetrievalResult
from config import settings
from model_manager import get_embedding_model, get_embeddings

logger = logging.getLogger(__name__)


class BaseRetriever:
    """Base class for all retrievers"""
    
    def __init__(self, sentences: List[str], sources: List[str], documents: List[dict]):
        self.sentences = sentences
        self.sources = sources
        self.documents = documents
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """Initialize the retriever"""
        raise NotImplementedError
    
    def search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[RetrievalResult]:
        """Search for similar documents"""
        raise NotImplementedError


class TFIDFRetriever(BaseRetriever):
    """TF-IDF based retriever"""
    
    def __init__(self, sentences: List[str], sources: List[str], documents: List[dict]):
        super().__init__(sentences, sources, documents)
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
    
    def initialize(self) -> bool:
        """Initialize TF-IDF vectorizer and matrix"""
        try:
            logger.info("Initializing TF-IDF retriever...")
            self.vectorizer = TfidfVectorizer(
                max_features=settings.TFIDF_MAX_FEATURES,
                ngram_range=(1, 2),  # Use unigrams and bigrams
                min_df=2,  # Ignore terms that appear in less than 2 documents
                max_df=0.95,  # Ignore terms that appear in more than 95% of documents
                stop_words=None  # Keep all words for Korean
            )
            self.tfidf_matrix = self.vectorizer.fit_transform(self.sentences)
            self.is_initialized = True
            logger.info("TF-IDF retriever initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing TF-IDF retriever: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[RetrievalResult]:
        """Search using TF-IDF"""
        if not self.is_initialized:
            logger.warning("TF-IDF retriever not initialized")
            return []
        
        try:
            start_time = time.time()
            query_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            
            # Get top indices with scores above threshold
            scored_indices = [(i, score) for i, score in enumerate(similarities) if score >= min_score]
            scored_indices.sort(key=lambda x: x[1], reverse=True)
            top_indices = scored_indices[:top_k]
            
            results = []
            for rank, (i, score) in enumerate(top_indices, 1):
                results.append(RetrievalResult(
                    sentence=self.sentences[i],
                    source=self.sources[i],
                    score=float(score),
                    document=self.documents[i],
                    rank=rank
                ))
            
            search_time = (time.time() - start_time) * 1000
            logger.debug(f"TF-IDF search completed in {search_time:.2f}ms")
            return results
            
        except Exception as e:
            logger.error(f"Error in TF-IDF search: {e}")
            return []


class EmbeddingRetriever(BaseRetriever):
    """Sentence embedding based retriever"""
    
    def __init__(self, sentences: List[str], sources: List[str], documents: List[dict]):
        super().__init__(sentences, sources, documents)
        self.model: Optional[SentenceTransformer] = None
        self.embeddings = None
    
    def initialize(self) -> bool:
        """Initialize sentence transformer model and embeddings"""
        try:
            logger.info("Initializing embedding retriever...")
            # Use reusable model from ModelManager
            self.model = get_embedding_model(settings.EMBEDDING_MODEL)
            if self.model is None:
                logger.error("Failed to load embedding model from ModelManager")
                return False
            
            # Generate embeddings using ModelManager's caching system
            logger.debug("Generating embeddings...")  # Changed to debug level
            self.embeddings = get_embeddings(
                self.sentences, 
                settings.EMBEDDING_MODEL,
                batch_size=settings.BATCH_SIZE,
                use_cache=True
            )
            
            if self.embeddings is None:
                logger.error("Failed to generate embeddings")
                return False
            
            self.is_initialized = True
            logger.info("Embedding retriever initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing embedding retriever: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[RetrievalResult]:
        """Search using sentence embeddings"""
        if not self.is_initialized:
            logger.warning("Embedding retriever not initialized")
            return []
        
        try:
            start_time = time.time()
            query_emb = self.model.encode([query], convert_to_numpy=True)
            similarities = cosine_similarity(query_emb, self.embeddings).flatten()
            
            # Get top indices with scores above threshold
            scored_indices = [(i, score) for i, score in enumerate(similarities) if score >= min_score]
            scored_indices.sort(key=lambda x: x[1], reverse=True)
            top_indices = scored_indices[:top_k]
            
            results = []
            for rank, (i, score) in enumerate(top_indices, 1):
                results.append(RetrievalResult(
                    sentence=self.sentences[i],
                    source=self.sources[i],
                    score=float(score),
                    document=self.documents[i],
                    rank=rank
                ))
            
            search_time = (time.time() - start_time) * 1000
            logger.debug(f"Embedding search completed in {search_time:.2f}ms")
            return results
            
        except Exception as e:
            logger.error(f"Error in embedding search: {e}")
            return []


class FAISSRetriever(BaseRetriever):
    """FAISS-based fast similarity search retriever"""
    
    def __init__(self, sentences: List[str], sources: List[str], documents: List[dict]):
        super().__init__(sentences, sources, documents)
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.embeddings = None
        # Use L2 distance index when IP is unavailable (older/faiss-lite builds)
        self._use_l2_index: bool = False
    
    def initialize(self) -> bool:
        """Initialize FAISS index"""
        try:
            logger.info("Initializing FAISS retriever...")
            # Use reusable model from ModelManager
            self.model = get_embedding_model(settings.EMBEDDING_MODEL)
            if self.model is None:
                logger.error("Failed to load embedding model from ModelManager")
                return False
            
            # Generate embeddings using ModelManager's caching system
            logger.info("Generating embeddings for FAISS...")
            self.embeddings = get_embeddings(
                self.sentences,
                settings.EMBEDDING_MODEL,
                batch_size=settings.BATCH_SIZE,
                use_cache=True
            )
            
            if self.embeddings is None:
                logger.error("Failed to generate embeddings for FAISS")
                return False
            
            # Create FAISS index (prefer IP; fallback to L2 if IP unavailable)
            embedding_dim = self.embeddings.shape[1]
            if hasattr(faiss, "IndexFlatIP"):
                self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
                self._use_l2_index = False
            elif hasattr(faiss, "IndexFlatL2"):
                logger.warning("FAISS IndexFlatIP not available; falling back to IndexFlatL2")
                self.index = faiss.IndexFlatL2(embedding_dim)
                self._use_l2_index = True
            else:
                logger.error("Neither FAISS IndexFlatIP nor IndexFlatL2 is available in this build")
                return False
            
            # Normalize embeddings for cosine similarity
            normalized_embeddings = self.embeddings.copy()
            faiss.normalize_L2(normalized_embeddings)
            
            # Add to index
            self.index.add(normalized_embeddings.astype('float32'))
            
            self.is_initialized = True
            logger.info(f"FAISS retriever initialized with {self.index.ntotal} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing FAISS retriever: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[RetrievalResult]:
        """Search using FAISS index"""
        if not self.is_initialized:
            logger.warning("FAISS retriever not initialized")
            return []
        
        try:
            start_time = time.time()
            
            # Encode and normalize query
            query_emb = self.model.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(query_emb)
            
            # Search in FAISS index
            raw_scores_or_dists, indices = self.index.search(query_emb.astype('float32'), top_k)
            # Convert distances to cosine similarity if using L2 index
            if self._use_l2_index:
                # For normalized vectors: d^2 = 2(1 - cos), so cos = 1 - d^2/2
                sims = 1.0 - (raw_scores_or_dists[0] / 2.0)
            else:
                sims = raw_scores_or_dists[0]
            
            results = []
            for rank, (score, idx) in enumerate(zip(sims, indices[0]), 1):
                if idx != -1 and score >= min_score:  # Valid index and above threshold
                    results.append(RetrievalResult(
                        sentence=self.sentences[idx],
                        source=self.sources[idx],
                        score=float(score),
                        document=self.documents[idx],
                        rank=rank
                    ))
            
            search_time = (time.time() - start_time) * 1000
            logger.debug(f"FAISS search completed in {search_time:.2f}ms")
            return results
            
        except Exception as e:
            logger.error(f"Error in FAISS search: {e}")
            return []
