import httpx
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from app.config import settings

logger = logging.getLogger("research_engine.tools.scraper")

# Initialize Tavily search tool helper
@tool
def search_web(query: str) -> List[Dict[str, Any]]:
    """Search the web for real-time information and market intelligence on a given query."""
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        logger.warning("TAVILY_API_KEY is not set. Returning empty mock search results.")
        return [{"url": "https://example.com", "content": f"Mock data for search query: '{query}'"}]

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 5
        }
        response = httpx.post(url, json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        return [{"url": r.get("url"), "content": r.get("content"), "title": r.get("title")} for r in results]
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return [{"url": "error", "content": f"Search failed with error: {str(e)}"}]

@tool
def scrape_website(url: str) -> str:
    """Scrape and extract the text content of a specific web page URL for deep research analysis."""
    if not url.startswith("http"):
        return "Invalid URL format. URL must start with http:// or https://"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script, style, and navigation elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
            
        # Get clean text
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Limit response size to prevent context window explosion
        return clean_text[:8000]
    except Exception as e:
        logger.error(f"Web scraping failed for {url}: {e}")
        return f"Failed to scrape webpage at {url} due to error: {str(e)}"
