"""
OpenAI client - embeddings and chat completions.
"""
from typing import List, Optional

from openai import OpenAI

from app.config import settings

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector for a text using OpenAI.
    
    Args:
        text: The text to embed
        
    Returns:
        Embedding vector as list of floats (1536 dimensions)
    """
    # Clean and truncate text if needed
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * 1536
    
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text
    )
    
    return response.data[0].embedding


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Get embeddings for multiple texts in a single API call.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    # Clean texts
    cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
    
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=cleaned_texts
    )
    
    # Sort by index to maintain order
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [d.embedding for d in sorted_data]


def chat_completion(
    messages: List[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str:
    """
    Generate a chat completion using OpenAI.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model to use (default from settings)
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        
    Returns:
        The assistant's response text
    """
    if model is None:
        model = settings.OPENAI_CHAT_MODEL
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content
