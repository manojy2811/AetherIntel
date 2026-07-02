import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.state import ResearchState
from app.agents.supervisor import get_supervisor_node
from app.agents.researcher import get_researcher_node
from app.agents.analyst import get_analyst_node
from app.agents.critic import get_critic_node

logger = logging.getLogger("research_engine.graph")

def route_next(state: ResearchState) -> str:
    """Conditional router mapping supervisor status state to graph nodes."""
    status = state.get("current_status") or ""
    if "researcher" in status:
        return "researcher"
    elif "analyst" in status:
        return "analyst"
    elif "critic" in status:
        return "critic"
    else:
        logger.info("Supervisor decided to terminate workflow.")
        return END

def compile_research_graph():
    """Assemble and compile the LangGraph workflow with memory persistence."""
    workflow = StateGraph(ResearchState)
    
    # Register Nodes
    workflow.add_node("supervisor", get_supervisor_node())
    workflow.add_node("researcher", get_researcher_node())
    workflow.add_node("analyst", get_analyst_node())
    workflow.add_node("critic", get_critic_node())
    
    # Add Edge from Start to Supervisor
    workflow.add_edge(START, "supervisor")
    
    # Add Hub & Spoke Routing from Supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "researcher": "researcher",
            "analyst": "analyst",
            "critic": "critic",
            END: END
        }
    )
    
    # Workers route back to Supervisor for next task assignment
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("analyst", "supervisor")
    workflow.add_edge("critic", "supervisor")
    
    # Configure checkpointer for time-travel state preservation
    checkpointer = MemorySaver()
    
    # Compile the graph executable with a Human interrupt after the Critic Node
    compiled_graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["critic"]
    )
    logger.info("LangGraph multi-agent swarm compiled successfully.")
    return compiled_graph

# Export compiled graph
graph = compile_research_graph()
