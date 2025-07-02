from typing import Dict, Any
import logging

from .mcp import mcp
from .webscraper import scraper

logger = logging.getLogger(__name__)


@mcp.tool
def scrape_website(url: str) -> Dict[str, Any]:
    """Scrape content from a specified URL"""
    try:
        content = scraper.fetch_content(url)
        return {
            "status": "success",
            "no. of characters": len(content),
            "message": "Website content scraped successfully",
            "data": {"content": content},
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": None,
        }
