import logging
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.state import ResearchState

logger = logging.getLogger("research_engine.agents.supervisor")

class RouterDecision(BaseModel):
    next_node: str = Field(
        ..., 
        description="The next node to execute. Options: 'researcher', 'analyst', 'critic', or 'FINISH'."
    )
    reasoning: str = Field(
        ..., 
        description="Justification explaining why this node is selected next."
    )

def get_supervisor_node():
    """
    Initializes and returns the Supervisor Router Node.
    Uses gemini-2.5-pro with structured output.
    """
    api_key = settings.GOOGLE_API_KEY
    # Initialize Google Gemini model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=api_key,
        temperature=0.1
    )
    
    # Force structured output mapping to Pydantic router decision schema
    structured_llm = model.with_structured_output(RouterDecision)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are the Enterprise Cognitive Research Supervisor.\n"
         "Your task is to orchestrate a team of specialized AI agents to generate a premium market intelligence report.\n"
         "Current query: {research_query}\n\n"
         "Agent Team:\n"
         "- researcher: Gathers real-time web news, facts, articles, and general web context.\n"
         "- analyst: Evaluates database financials, executes python math code/charts, and parses corporate spreadsheets.\n"
         "- critic: Performs synthesis, compiles report markdown, and audits quality against the goals.\n\n"
         "Your Job:\n"
         "Review the workflow progress, agent logs, gathered data, and decide which agent should act next.\n"
         "If the critic has finalized the report and no further corrections are needed, route to 'FINISH'.\n"
         "Do not loop infinitely; route to 'critic' once sufficient raw data and financial analysis are collected."
        ),
        ("human", 
         "Current State:\n"
         "Status: {current_status}\n"
         "Feedback from Critic/Human: {feedback}\n"
         "Gathered Raw Data Items: {data_count}\n"
         "Financial Metrics Collected: {metrics}\n"
         "History of steps: {agent_history}\n\n"
         "Select the next step."
        )
    ])
    
    # Bind the prompt and structured LLM
    supervisor_chain = prompt | structured_llm
    
    def supervisor_node(state: ResearchState) -> dict:
        logger.info("Supervisor router node invoked...")
        
        # Format variables
        data_count = len(state.get("gathered_raw_data") or [])
        metrics = str(state.get("financial_metrics") or {})
        history_summary = "\n".join([
            f"- Node {h.get('node')}: {h.get('message')}" 
            for h in (state.get("agent_history") or [])
        ])
        
        # If client / human sent an override, respect it
        override = state.get("next_node_override")
        if override:
            logger.info(f"Supervisor route overridden by state flag: {override}")
            return {
                "current_status": f"Routing override to {override}",
                "next_node_override": None,  # clear override
                "agent_history": [{"node": "supervisor", "message": f"Routed to {override} via user override."}],
                "next_node": override
            }
            
        try:
            decision = supervisor_chain.invoke({
                "research_query": state.get("research_query"),
                "current_status": state.get("current_status") or "initial",
                "feedback": state.get("feedback") or "None",
                "data_count": data_count,
                "metrics": metrics,
                "agent_history": history_summary or "Start of workflow"
            })
            
            logger.info(f"Supervisor Decision: {decision.next_node} | Reasoning: {decision.reasoning}")
            return {
                "current_status": f"Routing flow to {decision.next_node}",
                "agent_history": [{
                    "node": "supervisor", 
                    "message": f"Routed to {decision.next_node}. Reasoning: {decision.reasoning}"
                }],
                # We save the next node name directly into state for simple conditional edge lookup
                "feedback": None  # clear critic feedback once routed
            }
        except Exception as e:
            logger.error(f"Supervisor invocation failed: {e}. Defaulting routing to researcher.")
            return {
                "current_status": "Routing error, defaulting to researcher node",
                "agent_history": [{"node": "supervisor", "message": f"Routing failed: {str(e)}"}]
            }
            
    return supervisor_node
