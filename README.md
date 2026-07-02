# Enterprise Cognitive Research Engine (CRE)

An autonomous market intelligence system powered by LangChain, LangGraph, and Google Gemini models.

## Project Structure

```
research-engine/
├── config.py         # Environment configurations via pydantic-settings
├── db.py             # SQLAlchemy session and engine setup
├── main.py           # FastAPI entrypoint and SSE stream endpoints
├── schemas.py        # Request & response validation schemas
├── state.py          # LangGraph global state & reducer definitions
├── .env.example      # Example environment variables
└── README.md         # Project documentation
```

## Features

- **Multi-Agent Swarm**: Coordinated research, data querying, and synthesis/evaluation using Gemini models.
- **State Management & Checkpointing**: Dynamic workflow routing using LangGraph with a persistent state engine.
- **Server-Sent Events (SSE)**: Real-time token streaming and agent transition notifications.

## Getting Started

1. Clone or copy files to your workspace directory.
2. Install Python dependencies:
   ```bash
   pip install fastapi uvicorn pydantic pydantic-settings langchain langchain-google-genai langgraph sqlalchemy psycopg2-binary
   ```
3. Copy `.env.example` to `.env` and fill in credentials:
   ```bash
   copy .env.example .env
   ```
4. Start the development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
