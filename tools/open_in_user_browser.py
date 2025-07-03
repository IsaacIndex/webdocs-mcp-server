from typing import Dict, Any
import logging
from selenium.webdriver.chrome.options import Options

from .mcp import mcp
from .webscraper import chrome_options, create_driver

logger = logging.getLogger(__name__)


@mcp.tool
def open_in_user_browser(url: str) -> Dict[str, Any]:
    """Open a URL in the user's regular Chrome profile. the url MUST start with https://, prepend if not available"""
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
