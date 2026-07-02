import logging
import json
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.state import ResearchState
from app.tools.sql import query_mock_database
from app.tools.interpreter import execute_python_code

logger = logging.getLogger("research_engine.agents.analyst")

def get_analyst_node():
    """
    Initializes and returns the Financial Data Analyst Node.
    Uses gemini-2.5-flash with SQL DB queries and Python Interpreter tool.
    """
    api_key = settings.GOOGLE_API_KEY
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.1
    )
    
    # Bind SQL and Python tools
    tools = [query_mock_database, execute_python_code]
    model_with_tools = model.bind_tools(tools)
    
    def analyst_node(state: ResearchState) -> dict:
        logger.info("Financial analyst agent node invoked...")
        query = state.get("research_query")
        
        prompt = (
            f"You are an expert Enterprise Financial Analyst. Your job is to extract financial numbers "
            f"and perform calculations for query/company: '{query}'.\n"
            f"Use the `query_mock_database` tool to inspect enterprise tables: 'company_financials' "
            f"and 'market_metrics'. Note: only query standard SQL SELECT syntax.\n"
            f"Use `execute_python_code` for math computations, trends, growth calculations, or forecasting models.\n"
            f"Output your final findings strictly inside a JSON block of key-value metrics so we can save it "
            f"to the global state (e.g. {{'revenue': 385.7, 'growth_cagr': 16.4}})."
        )
        
        try:
            response = model_with_tools.invoke([
                SystemMessage(content=prompt),
                HumanMessage(content=f"Query database and perform quantitative models for: '{query}'")
            ])
            
            # Execute tool calls
            metrics_captured = {}
            tool_logs = []
            
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call["args"]
                    tool_logs.append(f"Used {tool_name} with {args}")
                    
                    if tool_name == "query_mock_database":
                        db_res = query_mock_database.invoke(args)
                        # Try parsing or loading data into metrics
                        metrics_captured["db_raw_output"] = db_res
                    elif tool_name == "execute_python_code":
                        py_res = execute_python_code.invoke(args)
                        metrics_captured["python_calculation_output"] = py_res
            
            # Clean up or parse response text for JSON dictionary
            content_text = response.content or ""
            if "{" in content_text and "}" in content_text:
                try:
                    start_idx = content_text.find("{")
                    end_idx = content_text.rfind("}") + 1
                    json_str = content_text[start_idx:end_idx]
                    parsed_metrics = json.loads(json_str)
                    metrics_captured.update(parsed_metrics)
                except Exception:
                    pass
            
            if not metrics_captured:
                metrics_captured["summary"] = content_text or "No structured metrics parsed."
                
            return {
                "financial_metrics": metrics_captured,
                "current_status": "Completed financial database analysis.",
                "agent_history": [{
                    "node": "analyst",
                    "message": f"Analyst executed data queries: {', '.join(tool_logs) or 'No tools invoked'}. Captured metrics."
                }]
            }
            
        except Exception as e:
            logger.error(f"Analyst node execution failed: {e}")
            return {
                "current_status": f"Analyst error: {str(e)}",
                "agent_history": [{"node": "analyst", "message": f"Execution failed: {str(e)}"}]
            }
            
    return analyst_node
