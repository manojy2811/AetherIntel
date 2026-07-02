import logging
from pydantic import BaseModel, Field
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.state import ResearchState

logger = logging.getLogger("research_engine.agents.critic")

class EvaluationResult(BaseModel):
    is_satisfactory: bool = Field(
        ..., 
        description="Whether the report meets all enterprise intelligence standard criteria and contains sufficient factual details."
    )
    report_markdown: str = Field(
        ..., 
        description="The full synthesized markdown report incorporating findings, data, and charts."
    )
    feedback: Optional[str] = Field(
        None, 
        description="If is_satisfactory is False, specify detailed instructions of what is missing or needs expansion."
    )

def get_critic_node():
    """
    Initializes and returns the Critic Evaluation Node.
    Uses gemini-2.5-pro with structured output.
    """
    api_key = settings.GOOGLE_API_KEY
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=api_key,
        temperature=0.1
    )
    
    structured_llm = model.with_structured_output(EvaluationResult)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are the Lead Critic and Editor for the Enterprise Cognitive Research Engine.\n"
         "Your task is to synthesize the final markdown report and evaluate its quality.\n\n"
         "CRITERIA FOR A PREMIUM REPORT:\n"
         "1. Must have a clear title (H1) and structured headings (H2/H3).\n"
         "2. Must integrate quantitative data/metrics collected by the Analyst.\n"
         "3. Must contain deep qualitative facts and context gathered by the Researcher.\n"
         "4. Must be thorough, professional, and contain no placeholder comments or TODOs.\n\n"
         "If the report lacks sufficient depth or metrics, set `is_satisfactory` to False "
         "and provide precise actionable instructions in `feedback` so the team can fetch the missing data."
        ),
        ("human",
         "Research Query: {research_query}\n\n"
         "Collected Raw Data:\n{raw_data}\n\n"
         "Collected Financial Metrics:\n{metrics}\n\n"
         "Current Report Version: {report_markdown}\n\n"
         "Please synthesize the final report and evaluate it."
        )
    ])
    
    critic_chain = prompt | structured_llm
    
    def critic_node(state: ResearchState) -> dict:
        logger.info("Critic editor node invoked...")
        
        raw_data_summary = "\n".join([
            f"- [{d.get('source')}]: {d.get('content')[:500]}..." 
            for d in (state.get("gathered_raw_data") or [])
        ])
        
        metrics_summary = str(state.get("financial_metrics") or {})
        
        try:
            result = critic_chain.invoke({
                "research_query": state.get("research_query"),
                "raw_data": raw_data_summary or "No web data collected yet.",
                "metrics": metrics_summary or "No financial metrics collected yet.",
                "report_markdown": state.get("report_markdown") or "None"
            })
            
            logger.info(f"Critic Evaluation: satisfactory={result.is_satisfactory} | feedback={result.feedback}")
            
            status = "Report approved by Critic Node." if result.is_satisfactory else "Report rejected by Critic Node: requesting revisions."
            
            return {
                "report_markdown": result.report_markdown,
                "feedback": result.feedback if not result.is_satisfactory else None,
                "current_status": status,
                "agent_history": [{
                    "node": "critic",
                    "message": f"Critic evaluation complete. Satisfactory={result.is_satisfactory}. Feedback: {result.feedback or 'None'}"
                }]
            }
        except Exception as e:
            logger.error(f"Critic node invocation failed: {e}")
            return {
                "current_status": f"Critic evaluation error: {str(e)}",
                "agent_history": [{"node": "critic", "message": f"Evaluation error: {str(e)}"}]
            }
            
    return critic_node
