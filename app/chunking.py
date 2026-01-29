"""
Text chunking utilities for RAG.
"""
from typing import List

from app.config import settings


def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Uses a simple character-based splitting with overlap.
    Tries to break at sentence boundaries when possible.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum characters per chunk (default from settings)
        chunk_overlap: Overlap between chunks (default from settings)
        
    Returns:
        List of text chunks
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = settings.CHUNK_OVERLAP
    
    if not text or not text.strip():
        return []
    
    # Clean up whitespace
    text = " ".join(text.split())
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks: List[str] = []
    start = 0
    
    while start < len(text):
        # Get the chunk end position
        end = start + chunk_size
        
        if end >= len(text):
            # Last chunk
            chunks.append(text[start:].strip())
            break
        
        # Try to find a good break point (sentence boundary)
        chunk = text[start:end]
        
        # Look for sentence endings within the last 20% of the chunk
        search_start = int(len(chunk) * 0.8)
        last_period = chunk.rfind(". ", search_start)
        last_question = chunk.rfind("? ", search_start)
        last_exclaim = chunk.rfind("! ", search_start)
        
        # Find the latest sentence boundary
        break_point = max(last_period, last_question, last_exclaim)
        
        if break_point > 0:
            # Found a sentence boundary, adjust end
            end = start + break_point + 1
            chunk = text[start:end].strip()
        else:
            # No sentence boundary, try to break at word boundary
            last_space = chunk.rfind(" ")
            if last_space > chunk_size // 2:
                end = start + last_space
                chunk = text[start:end].strip()
        
        if chunk:
            chunks.append(chunk)
        
        # Move start with overlap
        start = end - chunk_overlap
        if start < 0:
            start = 0
    
    return chunks
