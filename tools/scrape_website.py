from typing import Dict, Any
import logging

from tools.mcp import mcp
from tools.webscraper import scraper
from tools.prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("scrape_website")


@mcp.tool(description=PROMPT)
async def scrape_website(url: str) -> Dict[str, Any]:
    try:
        content = await scraper.fetch_content(url)
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


if __name__ == "__main__":
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="scrape the main text of a website")
    parser.add_argument("url", help="page to scrape")
    args = parser.parse_args()

    result = asyncio.run(scrape_website(args.url))
    print(json.dumps(result, indent=2))
