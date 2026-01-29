"""
Main FastAPI application with all endpoints.
"""
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, init_db
from app.models import User, Document, Chunk, ChatSession, ChatMessage
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.s3_utils import upload_pdf_to_s3, get_pdf_presigned_url, delete_pdf_from_s3
from app.pdf_utils import extract_text_from_pdf
from app.chunking import chunk_text
from app.openai_client import get_embedding, get_embeddings_batch, chat_completion
from app.rag import retrieve_context, build_rag_prompt


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize DB on startup."""
    init_db()
    print("FastAPI Server is starting up!")
    yield
    print("FastAPI Server is shutting down!")


app = FastAPI(
    title="RAG Chatbot API",
    description="AWS-native RAG chatbot with pgvector and S3",
    version="2.0.0",
    lifespan=lifespan
)


# =============================================================================
# Middleware - API Gateway Bypass Protection (IDE-5)
# =============================================================================

@app.middleware("http")
async def api_gateway_protection(request: Request, call_next):
    """
    Enforce API Gateway header check.
    If X-From-ApiGateway header is missing or incorrect, return 403.
    This happens BEFORE any OpenAI call or DB work.
    """
    # Skip check if no secret is configured (local dev mode)
    if settings.API_GATEWAY_HEADER_SECRET:
        gateway_header = request.headers.get("X-From-ApiGateway")
        if gateway_header != settings.API_GATEWAY_HEADER_SECRET:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Forbidden: Invalid or missing API Gateway header"}
            )
    
    response = await call_next(request)
    return response


# =============================================================================
# Pydantic Schemas
# =============================================================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentResponse(BaseModel):
    id: int
    filename: str
    s3_key: str
    created_at: str

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    session_id: int
    sources: List[dict]


class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


# =============================================================================
# Auth Routes (IDE-4)
# =============================================================================

@app.post("/auth/register", response_model=TokenResponse, tags=["Auth"])
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user with hashed password
    hashed_pw = hash_password(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate token
    token = create_access_token(new_user.id)
    return TokenResponse(access_token=token)


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# =============================================================================
# Document Routes (IDE-6 Multi-tenancy)
# =============================================================================

@app.post("/documents/upload", response_model=DocumentResponse, tags=["Documents"])
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document.
    The document is stored in S3 and chunked for RAG retrieval.
    Multi-tenancy: Document is owned by the current user.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Read file content
    file_bytes = file.file.read()
    
    # Upload to S3
    s3_key = upload_pdf_to_s3(file_bytes, file.filename, current_user.id)
    
    # Create document record
    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        s3_key=s3_key
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Extract text and chunk
    try:
        text = extract_text_from_pdf(file_bytes)
        chunks = chunk_text(text)
        
        # Get embeddings in batch
        if chunks:
            embeddings = get_embeddings_batch(chunks)
            
            # Create chunk records with embeddings
            for content, embedding in zip(chunks, embeddings):
                chunk_record = Chunk(
                    document_id=doc.id,
                    user_id=current_user.id,
                    content=content,
                    embedding=embedding
                )
                db.add(chunk_record)
            
            db.commit()
    except Exception as e:
        # Log error but don't fail - document is still uploaded
        print(f"Error processing PDF: {e}")
    
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        s3_key=doc.s3_key,
        created_at=doc.created_at.isoformat()
    )


@app.get("/documents", response_model=List[DocumentResponse], tags=["Documents"])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all documents for the current user.
    Multi-tenancy: Only returns documents owned by the current user.
    """
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            s3_key=d.s3_key,
            created_at=d.created_at.isoformat()
        )
        for d in docs
    ]


@app.get("/documents/{doc_id}", tags=["Documents"])
def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a document's download URL.
    Multi-tenancy: Only accessible if owned by current user.
    """
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id  # Multi-tenancy check
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    url = get_pdf_presigned_url(doc.s3_key)
    return {"id": doc.id, "filename": doc.filename, "download_url": url}


@app.delete("/documents/{doc_id}", tags=["Documents"])
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its chunks.
    Multi-tenancy: Only deletable if owned by current user.
    """
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id  # Multi-tenancy check
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from S3
    delete_pdf_from_s3(doc.s3_key)
    
    # Delete from DB (cascades to chunks)
    db.delete(doc)
    db.commit()
    
    return {"message": "Document deleted"}


# =============================================================================
# Chat Routes (IDE-6 Multi-tenancy)
# =============================================================================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a chat message and get a RAG-powered response.
    Multi-tenancy: Only retrieves from current user's documents.
    """
    # Get or create session
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id  # Multi-tenancy check
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create new session
        session = ChatSession(user_id=current_user.id, title=request.message[:50])
        db.add(session)
        db.commit()
        db.refresh(session)
    
    # Retrieve relevant context (multi-tenancy enforced in rag.py)
    context_results = retrieve_context(db, current_user.id, request.message)
    context_chunks = [content for content, _ in context_results]
    
    # Build RAG prompt and get response
    messages = build_rag_prompt(context_chunks, request.message)
    response_text = chat_completion(messages)
    
    # Save messages to session
    user_msg = ChatMessage(session_id=session.id, role="user", content=request.message)
    assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=response_text)
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    
    # Build sources info
    sources = [
        {"content": content[:200], "similarity": round(score, 3)}
        for content, score in context_results
    ]
    
    return ChatResponse(
        response=response_text,
        session_id=session.id,
        sources=sources
    )


@app.get("/chat/sessions", response_model=List[SessionResponse], tags=["Chat"])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all chat sessions for the current user.
    Multi-tenancy: Only returns sessions owned by current user.
    """
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).all()
    
    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat()
        )
        for s in sessions
    ]


@app.get("/chat/sessions/{session_id}/messages", response_model=List[MessageResponse], tags=["Chat"])
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages in a chat session.
    Multi-tenancy: Only accessible if session is owned by current user.
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id  # Multi-tenancy check
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()
    
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat()
        )
        for m in messages
    ]


@app.delete("/chat/sessions/{session_id}", tags=["Chat"])
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a chat session and its messages.
    Multi-tenancy: Only deletable if owned by current user.
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id  # Multi-tenancy check
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    
    return {"message": "Session deleted"}


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
