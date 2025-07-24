from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from glob import glob
import json
import os
from pathlib import Path
from tqdm.auto import tqdm
from datasets import Dataset, DatasetDict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import asyncio
import asyncpg
from pgvector.asyncpg import register_vector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Legal RAG API", description="Korean Legal Document RAG System")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/legal_rag")

# Global variables for storing data and models
dataset = None
embedding_model = None
db_pool = None

class QueryRequest(BaseModel):
    query: str
    method: str = "vector"  # "tfidf", "vector", or "both"
    top_k: int = 5
    source_filter: Optional[str] = None  # Filter by document source
    min_score: Optional[float] = 0.1  # Minimum similarity score threshold

class RetrievalResult(BaseModel):
    sentence: str
    source: str
    score: float
    document: dict  # 문서 전체 반환

class QueryResponse(BaseModel):
    query: str
    tfidf_results: Optional[List[RetrievalResult]] = None
    vector_results: Optional[List[RetrievalResult]] = None

async def init_database():
    """Initialize database connection and create tables with pgvector 0.8 optimizations"""
    global db_pool
    
    try:
        # Create connection pool with optimized settings
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60,
            server_settings={
                'jit': 'off',  # Disable JIT for better vector performance
                'shared_preload_libraries': 'vector',
                'max_parallel_workers_per_gather': '2'
            }
        )
        
        # Register pgvector types
        async with db_pool.acquire() as conn:
            await register_vector(conn)
            
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create documents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    sentence TEXT NOT NULL,
                    source TEXT NOT NULL,
                    document JSONB NOT NULL,
                    embedding vector(768),
                    tfidf_vector TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Drop old indexes if they exist
            await conn.execute("DROP INDEX IF EXISTS documents_embedding_idx")
            
            # Create HNSW index for better performance (pgvector 0.8 feature)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx 
                ON documents USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """)
            
            # Create additional indexes for filtering
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_source_idx 
                ON documents (source)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_created_at_idx 
                ON documents (created_at)
            """)
            
            # Create partial index for documents with embeddings
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_embedding_not_null_idx 
                ON documents (id) WHERE embedding IS NOT NULL
            """)
            
        logger.info("Database initialized successfully with pgvector 0.8 optimizations")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

async def get_document_count():
    """Get total number of documents in database"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM documents")
            return result
    except Exception as e:
        logger.error(f"Error getting document count: {e}")
        return 0

