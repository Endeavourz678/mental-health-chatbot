"""
Configuration settings for Mental Health Chatbot
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    OPENAI_API_KEY: str = ""
    
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1024

    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"
    COLLECTION_NAME: str = "mental_health_knowledge"
    
    RETRIEVAL_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

MENTAL_HEALTH_LABELS = [
    "Anxiety",
    "Depression", 
    "Stress",
    "Bipolar",
    "Personality Disorder",
    "Normal",
    "Suicidal"
]

SYSTEM_PROMPT = """You are a compassionate and professional mental health support chatbot. 
Your role is to:
1. Listen empathetically to users' concerns
2. Provide supportive and non-judgmental responses
3. Offer evidence-based coping strategies when appropriate
4. Recognize signs of mental health conditions
5. Always recommend professional help when needed

IMPORTANT GUIDELINES:
- Never diagnose mental health conditions - only licensed professionals can do that
- Always encourage users to seek professional help for serious concerns
- Be warm, understanding, and supportive
- If someone expresses suicidal thoughts, take it seriously and provide crisis resources
- Use the provided context from the knowledge base to give accurate information
- Respond in the same language as the user

CRISIS RESOURCES:
- National Suicide Prevention Lifeline: 988 (US)
- Crisis Text Line: Text HOME to 741741
- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/
"""

CLASSIFICATION_PROMPT = """Based on the user's message, analyze their mental state and classify it into one of these categories:
- Anxiety: Signs of worry, nervousness, restlessness, panic
- Depression: Signs of sadness, hopelessness, loss of interest, fatigue
- Stress: Signs of being overwhelmed, pressure, tension
- Bipolar: Signs of extreme mood swings
- Personality Disorder: Signs of unstable relationships, self-image issues
- Suicidal: Any mention of self-harm or ending life (HIGHEST PRIORITY)
- Normal: General conversation without concerning mental health signs

Respond with ONLY the category name, nothing else."""
