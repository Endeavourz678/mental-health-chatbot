# Mental Health Support Chatbot

A production-ready chatbot API for mental health support using RAG (Retrieval-Augmented Generation) with OpenAI.

## 🌟 Features

- **Mental Health Classification**: Automatically detects mental health indicators (Anxiety, Depression, Stress, etc.)
- **Crisis Detection**: Immediate detection of crisis situations with safety resources
- **RAG-powered Responses**: Context-aware responses using knowledge base
- **Session Management**: Maintains conversation history for continuity
- **Production Ready**: Docker support, health checks, structured logging

## 📁 Project Structure

```
mental-health-chatbot/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── schemas.py           # Pydantic models
│   └── session_manager.py   # Session handling
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration
├── data/
│   ├── dataset_qa.csv       # QA knowledge base
│   └── chroma_db/           # Vector store (auto-created)
├── models/
│   ├── __init__.py
│   └── rag_chain.py         # RAG implementation
├──public/
│   ├── index.html           # Run this for access our chatbot
│   ├── script.js
│   └── style.css
├── utils/
│   ├── __init__.py
│   ├── data_loader.py       # Data processing
│   └── vector_store.py      # ChromaDB wrapper
├── tests/
│   └── test_api.py          # API tests
├── .env.example
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Local Development

# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup API key
cp .env.example .env
# Edit .env → tambahkan OPENAI_API_KEY=sk-xxx

# 3. Run backend
python run.py

# 4. Open browser
http://localhost:3000

## 📡 API Endpoints

### Chat

**POST /chat**
```json
{
  "message": "I've been feeling anxious lately",
  "session_id": "user123",
  "include_context": false
}
```

Response:
```json
{
  "message_id": "msg_abc123",
  "response": "I hear that you've been experiencing anxiety...",
  "classification": "Anxiety",
  "confidence": 0.85,
  "is_crisis": false,
  "context": null
}
```

**POST /chat/simple**
```bash
curl -X POST "http://localhost:8000/chat/simple?message=Hello"
```

### Health & Stats

```bash
# Health check
curl http://localhost:8000/health

# Statistics
curl http://localhost:8000/stats
```

### Session Management

```bash
# Get session stats
curl http://localhost:8000/session/{session_id}/stats

# Clear session
curl -X DELETE http://localhost:8000/session/{session_id}
```

## 🧠 How It Works

### RAG Pipeline

1. **User Input** → Message received
2. **Crisis Check** → Immediate detection of crisis keywords
3. **Classification** → LLM classifies mental health state
4. **Retrieval** → Vector search for relevant knowledge
5. **Generation** → LLM generates contextual response
6. **Response** → Returns answer with classification

### Data Flow

```
User Message
     │
     ▼
┌─────────────┐
│ Crisis      │──── YES ──→ Crisis Response
│ Detection   │
└─────────────┘
     │ NO
     ▼
┌─────────────┐
│ Classify    │
│ Mental State│
└─────────────┘
     │
     ▼
┌─────────────┐     ┌──────────────┐
│ Retrieve    │────→│ Vector Store │
│ Context     │←────│ (ChromaDB)   │
└─────────────┘     └──────────────┘
     │
     ▼
┌─────────────┐
│ Generate    │
│ Response    │
└─────────────┘
     │
     ▼
  Response
```

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Required: OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model for generation |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `RETRIEVAL_TOP_K` | `5` | Number of documents to retrieve |
| `LOG_LEVEL` | `INFO` | Logging level |

## 📊 Adding Your Data

### QA Dataset Format (CSV)
```csv
id,question,answer,intent
1,What is anxiety?,Anxiety is a feeling of worry...,FACT-ANXIETY
```

### Statements Dataset Format (CSV)
```csv
,statement,status
0,I feel so worried all the time,Anxiety
1,I can't stop thinking about bad things,Anxiety
```

Place CSV files in `data/` directory and restart the server or call:
```bash
curl -X POST http://localhost:8000/index/reload
```


## 🔒 Security Notes

- Never expose API keys in code
- Use HTTPS in production
- Implement rate limiting for production
- Consider adding authentication
- Logs may contain sensitive information

## ⚠️ Disclaimer

This chatbot is designed for **supportive purposes only** and does **NOT** replace professional mental health care. If you or someone you know is in crisis:


---

Built with ❤️ for mental health awareness
