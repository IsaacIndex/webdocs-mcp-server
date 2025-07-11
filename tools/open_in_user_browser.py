from typing import Dict, Any
import logging
from selenium.webdriver.chrome.options import Options

from .mcp import mcp
from .webscraper import chrome_options, create_driver
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("open_in_user_browser")


@mcp.tool(description=PROMPT)
def open_in_user_browser(url: str) -> Dict[str, Any]:
    try:
        options = Options()
        for arg in chrome_options.arguments:
            if arg != "--headless":
                options.add_argument(arg)
        driver = create_driver(opts=options)
        driver.get(url)
        page_source = driver.page_source
        return {
            "status": "success",
            "message": f"Opened {url} in the user browser",
            "data": page_source,
        }
    except Exception as e:
        logger.error(f"Failed to open browser for {url}: {str(e)}")
        return {"status": "error", "message": str(e), "data": None}


open_in_user_browser.__doc__ = PROMPT


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="open a url in the user browser and return page source"
    )
    parser.add_argument("url", help="the page to open")
    args = parser.parse_args()

    result = open_in_user_browser(args.url)
    print(json.dumps(result, indent=2))
