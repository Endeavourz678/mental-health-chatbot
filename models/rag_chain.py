"""
RAG (Retrieval-Augmented Generation) Chain for Mental Health Chatbot
Logic: Natural flowing conversation - like talking to a supportive friend
Status label shown separately, NOT in the chat response
All prompts in English
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
    status_label: Optional[str] = None
    show_label: bool = False
    message_count: int = 0


# Threshold for showing label
CONFIDENCE_THRESHOLD = 0.65
MIN_MESSAGES_FOR_LABEL = 3  # Minimum 3 messages before showing label


class MentalHealthRAGChain:
    
    def __init__(
        self,
        vector_store: VectorStore,
        openai_api_key: str,
        llm_model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 512,
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
            'no reason to live', 'better off dead', 'ending it all',
            'bunuh diri', 'mau mati', 'ingin mati', 'tidak ingin hidup',
            'menyakiti diri', 'mengakhiri hidup'
        ]
        
        logger.info("Initialized Mental Health RAG Chain")
    
    def _check_crisis(self, text: str) -> bool:
        """Check for crisis keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.crisis_keywords)
    
    def _retrieve_context(self, query: str) -> List[Dict]:
        """Retrieve relevant context from vector store"""
        try:
            results = self.vector_store.search(query=query, top_k=self.retrieval_top_k)
            return results
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    def _format_context(self, retrieved_docs: List[Dict]) -> str:
        """Format retrieved documents into context string"""
        if not retrieved_docs:
            return ""
        
        parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'unknown')
            status = metadata.get('mental_health_status', '')
            
            if status:
                parts.append(f"[{i}] ({source} - {status}) {content}")
            else:
                parts.append(f"[{i}] ({source}) {content}")
        
        return "\n".join(parts)
    
    def _analyze_mental_state(self, chat_history: List[ChatMessage], current_message: str, context: str = "") -> Tuple[str, float]:
        """
        Analyze mental state from conversation using dataset as reference
        Returns: (classification, confidence)
        """
        try:
            all_user_msgs = [m.content for m in chat_history if m.role == "user"]
            all_user_msgs.append(current_message)
            
            conversation_text = "\n".join([f"- {msg}" for msg in all_user_msgs])
            
            # Build prompt with dataset context
            prompt = f"""You are a mental health classifier. Analyze the user messages and determine their mental health state.

=== USER MESSAGES ===
{conversation_text}

=== REFERENCE PATTERNS FROM MENTAL HEALTH DATABASE ===
{context if context else "No specific reference found."}

=== CLASSIFICATION TASK ===
Based on the user messages AND comparing them with the reference patterns from the database above, classify into ONE of these categories:

- Anxiety (signs: excessive worry, panic, nervousness, fear of future, racing thoughts)
- Depression (signs: persistent sadness, hopelessness, no energy, loss of interest, emptiness)
- Stress (signs: overwhelmed, pressure, burnout, tension, inability to cope)
- Bipolar (signs: mood swings, extreme highs and lows, manic episodes)
- Personality Disorder (signs: identity issues, unstable relationships, emotional dysregulation)
- Suicidal (signs: thoughts of death, self-harm, wanting to end life)
- Normal (no significant mental health concerns, just casual conversation)

=== INSTRUCTIONS ===
1. Compare the user's language patterns with the reference patterns from the database
2. Look for matching symptoms, emotions, and expressions
3. Rate your confidence from 0.0 to 1.0 based on how closely the user messages match the database patterns
4. Higher confidence = stronger match with database patterns

Reply ONLY in this exact format:
CLASSIFICATION: [category]
CONFIDENCE: [0.0-1.0]"""

            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a mental health classifier. Use the reference database patterns to accurately classify user messages. Compare user expressions with database patterns to determine classification and confidence. Output only the requested format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            result = response.choices[0].message.content.strip()
            
            classification = "Normal"
            confidence = 0.5
            
            for line in result.split('\n'):
                if line.startswith('CLASSIFICATION:'):
                    raw_class = line.replace('CLASSIFICATION:', '').strip()
                    valid_classes = ["Anxiety", "Depression", "Stress", "Bipolar", "Personality Disorder", "Suicidal", "Normal"]
                    for vc in valid_classes:
                        if vc.lower() in raw_class.lower():
                            classification = vc
                            break
                elif line.startswith('CONFIDENCE:'):
                    try:
                        conf_str = line.replace('CONFIDENCE:', '').strip()
                        confidence = float(conf_str)
                        confidence = max(0.0, min(1.0, confidence))
                    except:
                        confidence = 0.5
            
            return classification, confidence
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return "Normal", 0.3
    
    def _generate_response(
        self, 
        user_message: str, 
        context: str, 
        chat_history: List[ChatMessage],
        is_crisis: bool = False
    ) -> str:
        """Generate natural, friendly chatbot response using knowledge base"""
        try:
            if is_crisis:
                # Crisis mode - serious but supportive
                system = """You are a caring friend. The user may be in crisis.

YOUR PRIORITIES:
1. Show genuine care and concern
2. Validate their feelings without judgment
3. Provide crisis resources: 
   - National Suicide Prevention Lifeline: 988 (US)
   - Crisis Text Line: Text HOME to 741741
   - International: https://findahelpline.com
4. Encourage them to reach out to someone they trust
5. Stay with them in conversation

DO NOT lecture. DO NOT give generic advice. Just be present and caring."""

            else:
                # Normal mode - supportive friend using knowledge base
                system = """You are MindCare, a warm and supportive conversational companion.

=== HOW TO COMMUNICATE ===
- Talk like a close friend who listens, NOT like a psychologist or therapist
- Keep responses short and natural (2-3 sentences)
- Use casual but respectful language
- Ask follow-up questions to show genuine interest
- Validate feelings without judgment
- Match the user's language style and energy

=== USING THE KNOWLEDGE BASE ===
- You have access to a mental health knowledge base
- Use the information from the knowledge base to understand the user's situation
- If there's relevant information in the knowledge base, use it as reference for your response
- Deliver information naturally, DO NOT copy-paste or sound robotic
- Weave knowledge naturally into supportive conversation

=== WHAT NOT TO DO ===
- DO NOT mention diagnoses (anxiety, depression, stress, etc.)
- DO NOT say "based on our conversation..." or "according to the database..."
- DO NOT give disclaimers about seeking professional help
- DO NOT be overly formal or clinical
- DO NOT lecture or give long unsolicited advice
- DO NOT sound like a therapist or counselor

=== GOOD RESPONSE EXAMPLES ===
User: "I'm feeling really sad today"
Response: "Hey, I'm here for you. Want to talk about what's making you feel this way? 💙"

User: "I can't sleep lately"
Response: "Ugh, that's rough. Is there something on your mind keeping you up?"

User: "Work is so overwhelming"
Response: "That sounds exhausting. Are the deadlines piling up or is it something else?"

User: "I just need someone to talk to"
Response: "I'm right here. What's going on? You can share anything."

Remember: You're a FRIEND, not a doctor. Focus on LISTENING and BEING PRESENT."""

            messages = [{"role": "system", "content": system}]
            
            # Add knowledge base context if available
            if context:
                knowledge_prompt = f"""
=== KNOWLEDGE BASE REFERENCE ===
Use the following information from our mental health database to better understand and respond to the user.
DO NOT copy-paste this information. Use it naturally in your response.

{context}

Remember: Reference this knowledge naturally without mentioning "database" or "knowledge base" to the user.
"""
                messages.append({"role": "system", "content": knowledge_prompt})
            
            # Add chat history (last 10 messages)
            for msg in chat_history[-10:]:
                messages.append({"role": msg.role, "content": msg.content})
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return "I'm here for you. Want to tell me what's on your mind? 😊"
    
    def chat(
        self,
        user_message: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> RAGResponse:
        """
        Main chat method - natural conversation with background analysis
        Uses dataset for both classification and response generation
        """
        
        if chat_history is None:
            chat_history = []
        
        user_msg_count = len([m for m in chat_history if m.role == "user"]) + 1
        
        # Check for crisis keywords
        is_crisis = self._check_crisis(user_message)
        
        # Retrieve relevant context from dataset (ChromaDB)
        retrieved = self._retrieve_context(user_message)
        context = self._format_context(retrieved)
        
        # Log retrieved context for debugging
        logger.info(f"Retrieved {len(retrieved)} documents from knowledge base")
        if retrieved:
            logger.debug(f"Context preview: {context[:200]}...")
        
        # Analyze mental state using context from dataset
        classification, confidence = self._analyze_mental_state(chat_history, user_message, context)
        
        # Override if crisis detected
        if is_crisis:
            classification = "Suicidal"
            confidence = 1.0
        
        # Determine if should show status label
        show_label = (
            user_msg_count >= MIN_MESSAGES_FOR_LABEL and 
            confidence >= CONFIDENCE_THRESHOLD and
            classification != "Normal"
        ) or is_crisis
        
        # Create status label
        status_label = None
        if show_label:
            confidence_pct = int(confidence * 100)
            status_label = f"{classification} ({confidence_pct}%)"
        
        # Generate natural response using knowledge base
        answer = self._generate_response(
            user_message=user_message,
            context=context,
            chat_history=chat_history,
            is_crisis=is_crisis
        )
        
        return RAGResponse(
            answer=answer,
            classification=classification,
            confidence=confidence,
            retrieved_context=retrieved,
            is_crisis=is_crisis,
            status_label=status_label,
            show_label=show_label,
            message_count=user_msg_count
        )
    
    def get_crisis_response(self) -> str:
        """Get crisis resource response"""
        return """I'm really concerned about what you've shared. You matter, and help is available.

🆘 Please reach out now:
...ceritanya no darurat...

I'm here with you, but please also contact one of these resources. You don't have to go through this alone."""