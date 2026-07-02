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
    Resumes from checkpoint if an active session exists.
    """
    thread_id = request.thread_id or "default_thread_session"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Check if there is already an existing state / checkpoint
    state_snapshot = await graph.aget_state(config)
    
    if state_snapshot and state_snapshot.next:
        # Resume execution
        inputs = None
        logger.info(f"Resuming thread {thread_id} from current checkpoint.")
    else:
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
        logger.info(f"Starting new research workflow for thread {thread_id}.")
    
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

        # Retrieve current state from checkpointer to verify if it was interrupted
        state_snapshot = await graph.aget_state(config)
        final_values = state_snapshot.values if state_snapshot else {}
        next_nodes = list(state_snapshot.next) if state_snapshot and state_snapshot.next else []

        if next_nodes:
            # Graph execution is paused (interrupted) e.g., on the critic node
            payload = {
                "next_nodes": next_nodes,
                "values": {
                    "report_markdown": final_values.get("report_markdown", ""),
                    "current_status": final_values.get("current_status", "interrupted"),
                    "feedback": final_values.get("feedback")
                }
            }
            yield f"event: graph_interrupt\ndata: {json.dumps(payload)}\n\n"
        else:
            # Finished completely
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

@app.post("/api/v1/research/approve")
async def approve_research(request: HumanApprovalRequest):
    """
    Approve or reject a research report, providing feedback to refine the agent swarm routing.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    state_snapshot = await graph.aget_state(config)
    
    if not state_snapshot or not state_snapshot.next:
        raise HTTPException(status_code=400, detail="No active graph execution or interrupt found for this thread.")
        
    feedback_text = request.feedback
    next_override = "supervisor"
    
    if not request.approved:
        if not feedback_text:
            feedback_text = "Rejected by human operator. Please revise the report."
        status_msg = f"Rejected by human operator: {feedback_text}"
    else:
        status_msg = "Approved by human operator."
        # If approved, we will tell the supervisor that it's approved by clearing feedback and letting supervisor route to END
        feedback_text = None
        
    # Update the graph state as if it came from the critic node
    await graph.aupdate_state(
        config,
        {
            "feedback": feedback_text,
            "next_node_override": next_override,
            "current_status": status_msg,
            "agent_history": [{
                "node": "human_operator",
                "message": f"Operator decision: approved={request.approved}. Feedback: {feedback_text}"
            }]
        },
        as_node="critic"
    )
    
    return {"status": "resumed", "approved": request.approved}

@app.get("/api/v1/research/history/{thread_id}")
async def get_research_history(thread_id: str):
    """
    Fetches checkpoint state history for time-travel navigation.
    """
    config = {"configurable": {"thread_id": thread_id}}
    history = []
    
    async for state in graph.aget_state_history(config):
        history.append({
            "checkpoint_id": state.config.get("configurable", {}).get("checkpoint_id"),
            "values": {
                "research_query": state.values.get("research_query"),
                "current_status": state.values.get("current_status"),
                "report_markdown": state.values.get("report_markdown"),
                "feedback": state.values.get("feedback")
            },
            "next": list(state.next) if state.next else []
        })
        
    return {"thread_id": thread_id, "history": history}

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "AetherIntel Engine"}
