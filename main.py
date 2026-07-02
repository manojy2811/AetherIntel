import asyncio
import json
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from config import settings
from db import get_db
from schemas import ResearchRequest, HumanApprovalRequest
from state import ResearchState

# Logging setup
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("research_engine")

app = FastAPI(
    title="Enterprise Cognitive Research Engine (CRE)",
    description="Gemini-Powered Multi-Agent Market Intelligence System",
    version="1.0.0"
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LangGraph checkpointer initialization (Mock/PostgresSaver preparation)
# Note: In Phase 3, we will fully wire up PostgresSaver with active threads.
# For Phase 1 base, we provide a placeholder connection check/setup.
checkpoint_saver = None
try:
    from langgraph.checkpoint.memory import MemorySaver
    checkpoint_saver = MemorySaver()
    logger.info("Initialized memory saver checkpoint for base graph state management.")
except Exception as e:
    logger.error(f"Failed to initialize memory checkpointer: {e}")

@app.on_event("startup")
async def startup_event():
    logger.info("CRE Backend is starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("CRE Backend is shutting down...")

async def dummy_sse_generator(request: ResearchRequest) -> AsyncGenerator[str, None]:
    """Generates dummy SSE events to simulate LangGraph worker updates."""
    try:
        # 1. Start Event
        yield f"event: agent_start\ndata: {json.dumps({'message': 'Starting research workflow...', 'query': request.research_query})}\n\n"
        await asyncio.sleep(1)

        # 2. Tool Call Simulated Event
        yield f"event: tool_call\ndata: {json.dumps({'tool': 'Tavily Search', 'input': request.research_query})}\n\n"
        await asyncio.sleep(1.5)

        # 3. Token Stream Simulation
        tokens = ["Analyzing", " market", " trends", " and", " competitive", " landscape", " using", " Gemini..."]
        for token in tokens:
            yield f"event: token_stream\ndata: {json.dumps({'token': token})}\n\n"
            await asyncio.sleep(0.2)

        # 4. Success / Done Event
        final_report = f"# Research Report: {request.research_query}\n\nThis is a baseline generated market intelligence report."
        yield f"event: graph_end\ndata: {json.dumps({'report_markdown': final_report, 'status': 'completed'})}\n\n"

    except asyncio.CancelledError:
        logger.warning("Stream request cancelled by user.")
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

@app.post("/api/v1/research/stream")
async def stream_research(request: ResearchRequest):
    """
    Initiates research engine streaming responses via Server-Sent Events (SSE).
    """
    if not request.research_query.strip():
        raise HTTPException(status_code=400, detail="Research query cannot be empty.")
    
    return StreamingResponse(
        dummy_sse_generator(request),
        media_type="text/event-stream"
    )

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "Enterprise Cognitive Research Engine"}