async def clear_documents():
    """Clear all documents from database"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM documents")
        logger.info("All documents cleared from database")
        return True
    except Exception as e:
        logger.error(f"Error clearing documents: {e}")
        return False

async def load_legal_data():
    """Load legal documents from JSON files and store in PostgreSQL with batch optimization"""
    global dataset, embedding_model
    
    try:
        logger.info("Loading legal data...")
        
        # Check if data already exists in database
        doc_count = await get_document_count()
        if doc_count > 0:
            logger.info(f"Database already contains {doc_count} documents. Skipping data loading.")
            return True
        
        data_type = sorted(glob("full_data/Training/01.원천데이터/*"))
        
        if not data_type:
            logger.warning("No data directories found")
            return False
            
        data_list = sorted([glob(d_type + "/*.json") for d_type in data_type])
        
        dataset_dict = {}
        for i in tqdm(range(len(data_type))):
            key = data_type[i].split()[-1]
            json_files = data_list[i]
            
            if json_files:
                try:
                    dataset_dict[key] = Dataset.from_json(json_files, num_proc=os.cpu_count())
                    logger.info(f"Loaded {len(json_files)} files for {key}")
                except Exception as e:
                    logger.error(f"Error loading {key}: {e}")
                    continue
        
        if not dataset_dict:
            logger.error("No datasets loaded successfully")
            return False
            
        dataset = DatasetDict(dataset_dict)
        
        # Initialize embedding model if not already done
        if embedding_model is None:
            logger.info("Loading embedding model...")
            embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        
        # Process and store documents in database with batch optimization
        logger.info("Processing and storing documents in database...")
        
        BATCH_SIZE = 1000  # Optimized batch size for pgvector 0.8
        
        async with db_pool.acquire() as conn:
            await register_vector(conn)  # Register vector types for this connection
            
            for key in dataset.keys():
                logger.info(f"Processing {key}...")
                
                sentences_batch = []
                sources_batch = []
                documents_batch = []
                
                for item in tqdm(dataset[key], desc=f"Processing {key}"):
                    if 'sentences' in item and isinstance(item['sentences'], list):
                        for sent in item['sentences']:
                            if sent and sent.strip():  # Skip empty sentences
                                sentences_batch.append(sent.strip())
                                sources_batch.append(key)
                                documents_batch.append(item)
                
                if sentences_batch:
                    # Process in batches for better memory management
                    for i in range(0, len(sentences_batch), BATCH_SIZE):
                        batch_end = min(i + BATCH_SIZE, len(sentences_batch))
                        current_sentences = sentences_batch[i:batch_end]
                        current_sources = sources_batch[i:batch_end]
                        current_documents = documents_batch[i:batch_end]
                        
                        # Generate embeddings for current batch
                        logger.info(f"Generating embeddings for batch {i//BATCH_SIZE + 1} ({len(current_sentences)} sentences) from {key}...")
                        embeddings = embedding_model.encode(
                            current_sentences, 
                            convert_to_numpy=True, 
                            show_progress_bar=True,
                            batch_size=32  # Optimize embedding batch size
                        )
                        
                        # Prepare batch insert data
                        insert_data = [
                            (sentence, source, json.dumps(document), embedding.tolist())
                            for sentence, source, document, embedding in zip(
                                current_sentences, current_sources, current_documents, embeddings
                            )
                        ]
                        
                        # Batch insert with COPY for better performance
                        logger.info(f"Inserting batch {i//BATCH_SIZE + 1} ({len(insert_data)} documents) into database...")
                        
                        await conn.executemany("""
                            INSERT INTO documents (sentence, source, document, embedding)
                            VALUES ($1, $2, $3, $4)
                        """, insert_data)
                        
                        # Commit after each batch to avoid long transactions
                        logger.info(f"Batch {i//BATCH_SIZE + 1} inserted successfully")
        
        total_docs = await get_document_count()
        logger.info(f"Successfully loaded {total_docs} documents into database")
        
        # Analyze table for better query performance
        async with db_pool.acquire() as conn:
            await conn.execute("ANALYZE documents")
            logger.info("Database table analyzed for optimal query performance")
        
        return True
        
    except Exception as e:
        logger.error(f"Error loading legal data: {e}")
        return False

async def initialize_tfidf():
    """Initialize TF-IDF vectorizer and store vectors in database"""
    try:
        logger.info("Initializing TF-IDF...")
        
        # Check if TF-IDF vectors already exist
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE tfidf_vector IS NOT NULL")
            if result > 0:
                logger.info("TF-IDF vectors already exist in database")
                return True
        
        # Get all sentences from database
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, sentence FROM documents ORDER BY id")
            
        if not rows:
            logger.warning("No documents found in database")
            return False
        
        sentences = [row['sentence'] for row in rows]
        doc_ids = [row['id'] for row in rows]
        
        # Create TF-IDF vectorizer and fit
        logger.info("Creating TF-IDF vectors...")
        vectorizer = TfidfVectorizer(max_features=10000)
        tfidf_matrix = vectorizer.fit_transform(sentences)
        
        # Store TF-IDF vectors in database
        logger.info("Storing TF-IDF vectors in database...")
        async with db_pool.acquire() as conn:
            for doc_id, tfidf_vector in zip(doc_ids, tfidf_matrix):
                # Convert sparse matrix row to string representation
                vector_str = json.dumps(tfidf_vector.toarray().tolist()[0])
                await conn.execute(
                    "UPDATE documents SET tfidf_vector = $1 WHERE id = $2",
                    vector_str, doc_id
                )
        
        logger.info("TF-IDF initialization completed")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing TF-IDF: {e}")
        return False

async def initialize_embeddings():
    """Initialize embedding model"""
    global embedding_model
    
    try:
        if embedding_model is None:
            logger.info("Loading embedding model...")
            embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
            logger.info("Embedding model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing embedding model: {e}")
        return False

async def retrieve_context_tfidf(query: str, top_k: int = 5) -> List[RetrievalResult]:
    """Retrieve context using TF-IDF stored in PostgreSQL"""
    try:
        # Get all documents with TF-IDF vectors
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, sentence, source, document, tfidf_vector 
                FROM documents 
                WHERE tfidf_vector IS NOT NULL
                ORDER BY id
            """)
        
        if not rows:
            logger.warning("No TF-IDF vectors found in database")
            return []
        
        # Extract sentences and TF-IDF vectors
        sentences = [row['sentence'] for row in rows]
        tfidf_vectors = []
        
        for row in rows:
            vector_data = json.loads(row['tfidf_vector'])
            tfidf_vectors.append(vector_data)
        
        # Create TF-IDF vectorizer and fit on existing sentences
        vectorizer = TfidfVectorizer(max_features=10000)
        vectorizer.fit(sentences)
        
        # Transform query
        query_vec = vectorizer.transform([query])
        
        # Calculate similarities
        tfidf_matrix = np.array(tfidf_vectors)
        similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        
        # Get top results
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for i in top_indices:
            if similarities[i] > 0:  # Only include non-zero similarities
                row = rows[i]
                results.append(RetrievalResult(
                    sentence=row['sentence'],
                    source=row['source'],
                    score=float(similarities[i]),
                    document=json.loads(row['document'])
                ))
        
        return results
        
    except Exception as e:
        logger.error(f"Error in TF-IDF retrieval: {e}")
        return []

