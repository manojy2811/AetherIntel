import asyncio
import json
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from app.config import settings
from app.db import get_db
from app.schemas import ResearchRequest, HumanApprovalRequest
from app.state import ResearchState
from app.graph import graph
from app.tools.sql import seed_mock_database

# Logging setup
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("research_engine.main")

app = FastAPI(
    title="AetherIntel - Enterprise Cognitive Research Engine",
    description="LangGraph Multi-Agent intelligence swarm using Google Gemini.",
    version="2.0.0"
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Enterprise Cognitive Research Engine (CRE) Database...")
    # Seed mock enterprise database tables
    seed_mock_database()
    logger.info("CRE Startup initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("CRE Backend is shutting down...")

async def run_graph_stream(request: ResearchRequest) -> AsyncGenerator[str, None]:
    """
    Executes LangGraph asynchronously, broadcasting real-time SSE updates.
    """
    thread_id = request.thread_id or "default_thread_session"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initialize the input state
    inputs = {
        "research_query": request.research_query,
        "gathered_raw_data": [],
        "financial_metrics": {},
        "report_markdown": "",
        "agent_history": [],
        "current_status": "Starting multi-agent workflow.",
        "feedback": None,
        "next_node_override": None
    }
    
    try:
        # Stream events from LangGraph
        # We use astream_events (v2) to capture granular node operations, model streams, and outputs.
        async for event in graph.astream_events(inputs, config, version="v2"):
            kind = event.get("event")
            name = event.get("name")
            
            # 1. Agent/Node Starts
            if kind == "on_chain_start" and name in ["supervisor", "researcher", "analyst", "critic"]:
                payload = {
                    "agent": name,
                    "status": f"Starting node execution: {name}"
                }
                yield f"event: agent_start\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.05)
                
            # 2. Tool Calls
            elif kind == "on_tool_start":
                payload = {
                    "tool": name,
                    "input": event.get("data", {}).get("input")
                }
                yield f"event: tool_call\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.05)
                
            # 3. Model Token Streams (Gemini output generation)
            elif kind == "on_chat_model_stream":
                # Extract chunk content if available
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    payload = {"token": chunk.content}
                    yield f"event: token_stream\ndata: {json.dumps(payload)}\n\n"
                    
            # 4. Chain Ends for Worker Nodes
            elif kind == "on_chain_end" and name in ["supervisor", "researcher", "analyst", "critic"]:
                # Grab latest values output from state update
                output_data = event.get("data", {}).get("output", {})
                payload = {
                    "agent": name,
                    "output": output_data
                }
                yield f"event: agent_end\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.05)

        # Retrieve final state from checkpointer
        state_snapshot = await graph.aget_state(config)
        final_values = state_snapshot.values if state_snapshot else {}
        
        end_payload = {
            "report_markdown": final_values.get("report_markdown", ""),
            "status": final_values.get("current_status", "completed"),
            "agent_history": final_values.get("agent_history", [])
        }
        yield f"event: graph_end\ndata: {json.dumps(end_payload)}\n\n"

    except asyncio.CancelledError:
        logger.warning("Research stream execution client cancelled.")
    except Exception as e:
        logger.error(f"Graph stream error occurred: {e}")
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

@app.post("/api/v1/research/stream")
async def stream_research(request: ResearchRequest):
    """
    Initiates research engine streaming responses via Server-Sent Events (SSE).
    """
    if not request.research_query.strip():
        raise HTTPException(status_code=400, detail="Research query cannot be empty.")
    
    return StreamingResponse(
        run_graph_stream(request),
        media_type="text/event-stream"
    )

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "AetherIntel Engine"}
