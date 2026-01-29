"""
PDF utilities - extract text from PDF files.
"""
from io import BytesIO
from typing import List

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text content from a PDF file.
    
    Args:
        file_bytes: The PDF file content as bytes
        
    Returns:
        Extracted text as a single string
    """
    pdf_file = BytesIO(file_bytes)
    reader = PdfReader(pdf_file)
    
    text_parts: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    
    return "\n\n".join(text_parts)


def extract_text_by_page(file_bytes: bytes) -> List[str]:
    """
    Extract text from a PDF file, returning a list of text per page.
    
    Args:
        file_bytes: The PDF file content as bytes
        
    Returns:
        List of strings, one per page
    """
    pdf_file = BytesIO(file_bytes)
    reader = PdfReader(pdf_file)
    
    pages: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        pages.append(page_text if page_text else "")
    
    return pages
