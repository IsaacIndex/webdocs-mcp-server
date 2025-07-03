from typing import Dict, Any
import logging
from selenium.webdriver.chrome.options import Options

from .mcp import mcp
from .webscraper import _get_chrome_profile_path, create_driver

logger = logging.getLogger(__name__)


@mcp.tool
def open_in_user_browser(url: str) -> Dict[str, Any]:
    """Open a URL in the user's regular Chrome profile."""
    try:
        profile = _get_chrome_profile_path()
        options = Options()
        options.add_argument(f"--user-data-dir={profile}")
        driver = create_driver(options)
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