async def retrieve_context_vector(query: str, top_k: int = 5, source_filter: Optional[str] = None) -> List[RetrievalResult]:
    """Retrieve context using pgvector similarity search with pgvector 0.8 optimizations"""
    if embedding_model is None:
        return []
    
    try:
        # Encode query
        query_emb = embedding_model.encode([query], convert_to_numpy=True)
        query_vector = query_emb[0].tolist()
        
        # Search using pgvector cosine similarity with optimized query
        async with db_pool.acquire() as conn:
            await register_vector(conn)  # Ensure vector types are registered
            
            # Build query with optional source filtering
            base_query = """
                SELECT sentence, source, document, 
                       1 - (embedding <=> $1::vector) as similarity_score
                FROM documents 
                WHERE embedding IS NOT NULL
            """
            
            params = [query_vector]
            param_count = 1
            
            if source_filter:
                param_count += 1
                base_query += f" AND source = ${param_count}"
                params.append(source_filter)
            
            # Use HNSW index with ef_search parameter for better recall
            final_query = f"""
                SET hnsw.ef_search = {min(top_k * 4, 200)};
                {base_query}
                ORDER BY embedding <=> $1::vector
                LIMIT ${param_count + 1}
            """
            params.append(top_k)
            
            # Execute with optimized settings
            rows = await conn.fetch(final_query, *params)
        
        results = []
        for row in rows:
            # Use a lower threshold for similarity to include more relevant results
            if row['similarity_score'] > 0.1:  
                results.append(RetrievalResult(
                    sentence=row['sentence'],
                    source=row['source'],
                    score=float(row['similarity_score']),
                    document=json.loads(row['document'])
                ))
        
        return results
        
    except Exception as e:
        logger.error(f"Error in vector retrieval: {e}")
        return []

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting Legal RAG API...")
    
    # Initialize database
    if not await init_database():
        logger.error("Failed to initialize database")
        return
    
    # Initialize embedding model
    if not await initialize_embeddings():
        logger.error("Failed to initialize embedding model")
        return
    
    # Load data into database
    if not await load_legal_data():
        logger.error("Failed to load legal data")
        return
    
    # Initialize TF-IDF
    if not await initialize_tfidf():
        logger.error("Failed to initialize TF-IDF")
    
    logger.info("Legal RAG API startup completed")

