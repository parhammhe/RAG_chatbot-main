"""
RAG module - retrieval and prompt building for RAG pipeline.
"""
from typing import List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.models import Chunk
from app.openai_client import get_embedding


def retrieve_context(
    db: Session,
    user_id: int,
    query: str,
    k: int = None
) -> List[Tuple[str, float]]:
    """
    Retrieve top-k relevant chunks for a user's query using pgvector.
    
    IMPORTANT: Only returns chunks belonging to the specified user (multi-tenancy).
    
    Args:
        db: Database session
        user_id: The current user's ID
        query: The search query
        k: Number of results to return (default from settings)
        
    Returns:
        List of (chunk_content, similarity_score) tuples
    """
    if k is None:
        k = settings.RETRIEVAL_TOP_K
    
    # Get query embedding
    query_embedding = get_embedding(query)
    
    # Use pgvector's cosine similarity search
    # Filter by user_id to ensure multi-tenancy isolation
    sql = text("""
        SELECT content, 1 - (embedding <=> :embedding) as similarity
        FROM chunks
        WHERE user_id = :user_id
        ORDER BY embedding <=> :embedding
        LIMIT :k
    """)
    
    result = db.execute(
        sql,
        {
            "embedding": str(query_embedding),
            "user_id": user_id,
            "k": k
        }
    )
    
    return [(row.content, row.similarity) for row in result]


def retrieve_chunks_with_metadata(
    db: Session,
    user_id: int,
    query: str,
    k: int = None
) -> List[dict]:
    """
    Retrieve chunks with full metadata for a user's query.
    
    Args:
        db: Database session
        user_id: The current user's ID
        query: The search query
        k: Number of results to return
        
    Returns:
        List of dicts with chunk info and similarity
    """
    if k is None:
        k = settings.RETRIEVAL_TOP_K
    
    query_embedding = get_embedding(query)
    
    sql = text("""
        SELECT c.id, c.content, c.document_id, d.filename,
               1 - (c.embedding <=> :embedding) as similarity
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.user_id = :user_id
        ORDER BY c.embedding <=> :embedding
        LIMIT :k
    """)
    
    result = db.execute(
        sql,
        {
            "embedding": str(query_embedding),
            "user_id": user_id,
            "k": k
        }
    )
    
    return [
        {
            "chunk_id": row.id,
            "content": row.content,
            "document_id": row.document_id,
            "filename": row.filename,
            "similarity": row.similarity
        }
        for row in result
    ]


def build_rag_prompt(context_chunks: List[str], query: str) -> List[dict]:
    """
    Build a prompt for RAG-based chat completion.
    
    Args:
        context_chunks: List of relevant text chunks
        query: The user's question
        
    Returns:
        List of messages for chat completion
    """
    context_text = "\n\n---\n\n".join(context_chunks)
    
    system_message = """You are a helpful AI assistant. Answer the user's question based on the provided context. 
If the context doesn't contain relevant information to answer the question, say so honestly.
Be concise and accurate in your responses."""

    user_message = f"""Context:
{context_text}

Question: {query}

Please answer the question based on the context provided above."""

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
