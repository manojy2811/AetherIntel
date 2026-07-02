from typing import Annotated, Dict, Any, List, Optional
from typing_extensions import TypedDict
import operator

def append_reducer(left: list, right: list) -> list:
    """Thread-safe list append reducer."""
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right

def update_dict_reducer(left: dict, right: dict) -> dict:
    """Dict merger reducer."""
    if left is None:
        left = {}
    if right is None:
        right = {}
    return {**left, **right}

class ResearchState(TypedDict):
    research_query: str
    gathered_raw_data: Annotated[List[Dict[str, Any]], append_reducer]
    financial_metrics: Annotated[Dict[str, Any], update_dict_reducer]
    report_markdown: str
    agent_history: Annotated[List[Dict[str, Any]], append_reducer]
    current_status: str
    feedback: Optional[str]
    next_node_override: Optional[str]
