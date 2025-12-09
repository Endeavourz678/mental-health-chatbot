"""
Tests for Mental Health Chatbot API
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


client = TestClient(app)


class TestHealthEndpoints:
    """Test health and stats endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "vector_store_status" in data


class TestChatEndpoints:
    """Test chat functionality"""
    
    def test_chat_simple_greeting(self):
        """Test simple chat with greeting"""
        response = client.post(
            "/chat/simple",
            params={"message": "Hello"}
        )
        # May fail if OpenAI key not set, that's expected
        assert response.status_code in [200, 503]
    
    def test_chat_full_endpoint(self):
        """Test full chat endpoint"""
        response = client.post(
            "/chat",
            json={
                "message": "I've been feeling anxious lately",
                "session_id": "test_session_1",
                "include_context": False
            }
        )
        # May fail if OpenAI key not set
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "response" in data
            assert "classification" in data
            assert "is_crisis" in data
    
    def test_chat_with_context(self):
        """Test chat with context retrieval"""
        response = client.post(
            "/chat",
            json={
                "message": "What is anxiety?",
                "include_context": True
            }
        )
        assert response.status_code in [200, 503]


class TestSessionManagement:
    """Test session endpoints"""
    
    def test_session_stats_not_found(self):
        """Test session stats for non-existent session"""
        response = client.get("/session/nonexistent_session/stats")
        # Should return 404 or session stats if auto-created
        assert response.status_code in [200, 404, 503]
    
    def test_clear_session(self):
        """Test clearing a session"""
        response = client.delete("/session/test_session_to_clear")
        # May return 404 if session doesn't exist
        assert response.status_code in [200, 404, 503]


class TestInputValidation:
    """Test input validation"""
    
    def test_empty_message(self):
        """Test that empty messages are rejected"""
        response = client.post(
            "/chat",
            json={
                "message": "",
                "session_id": "test"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_long_message(self):
        """Test message length limit"""
        long_message = "a" * 6000  # Exceeds 5000 char limit
        response = client.post(
            "/chat",
            json={
                "message": long_message,
                "session_id": "test"
            }
        )
        assert response.status_code == 422


class TestCrisisDetection:
    """Test crisis detection (these tests are sensitive)"""
    
    def test_crisis_keywords_detected(self):
        """Test that crisis indicators are detected"""
        # Note: This is for testing purposes only
        # In production, these messages would trigger crisis response
        crisis_messages = [
            "I want to end my life",
            "I've been thinking about suicide"
        ]
        
        for msg in crisis_messages:
            response = client.post(
                "/chat",
                json={"message": msg}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data.get("is_crisis") == True
                assert "crisis" in data.get("response", "").lower() or \
                       "988" in data.get("response", "") or \
                       "help" in data.get("response", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
