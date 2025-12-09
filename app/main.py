"""
FastAPI Application for Mental Health Chatbot
Production-ready REST API with RAG capabilities
"""
import os
import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings, SYSTEM_PROMPT
from utils import DataLoader, VectorStore
from models import MentalHealthRAGChain
from app.schemas import (
    ChatRequest, ChatResponse, HealthCheckResponse, 
    StatsResponse, ErrorResponse, ContextItem
)
from app.session_manager import SessionManager


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global instances
vector_store: Optional[VectorStore] = None
rag_chain: Optional[MentalHealthRAGChain] = None
session_manager: Optional[SessionManager] = None


def initialize_components():
    """Initialize all components"""
    global vector_store, rag_chain, session_manager
    
    logger.info("Initializing components...")
    
    # Check for API key
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set. Some features will be unavailable.")
        return False
    
    try:
        # Initialize vector store
        vector_store = VectorStore(
            persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
            collection_name=settings.COLLECTION_NAME,
            openai_api_key=api_key,
            embedding_model=settings.EMBEDDING_MODEL
        )
        
        # Load and index data if collection is empty
        stats = vector_store.get_collection_stats()
        if stats['count'] == 0:
            logger.info("Vector store is empty, loading data...")
            data_loader = DataLoader(settings.DATA_DIR)
            documents = data_loader.load_all_datasets()
            if documents:
                vector_store.add_documents(documents)
                logger.info(f"Indexed {len(documents)} documents")
        else:
            logger.info(f"Vector store has {stats['count']} documents")
        
        # Initialize RAG chain
        rag_chain = MentalHealthRAGChain(
            vector_store=vector_store,
            openai_api_key=api_key,
            llm_model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            retrieval_top_k=settings.RETRIEVAL_TOP_K
        )
        
        # Initialize session manager
        session_manager = SessionManager()
        
        logger.info("All components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    initialize_components()
    yield
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Mental Health Support Chatbot API",
    description="""
    A production-ready chatbot API for mental health support using RAG (Retrieval-Augmented Generation).
    
    ## Features
    - Mental health classification (Anxiety, Depression, Stress, etc.)
    - Crisis detection with immediate support resources
    - Context-aware responses using knowledge base
    - Session management for conversation continuity
    
    ## Important Notes
    - This chatbot is for support purposes only and does not replace professional help
    - Crisis resources are provided when concerning content is detected
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Exception Handlers ============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.DEBUG else None
        ).model_dump()
    )


# ============ Dependency Functions ============

def get_rag_chain() -> MentalHealthRAGChain:
    """Dependency to get RAG chain"""
    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Please check API key configuration."
        )
    return rag_chain


def get_session_manager() -> SessionManager:
    """Dependency to get session manager"""
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    return session_manager


# ============ API Endpoints ============

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Mental Health Support Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    vs_status = "healthy" if vector_store else "not_initialized"
    doc_count = vector_store.get_collection_stats()['count'] if vector_store else 0
    
    return HealthCheckResponse(
        status="healthy" if rag_chain else "degraded",
        version="1.0.0",
        vector_store_status=vs_status,
        document_count=doc_count
    )


@app.get("/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats():
    """Get system statistics"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not initialized")
    
    stats = vector_store.get_collection_stats()
    
    return StatsResponse(
        total_documents=stats['count'],
        collection_name=stats['name'],
        embedding_model=settings.EMBEDDING_MODEL,
        llm_model=settings.LLM_MODEL
    )


@app.post("/chat", tags=["Chat"])
async def chat(
    request: ChatRequest,
    chain: MentalHealthRAGChain = Depends(get_rag_chain),
    sessions: SessionManager = Depends(get_session_manager)
):
    """
    Main chat endpoint
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get chat history
        chat_history = []
        try:
            chat_history = sessions.get_chat_history(session_id)
        except:
            pass
        
        # Get response from RAG chain
        response = chain.chat(
            user_message=request.message,
            chat_history=chat_history
        )
        
        # Save to session
        try:
            sessions.add_message(session_id, "user", request.message, response.classification, response.is_crisis)
            sessions.add_message(session_id, "assistant", response.answer)
        except:
            pass
        
        # Return simple dict
        return {
            "message_id": f"msg_{uuid.uuid4().hex[:12]}",
            "response": response.answer,
            "classification": response.classification,
            "confidence": response.confidence,
            "is_crisis": response.is_crisis,
            "is_final_analysis": response.is_final_analysis,
            "message_count": response.message_count,
            "messages_until_analysis": max(0, 5 - response.message_count)
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/simple", tags=["Chat"])
async def chat_simple(
    message: str,
    chain: MentalHealthRAGChain = Depends(get_rag_chain)
):
    """
    Simplified chat endpoint - just message in, response out
    """
    try:
        response = chain.chat(user_message=message)
        
        return {
            "response": response.answer,
            "classification": response.classification,
            "is_crisis": response.is_crisis
        }
        
    except Exception as e:
        logger.error(f"Error in simple chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}", tags=["Session"])
async def clear_session(
    session_id: str,
    sessions: SessionManager = Depends(get_session_manager)
):
    """Clear a chat session"""
    if sessions.clear_session(session_id):
        return {"message": f"Session {session_id} cleared"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/session/{session_id}/stats", tags=["Session"])
async def get_session_stats(
    session_id: str,
    sessions: SessionManager = Depends(get_session_manager)
):
    """Get statistics for a session"""
    stats = sessions.get_session_stats(session_id)
    if stats:
        return stats
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/index/reload", tags=["Admin"])
async def reload_index(
    background_tasks: BackgroundTasks,
    chain: MentalHealthRAGChain = Depends(get_rag_chain)
):
    """Reload the vector store index from data files"""
    
    def reload_task():
        try:
            data_loader = DataLoader(settings.DATA_DIR)
            documents = data_loader.load_all_datasets()
            if documents:
                vector_store.clear_collection()
                vector_store.add_documents(documents)
                logger.info(f"Reloaded {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error reloading index: {e}")
    
    background_tasks.add_task(reload_task)
    
    return {"message": "Index reload started in background"}


# ============ Main Entry Point ============

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )