from typing import Dict, Any
import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from .mcp import mcp
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("extract_links")


@mcp.tool(description=PROMPT)
def extract_links(url: str) -> Dict[str, Any]:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
        base_url = url

        soup = BeautifulSoup(html, "html.parser")

        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            text = a_tag.get_text(strip=True)

            if not href or href.startswith("javascript:"):
                continue

            if not href.startswith(("http://", "https://")):
                href = urljoin(base_url, href)

            links.append({"url": href, "text": text if text else href})

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


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="extract links from a url")
    parser.add_argument("url", help="url to fetch")
    args = parser.parse_args()

    result = extract_links(args.url)
    print(json.dumps(result, indent=2))
