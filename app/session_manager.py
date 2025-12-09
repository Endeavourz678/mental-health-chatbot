"""
Session management for maintaining conversation history
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from collections import OrderedDict

from models import ChatMessage


logger = logging.getLogger(__name__)


class SessionManager:
    """
    In-memory session manager for conversation history
    Simple version without threading locks to avoid deadlock
    """
    
    def __init__(
        self,
        max_sessions: int = 10000,
        session_ttl_hours: int = 24,
        max_messages_per_session: int = 100
    ):
        self.sessions: Dict[str, Dict] = {}
        self.max_sessions = max_sessions
        self.session_ttl = timedelta(hours=session_ttl_hours)
        self.max_messages = max_messages_per_session
        
        logger.info(f"Initialized SessionManager with max_sessions={max_sessions}")
    
    def _get_or_create_session(self, session_id: str) -> Dict:
        """Get session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'session_id': session_id,
                'messages': [],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'metadata': {}
            }
        return self.sessions[session_id]
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        classification: Optional[str] = None,
        is_crisis: bool = False
    ) -> None:
        """Add a message to session history"""
        session = self._get_or_create_session(session_id)
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow(),
            'classification': classification,
            'is_crisis': is_crisis
        }
        
        session['messages'].append(message)
        session['updated_at'] = datetime.utcnow()
        
        # Trim if too many messages
        if len(session['messages']) > self.max_messages:
            session['messages'] = session['messages'][-self.max_messages:]
    
    def get_chat_history(self, session_id: str) -> List[ChatMessage]:
        """Get chat history as ChatMessage objects"""
        session = self._get_or_create_session(session_id)
        
        return [
            ChatMessage(role=msg['role'], content=msg['content'])
            for msg in session['messages']
        ]
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        return len(self.sessions)
    
    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get statistics for a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        messages = session['messages']
        crisis_count = sum(1 for m in messages if m.get('is_crisis', False))
        
        classifications = {}
        for msg in messages:
            if msg.get('classification'):
                cls = msg['classification']
                classifications[cls] = classifications.get(cls, 0) + 1
        
        return {
            'session_id': session_id,
            'message_count': len(messages),
            'crisis_detections': crisis_count,
            'classifications': classifications,
            'created_at': session['created_at'].isoformat(),
            'updated_at': session['updated_at'].isoformat()
        }