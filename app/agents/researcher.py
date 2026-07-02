import logging
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.state import ResearchState
from app.tools.scraper import search_web, scrape_website

logger = logging.getLogger("research_engine.agents.researcher")

def get_researcher_node():
    """
    Initializes and returns the Researcher Node.
    Uses gemini-2.5-flash with search/scraping tools.
    """
    api_key = settings.GOOGLE_API_KEY
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.2
    )
    
    # Bind tools to the model
    tools = [search_web, scrape_website]
    model_with_tools = model.bind_tools(tools)
    
    def researcher_node(state: ResearchState) -> dict:
        logger.info("Researcher agent node invoked...")
        query = state.get("research_query")
        history = state.get("agent_history") or []
        
        prompt = (
            f"You are an expert market intelligence researcher. Your goal is to gather high-quality "
            f"qualitative details, trends, and market information for the query: '{query}'.\n"
            f"Use the `search_web` tool to search for current news or industry dynamics. "
            f"If you find specific reports or websites with rich details, use `scrape_website` to extract their text.\n"
            f"Conduct at least one search, parse the results, and return your summarized findings as raw data. "
            f"Be detailed and professional."
        )
        
        try:
            # Let the model decide to use tools
            response = model_with_tools.invoke([
                SystemMessage(content=prompt),
                HumanMessage(content=f"Please research details related to: '{query}'")
            ])
            
            # Process tool calls if any
            gathered_items = []
            tool_calls_log = []
            
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call["args"]
                    tool_calls_log.append(f"Called {tool_name} with {args}")
                    
                    if tool_name == "search_web":
                        res = search_web.invoke(args)
                        for item in res:
                            gathered_items.append({
                                "source": item.get("url"),
                                "content": item.get("content"),
                                "type": "web_search",
                                "title": item.get("title")
                            })
                    elif tool_name == "scrape_website":
                        res = scrape_website.invoke(args)
                        gathered_items.append({
                            "source": args.get("url"),
                            "content": res,
                            "type": "web_scrape",
                            "title": "Webpage Scraping"
                        })
            
            # If no tool calls were generated, use the response content
            summary_message = response.content if not tool_calls_log else f"Executed research tools: {', '.join(tool_calls_log)}"
            if not response.tool_calls and response.content:
                gathered_items.append({
                    "source": "AI Researcher Brain",
                    "content": response.content,
                    "type": "general_knowledge",
                    "title": "Agent Research Synthesis"
                })
                
            return {
                "gathered_raw_data": gathered_items,
                "current_status": "Finished qualitative web research step.",
                "agent_history": [{
                    "node": "researcher",
                    "message": f"Researcher collected {len(gathered_items)} data entries. {summary_message}"
                }]
            }
            
        except Exception as e:
            logger.error(f"Researcher node run failed: {e}")
            return {
                "current_status": f"Researcher error: {str(e)}",
                "agent_history": [{"node": "researcher", "message": f"Execution failed: {str(e)}"}]
            }
            
    return researcher_node
