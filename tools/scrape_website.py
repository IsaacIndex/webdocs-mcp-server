from typing import Dict, Any
import logging

from .mcp import mcp
from .webscraper import scraper
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("scrape_website")


@mcp.tool(description=PROMPT)
def scrape_website(url: str) -> Dict[str, Any]:
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


scrape_website.__doc__ = PROMPT
