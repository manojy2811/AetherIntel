from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ResearchRequest(BaseModel):
    research_query: str = Field(..., description="The query/topic to research.")
    thread_id: Optional[str] = Field(None, description="Thread ID for continuing research or using a checkpoint.")

class HumanApprovalRequest(BaseModel):
    thread_id: str = Field(..., description="The thread/session ID being approved.")
    approved: bool = Field(..., description="Whether to approve the current state.")
    feedback: Optional[str] = Field(None, description="Feedback or guidance if rejected or modified.")

class CheckpointStateResponse(BaseModel):
    thread_id: str
    checkpoint_id: str
    values: Dict[str, Any]
    next_node: Optional[str]
    history: List[Dict[str, Any]]
