"""
RAG (Retrieval-Augmented Generation) Chain for Mental Health Chatbot
"""
from openai import OpenAI
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass

from utils.vector_store import VectorStore
from config import SYSTEM_PROMPT, CLASSIFICATION_PROMPT, MENTAL_HEALTH_LABELS


logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str
    content: str


@dataclass
class RAGResponse:
    """Response from the RAG chain"""
    answer: str
    classification: Optional[str]
    confidence: float
    retrieved_context: List[Dict]
    is_crisis: bool
    is_final_analysis: bool = False
    message_count: int = 0


MIN_MESSAGES_FOR_ANALYSIS = 5


class MentalHealthRAGChain:
    
    def __init__(
        self,
        vector_store: VectorStore,
        openai_api_key: str,
        llm_model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        retrieval_top_k: int = 5
    ):
        self.vector_store = vector_store
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retrieval_top_k = retrieval_top_k
        
        self.crisis_keywords = [
            'suicide', 'kill myself', 'end my life', 'want to die',
            'self-harm', 'hurt myself', 'cutting', 'overdose',
            'no reason to live', 'better off dead', 'ending it all'
        ]
        
        logger.info("Initialized Mental Health RAG Chain")
    
    def _check_crisis(self, text: str) -> bool:
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.crisis_keywords)
    
    def _retrieve_context(self, query: str) -> List[Dict]:
        try:
            results = self.vector_store.search(query=query, top_k=self.retrieval_top_k)
            return results
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    def _format_context(self, retrieved_docs: List[Dict]) -> str:
        if not retrieved_docs:
            return ""
        
        parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            content = doc.get('content', '')
            parts.append(f"[{i}] {content}")
        
        return "\n".join(parts)
    
    def _analyze_conversation(self, chat_history: List[ChatMessage], current_message: str) -> Tuple[str, float]:
        """Analyze full conversation for mental health classification"""
        try:
            all_user_msgs = [m.content for m in chat_history if m.role == "user"]
            all_user_msgs.append(current_message)
            conversation = "\n".join([f"- {msg}" for msg in all_user_msgs])
            
            prompt = f"""Analyze these user messages and classify their mental health state.

Messages:
{conversation}

Classify into ONE category:
- Anxiety
- Depression  
- Stress
- Bipolar
- Personality Disorder
- Suicidal
- Normal

Reply with ONLY the category name."""

            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a mental health classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            classification = response.choices[0].message.content.strip()
            
            # Validate
            valid = ["Anxiety", "Depression", "Stress", "Bipolar", "Personality Disorder", "Suicidal", "Normal"]
            if classification not in valid:
                for v in valid:
                    if v.lower() in classification.lower():
                        classification = v
                        break
                else:
                    classification = "Normal"
            
            confidence = 0.75 if classification != "Normal" else 0.6
            return classification, confidence
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return "Normal", 0.5
    
    def _generate_response(self, user_message: str, context: str, chat_history: List[ChatMessage], is_gathering: bool) -> str:
        """Generate chatbot response"""
        try:
            if is_gathering:
                system = """You are a compassionate mental health support chatbot.
Your goal is to LISTEN and understand the user's feelings.
- Be warm and empathetic
- Ask follow-up questions to understand better
- DO NOT diagnose or label them yet
- Keep responses short and conversational"""
            else:
                system = """You are a compassionate mental health support chatbot.
Provide a supportive summary based on the conversation.
- Acknowledge their feelings
- Offer 2-3 coping strategies
- Recommend professional help if needed
- Be warm, not clinical"""

            messages = [{"role": "system", "content": system}]
            
            # Add history
            for msg in chat_history[-6:]:
                messages.append({"role": msg.role, "content": msg.content})
            
            # Add current
            if context:
                user_content = f"{user_message}\n\n[Reference info: {context[:500]}]"
            else:
                user_content = user_message
                
            messages.append({"role": "user", "content": user_content})
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return "I'm here to listen. Could you tell me more about how you're feeling?"
    
    def chat(
        self,
        user_message: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> RAGResponse:
        """Main chat method"""
        
        if chat_history is None:
            chat_history = []
        
        # Count user messages
        user_msg_count = len([m for m in chat_history if m.role == "user"]) + 1
        
        # Check crisis
        is_crisis = self._check_crisis(user_message)
        
        # Get context
        retrieved = self._retrieve_context(user_message)
        context = self._format_context(retrieved)
        
        # Decide: gathering or analysis
        is_gathering = user_msg_count < MIN_MESSAGES_FOR_ANALYSIS
        
        if is_gathering and not is_crisis:
            # Still chatting, no classification yet
            answer = self._generate_response(user_message, context, chat_history, is_gathering=True)
            
            return RAGResponse(
                answer=answer,
                classification=None,
                confidence=0.0,
                retrieved_context=retrieved,
                is_crisis=is_crisis,
                is_final_analysis=False,
                message_count=user_msg_count
            )
        else:
            # Time for analysis
            classification, confidence = self._analyze_conversation(chat_history, user_message)
            
            if is_crisis:
                classification = "Suicidal"
                confidence = 1.0
            
            answer = self._generate_response(user_message, context, chat_history, is_gathering=False)
            
            # Add analysis summary
            answer = f"""Based on our conversation, I've noticed some signs that suggest you may be experiencing **{classification}**.

{answer}

Remember: This is not a diagnosis. Please consider speaking with a mental health professional for proper support."""
            
            return RAGResponse(
                answer=answer,
                classification=classification,
                confidence=confidence,
                retrieved_context=retrieved,
                is_crisis=is_crisis,
                is_final_analysis=True,
                message_count=user_msg_count
            )
    
    def get_crisis_response(self) -> str:
        return """I'm concerned about what you've shared. Please reach out for help:

🆘 National Suicide Prevention Lifeline: 988 (US)
🆘 Crisis Text Line: Text HOME to 741741

You matter. Help is available."""