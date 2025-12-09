"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============ Request Schemas ============

class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=5000, description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    include_context: bool = Field(False, description="Whether to include retrieved context in response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I've been feeling anxious lately and can't sleep well",
                "session_id": "user123_session1",
                "include_context": False
            }
        }


class FeedbackRequest(BaseModel):
    """Request schema for feedback endpoint"""
    session_id: str = Field(..., description="Session ID")
    message_id: str = Field(..., description="Message ID to provide feedback for")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Optional feedback text")


class IndexDocumentsRequest(BaseModel):
    """Request schema for indexing new documents"""
    documents: List[Dict[str, Any]] = Field(..., description="List of documents to index")
    

# ============ Response Schemas ============

class ContextItem(BaseModel):
    """Schema for retrieved context items"""
    content: str
    source: str
    similarity: float
    metadata: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    """Response schema for chat endpoint"""
    message_id: str = Field(..., description="Unique message ID")
    response: str = Field(..., description="Chatbot's response")
    classification: Optional[str] = Field(None, description="Detected mental health classification (only after enough messages)")
    confidence: float = Field(..., ge=0, le=1, description="Classification confidence score")
    is_crisis: bool = Field(False, description="Whether crisis indicators were detected")
    is_final_analysis: bool = Field(False, description="Whether this is the final analysis")
    message_count: int = Field(0, description="Number of messages in conversation")
    messages_until_analysis: int = Field(0, description="Messages remaining until analysis")
    context: Optional[List[ContextItem]] = Field(None, description="Retrieved context if requested")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_abc123",
                "response": "I hear that you're going through a difficult time...",
                "classification": None,
                "confidence": 0.0,
                "is_crisis": False,
                "is_final_analysis": False,
                "message_count": 2,
                "messages_until_analysis": 3,
                "context": None,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class HealthCheckResponse(BaseModel):
    """Response schema for health check endpoint"""
    status: str
    version: str
    vector_store_status: str
    document_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatsResponse(BaseModel):
    """Response schema for statistics endpoint"""
    total_documents: int
    collection_name: str
    embedding_model: str
    llm_model: str


class ErrorResponse(BaseModel):
    """Response schema for errors"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ Session Schemas ============

class Message(BaseModel):
    """Schema for a single message in conversation history"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    classification: Optional[str] = None
    is_crisis: bool = False


class Session(BaseModel):
    """Schema for a chat session"""
    session_id: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}