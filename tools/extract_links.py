from typing import Dict, Any
import logging

from .mcp import mcp
from .webscraper import scraper
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("extract_links")


@mcp.tool(description=PROMPT)
def extract_links(url: str) -> Dict[str, Any]:
    try:
        links = scraper.extract_links(url)
        return {
            "status": "success",
            "no. of links": len(links),
            "message": "Links extracted successfully",
            "data": {"links": links},
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": None,
        }


extract_links.__doc__ = PROMPT
