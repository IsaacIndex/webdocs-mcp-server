from typing import Dict, Any
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from .mcp import mcp
from .webscraper import _get_chrome_profile_path

logger = logging.getLogger(__name__)


@mcp.tool
def open_in_user_browser(url: str) -> Dict[str, Any]:
    """Open a URL in the user's regular Chrome profile."""
    try:
        profile = _get_chrome_profile_path()
        options = Options()
        options.add_argument(f"--user-data-dir={profile}")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
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
