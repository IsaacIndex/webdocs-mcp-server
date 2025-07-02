from typing import Dict, Any
import logging

from .mcp import mcp
from .webscraper import scraper

logger = logging.getLogger(__name__)


@mcp.tool
def extract_links(url: str) -> Dict[str, Any]:
    """Extract all links from a specified URL"""
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
