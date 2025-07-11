import logging
import os
import re
import shutil
from typing import Optional, List, Dict
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from langdetect import detect, LangDetectException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
user_agent = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
)
chrome_options.add_argument(f'--user-agent={user_agent}')


def _get_chrome_binary() -> Optional[str]:
    """Return the Chrome executable path or None if not found."""
    env_binary = os.getenv("CHROME_BINARY")
    if env_binary and os.path.exists(env_binary):
        return env_binary

    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium-browser"),
        shutil.which("chrome"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def create_driver(opts: Optional[Options] = None) -> WebDriver:
    """Initialize and return a Chrome WebDriver."""
    options = opts or chrome_options
    binary = _get_chrome_binary()
    if binary:
        options.binary_location = binary
        logger.info(f"Using Chrome binary at {binary}")
    else:
        logger.warning("Chrome binary not found; relying on default discovery")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )


class WebScraper:
    def __init__(self, mode: str = "playwright") -> None:
        """Create a web scraper using either Selenium or Playwright."""
        self.mode = mode.lower()
        self.driver: Optional[WebDriver] = None
        self.unwanted_elements = [
            'script', 'style', 'nav', 'footer', 'header', 'aside',
            'iframe', 'noscript', 'svg', 'form', 'button', 'input',
            'meta', 'link', 'img', 'video', 'audio'
        ]
        self.unwanted_classes = [
            'menu', 'navigation', 'sidebar', 'footer', 'header',
            'advertisement', 'banner', 'cookie', 'popup', 'modal',
            'comment', 'social', 'share', 'related', 'recommended'
        ]
        self.unwanted_class_patterns = [re.compile(cls, re.IGNORECASE) for cls in self.unwanted_classes]
        self.non_content_patterns = [
            re.compile(r'^\s*$'),
            re.compile(r'^[0-9\s]+$'),
            re.compile(r'^[A-Z\s]+$'),
            re.compile(r'cookie|privacy|terms|conditions', re.IGNORECASE)
        ]
        if self.mode == "playwright":
            # Delay Playwright startup until first use so we can await it
            self.playwright = None
            self.browser = None
            self.page = None
            logger.info("WebScraper (async‑Playwright) will initialise on first request")
        else:
            try:
                logger.info("Initializing Chrome WebDriver...")
                self.driver = create_driver()
                logger.info("Chrome WebDriver initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
                self.driver = None

    async def _ensure_page(self) -> None:
        """Lazily start Playwright, browser and page (async‑safe)."""
        if self.page:
            return

        if not self.playwright:
            self.playwright = await async_playwright().start()

        if not self.browser:
            self.browser = await self.playwright.chromium.launch(headless=True)

        if not self.page:
            self.page = await self.browser.new_page()

    async def _ensure_driver(self) -> None:
        # NOTE: this method is now awaited by callers
        if self.mode == "playwright":
            await self._ensure_page()
        else:
            if self.driver:
                return
            try:
                logger.info("Attempting to reinitialize Chrome WebDriver...")
                self.driver = await asyncio.get_running_loop().run_in_executor(None, create_driver)
                logger.info("Chrome WebDriver reinitialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize Chrome WebDriver: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        text = re.sub(r'([.,!?-])\1+', r'\1', text)
        text = text.strip()
        return text

    def _is_relevant_content(self, text: str) -> bool:
        if len(text) < 20:
            return False
        for pattern in self.non_content_patterns:
            if pattern.search(text):
                return False
        return True

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        for element in self.unwanted_elements:
            for tag in soup.find_all(element):
                tag.decompose()

        for class_pattern in self.unwanted_class_patterns:
            for tag in soup.find_all(class_=class_pattern):
                tag.decompose()

        main_content = None
        for tag in ['article', 'main', 'div[role="main"]', '.content', '#content']:
            main_content = soup.select_one(tag)
            if main_content:
                break

        if not main_content:
            main_content = soup.body

        return main_content.get_text(separator='\n', strip=True) if main_content else ''

    async def extract_links(self, url: str) -> List[Dict[str, str]]:
        await self._ensure_driver()

        try:
            logger.info(f"Extracting links from URL: {url}")
            if self.mode == "playwright":
                assert self.page is not None
                await self.page.goto(url)
                await self.page.wait_for_load_state("load")
                await asyncio.sleep(2)
                html_content = await self.page.content()
            else:
                assert self.driver is not None
                await asyncio.get_running_loop().run_in_executor(None, self.driver.get, url)
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located(("tag name", "body"))
                )
                await asyncio.sleep(2)
                html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            links = []
            for a_tag in soup.find_all('a', href=True):
                if not isinstance(a_tag, Tag):
                    continue

                href_value = a_tag.get('href', '')
                if isinstance(href_value, list):
                    href = href_value[0] if href_value else ""
                else:
                    href = href_value or ""

                text = a_tag.get_text(strip=True)

                if not href or href.startswith('javascript:'):
                    continue

                if not href.startswith(('http://', 'https://')):
                    href = urljoin(url, href)

                links.append({
                    "url": href,
                    "text": text if text else href
                })

            logger.info(f"Successfully extracted {len(links)} links from {url}")
            return links
        except Exception as e:
            error_msg = f"Error extracting links from {url}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def fetch_content(self, url: str) -> str:
        await self._ensure_driver()

        try:
            logger.info(f"Fetching content from URL: {url}")
            if self.mode == "playwright":
                assert self.page is not None
                await self.page.goto(url)
                await self.page.wait_for_load_state("load")
                await asyncio.sleep(5)
                html_content = await self.page.content()
            else:
                assert self.driver is not None
                await asyncio.get_running_loop().run_in_executor(None, self.driver.get, url)
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located(("tag name", "body"))
                )
                await asyncio.sleep(5)
                html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            text = self._extract_main_content(soup)

            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                cleaned_line = self._clean_text(line)
                if self._is_relevant_content(cleaned_line):
                    cleaned_lines.append(cleaned_line)

            text = '\n'.join(cleaned_lines)
            text = re.sub(r'\n\s*\n', '\n\n', text)

            try:
                if detect(text) != 'en':
                    logger.warning(f"Non-English content detected from {url}")
            except LangDetectException:
                logger.warning(f"Could not detect language for content from {url}")

            logger.info(f"Successfully extracted and cleaned text content from {url}")
            return text
        except Exception as e:
            error_msg = f"Error fetching content from {url}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def cleanup(self) -> None:
        if self.mode == "playwright":
            if self.browser:
                try:
                    await self.browser.close()
                    logger.info("Playwright browser cleaned up successfully")
                except Exception as e:
                    logger.error(f"Error during Playwright cleanup: {str(e)}")
            if self.playwright:
                await self.playwright.stop()
        else:
            if self.driver:
                try:
                    await asyncio.get_running_loop().run_in_executor(None, self.driver.quit)
                    logger.info("Chrome WebDriver cleaned up successfully")
                except Exception as e:
                    logger.error(f"Error during WebDriver cleanup: {str(e)}")


# The scraper instance can be created synchronously; its heavy resources
# are loaded lazily when the first async method is awaited.
scraper = WebScraper()


if __name__ == "__main__":
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="basic cli for the WebScraper")
    parser.add_argument("url", help="page to fetch")
    parser.add_argument(
        "--mode",
        choices=["playwright", "selenium"],
        default="playwright",
        help="scraper mode",
    )
    parser.add_argument(
        "--links",
        action="store_true",
        help="extract links instead of text content",
    )
    args = parser.parse_args()

    scraper = WebScraper(mode=args.mode)
    try:
        if args.links:
            data = asyncio.run(scraper.extract_links(args.url))
        else:
            data = asyncio.run(scraper.fetch_content(args.url))
        print(json.dumps(data, indent=2))
    finally:
        asyncio.run(scraper.cleanup())