@app.get("/")
async def root():
    """Root endpoint"""
    doc_count = await get_document_count()
    
    # Get document types from database
    async with db_pool.acquire() as conn:
        sources = await conn.fetch("SELECT DISTINCT source FROM documents")
        document_types = [row['source'] for row in sources]
    
    return {
        "message": "Legal RAG API",
        "status": "running",
        "total_documents": doc_count,
        "document_types": document_types
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    doc_count = await get_document_count()
    
    # Check TF-IDF readiness
    async with db_pool.acquire() as conn:
        tfidf_count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE tfidf_vector IS NOT NULL")
        vector_count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
    
    return {
        "status": "healthy",
        "database_connected": db_pool is not None,
        "total_documents": doc_count,
        "tfidf_ready": tfidf_count > 0,
        "tfidf_documents": tfidf_count,
        "embeddings_ready": embedding_model is not None,
        "vector_documents": vector_count
    }

@app.post("/search", response_model=QueryResponse)
async def search_documents(request: QueryRequest):
    """Search legal documents using RAG with pgvector 0.8 optimizations"""
    doc_count = await get_document_count()
    if doc_count == 0:
        raise HTTPException(status_code=503, detail="No data loaded in database")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    response = QueryResponse(query=request.query)
    
    try:
        if request.method in ["tfidf", "both"]:
            tfidf_results = await retrieve_context_tfidf(request.query, request.top_k)
            # Apply score filtering if specified
            if request.min_score:
                tfidf_results = [r for r in tfidf_results if r.score >= request.min_score]
            response.tfidf_results = tfidf_results
        
        if request.method in ["vector", "both"]:
            if embedding_model is not None:
                vector_results = await retrieve_context_vector(
                    request.query, 
                    request.top_k, 
                    request.source_filter
                )
                # Apply score filtering if specified
                if request.min_score:
                    vector_results = [r for r in vector_results if r.score >= request.min_score]
                response.vector_results = vector_results
            else:
                logger.warning("Embedding model not available")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/stats")
async def get_stats():
    """Get statistics about the loaded data"""
    doc_count = await get_document_count()
    if doc_count == 0:
        raise HTTPException(status_code=503, detail="No data loaded in database")
    
    # Get document type statistics
    async with db_pool.acquire() as conn:
        source_stats = await conn.fetch("""
            SELECT source, COUNT(*) as count 
            FROM documents 
            GROUP BY source 
            ORDER BY count DESC
        """)
        
        tfidf_count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE tfidf_vector IS NOT NULL")
        vector_count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
    
    stats = {}
    for row in source_stats:
        stats[row['source']] = {
            "total_documents": row['count']
        }
    
    return {
        "total_documents": doc_count,
        "document_types": stats,
        "models_ready": {
            "tfidf": tfidf_count > 0,
            "tfidf_documents": tfidf_count,
            "embeddings": embedding_model is not None,
            "vector_documents": vector_count
        },
        "database_info": {
            "connected": db_pool is not None,
            "total_documents": doc_count,
            "documents_with_tfidf": tfidf_count,
            "documents_with_vectors": vector_count
        }
    }

@app.delete("/documents")
async def clear_all_documents():
    """Clear all documents from database"""
    try:
        if await clear_documents():
            return {
                "message": "All documents cleared from database successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear documents")
    except Exception as e:
        logger.error(f"Error clearing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear documents")

@app.get("/sources")
async def get_document_sources():
    """Get all available document sources"""
    try:
        async with db_pool.acquire() as conn:
            sources = await conn.fetch("""
                SELECT source, COUNT(*) as document_count,
                       COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as vector_count,
                       COUNT(CASE WHEN tfidf_vector IS NOT NULL THEN 1 END) as tfidf_count
                FROM documents 
                GROUP BY source 
                ORDER BY document_count DESC
            """)
        
        return {
            "sources": [
                {
                    "name": row['source'],
                    "document_count": row['document_count'],
                    "vector_count": row['vector_count'],
                    "tfidf_count": row['tfidf_count']
                }
                for row in sources
            ]
        }
    except Exception as e:
        logger.error(f"Error getting document sources: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document sources")

@app.post("/search/similar")
async def find_similar_documents(request: dict):
    """Find documents similar to a given document ID using pgvector"""
    document_id = request.get("document_id")
    top_k = request.get("top_k", 5)
    
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")
    
    try:
        async with db_pool.acquire() as conn:
            await register_vector(conn)
            
            # Get the embedding of the reference document
            ref_doc = await conn.fetchrow("""
                SELECT embedding, sentence, source, document 
                FROM documents 
                WHERE id = $1 AND embedding IS NOT NULL
            """, document_id)
            
            if not ref_doc:
                raise HTTPException(status_code=404, detail="Document not found or has no embedding")
            
            # Find similar documents
            rows = await conn.fetch("""
                SELECT id, sentence, source, document,
                       1 - (embedding <=> $1::vector) as similarity_score
                FROM documents 
                WHERE id != $2 AND embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, ref_doc['embedding'], document_id, top_k)
            
            results = []
            for row in rows:
                if row['similarity_score'] > 0.1:
                    results.append({
                        "id": row['id'],
                        "sentence": row['sentence'],
                        "source": row['source'],
                        "score": float(row['similarity_score']),
                        "document": json.loads(row['document'])
                    })
            
            return {
                "reference_document": {
                    "id": document_id,
                    "sentence": ref_doc['sentence'],
                    "source": ref_doc['source']
                },
                "similar_documents": results
            }
            
    except Exception as e:
        logger.error(f"Error finding similar documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar documents")

@app.get("/index/status")
async def get_index_status():
    """Get status of pgvector indexes"""
    try:
        async with db_pool.acquire() as conn:
            # Get index information
            indexes = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename = 'documents'
                ORDER BY indexname
            """)
            
            # Get table statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_documents,
                    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as documents_with_vectors,
                    COUNT(CASE WHEN tfidf_vector IS NOT NULL THEN 1 END) as documents_with_tfidf,
                    pg_size_pretty(pg_total_relation_size('documents')) as table_size
                FROM documents
            """)
            
            return {
                "indexes": [
                    {
                        "name": idx['indexname'],
                        "definition": idx['indexdef']
                    }
                    for idx in indexes
                ],
                "statistics": {
                    "total_documents": stats['total_documents'],
                    "documents_with_vectors": stats['documents_with_vectors'],
                    "documents_with_tfidf": stats['documents_with_tfidf'],
                    "table_size": stats['table_size']
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting index status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get index status")

@app.post("/reload")
async def reload_data():
    """Reload data and reinitialize models"""
    global dataset, embedding_model
    
    try:
        logger.info("Reloading data...")
        
        # Clear database
        await clear_documents()
        
        # Clear current data
        dataset = None
        embedding_model = None
        
        # Initialize embedding model
        if not await initialize_embeddings():
            raise HTTPException(status_code=500, detail="Failed to initialize embedding model")
        
        # Reload data into database
        if not await load_legal_data():
            raise HTTPException(status_code=500, detail="Failed to load legal data")
        
        # Initialize TF-IDF
        tfidf_success = await initialize_tfidf()
        
        doc_count = await get_document_count()
        
        # Get document types
        async with db_pool.acquire() as conn:
            sources = await conn.fetch("SELECT DISTINCT source FROM documents")
            document_types = [row['source'] for row in sources]
        
        return {
            "message": "Data reloaded successfully",
            "total_documents": doc_count,
            "tfidf_initialized": tfidf_success,
            "embeddings_initialized": embedding_model is not None,
            "document_types": document_types
        }
        
    except Exception as e:
        logger.error(f"Error reloading data: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload data")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

async def main():
    """Main function with pgvector 0.8 optimizations"""
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('legal_rag.log')
        ]
    )
    
    logger.info("Starting Legal RAG API with pgvector 0.8...")
    
    # Initialize database with optimizations
    if not await init_database():
        logger.error("Failed to initialize database. Exiting.")
        sys.exit(1)
    
    # Initialize embedding model
    if not await initialize_embeddings():
        logger.error("Failed to initialize embedding model. Exiting.")
        sys.exit(1)
    
    # Load data if needed
    doc_count = await get_document_count()
    if doc_count == 0:
        logger.info("No documents found. Loading legal data...")
        if not await load_legal_data():
            logger.error("Failed to load legal data. Exiting.")
            sys.exit(1)
    else:
        logger.info(f"Found {doc_count} documents in database")
    
    # Initialize TF-IDF if needed
    async with db_pool.acquire() as conn:
        tfidf_count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE tfidf_vector IS NOT NULL")
        if tfidf_count == 0:
            logger.info("No TF-IDF vectors found. Initializing...")
            await initialize_tfidf()
    
    # Optimize database settings for pgvector 0.8
    try:
        async with db_pool.acquire() as conn:
            # Set optimal work_mem for vector operations
            await conn.execute("SET work_mem = '256MB'")
            # Set maintenance_work_mem for index building
            await conn.execute("SET maintenance_work_mem = '1GB'")
            # Optimize for vector operations
            await conn.execute("SET max_parallel_workers_per_gather = 2")
            # Set HNSW parameters for better performance
            await conn.execute("SET hnsw.ef_search = 100")
            
        logger.info("Database optimized for pgvector 0.8 operations")
    except Exception as e:
        logger.warning(f"Could not apply database optimizations: {e}")
    
    logger.info("Legal RAG API initialization completed successfully")
    
    # Run the FastAPI application
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True,
        workers=1  # Single worker for shared database pool
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())