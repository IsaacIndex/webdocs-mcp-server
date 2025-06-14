from fastmcp import FastMCP
from typing import Dict, Any, List
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException
import re
import time
import os
from urllib.parse import urljoin
import sys
import requests

# Configure logging
log_file = os.path.join(os.path.expanduser("~"), "Downloads", "mcp.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Chrome options
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

# Initialize FastMCP
mcp = FastMCP("Web Scraper MCP 🚀")


def _get_chrome_profile_path() -> str:
    """Return the default Chrome user profile path based on the OS."""
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "Google", "Chrome")
    if sys.platform.startswith("linux"):
        return os.path.join(home, ".config", "google-chrome")
    if sys.platform.startswith("win"):
        return os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data")
    raise RuntimeError("Unsupported operating system for locating Chrome profile")


class WebScraper:
    def __init__(self):
        self.driver = None
        # Elements to remove from the content
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
        try:
            logger.info("Initializing Chrome WebDriver...")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
            self.driver = None

    def _ensure_driver(self):
        if self.driver:
            return
        try:
            logger.info("Attempting to reinitialize Chrome WebDriver...")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logger.info("Chrome WebDriver reinitialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize Chrome WebDriver: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        # Remove multiple punctuation
        text = re.sub(r'([.,!?-])\1+', r'\1', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _is_relevant_content(self, text: str) -> bool:
        """Check if the text content is relevant."""
        # Minimum content length
        if len(text) < 20:
            return False
        for pattern in self.non_content_patterns:
            if pattern.search(text):
                return False
        return True

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from the page."""
        # Remove unwanted elements
        for element in self.unwanted_elements:
            for tag in soup.find_all(element):
                tag.decompose()

        # Remove elements with unwanted classes
        for class_pattern in self.unwanted_class_patterns:
            for tag in soup.find_all(class_=class_pattern):
                tag.decompose()

        # Try to find the main content area
        main_content = None
        for tag in ['article', 'main', 'div[role="main"]', '.content', '#content']:
            main_content = soup.select_one(tag)
            if main_content:
                break

        # If no main content found, use the body
        if not main_content:
            main_content = soup.body

        return main_content.get_text(separator='\n', strip=True) if main_content else ''

    def extract_links(self, url: str) -> List[Dict[str, str]]:
        """Extract all links from the webpage."""
        self._ensure_driver()

        try:
            logger.info(f"Extracting links from URL: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            time.sleep(2)  # Shorter wait time for links

            # Get the page source and parse with BeautifulSoup
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract all links
            links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                text = a_tag.get_text(strip=True)

                # Skip empty links and javascript:void(0)
                if not href or href.startswith('javascript:'):
                    continue

                # Make relative URLs absolute
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

    def fetch_content(self, url: str) -> str:
        self._ensure_driver()

        try:
            logger.info(f"Fetching content from URL: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            time.sleep(5)

            # Get the page source and parse with BeautifulSoup
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract main content
            text = self._extract_main_content(soup)

            # Clean and process the text
            lines = text.split('\n')
            cleaned_lines = []

            for line in lines:
                cleaned_line = self._clean_text(line)
                if self._is_relevant_content(cleaned_line):
                    cleaned_lines.append(cleaned_line)

            # Join lines and remove duplicate content
            text = '\n'.join(cleaned_lines)
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove multiple newlines

            # Optional: Detect language and filter non-English content
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

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome WebDriver cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during WebDriver cleanup: {str(e)}")


@mcp.tool
def open_in_user_browser(url: str) -> Dict[str, Any]:
    """Open a URL in the user's regular Chrome profile."""
    try:
        profile = _get_chrome_profile_path()
        options = Options()
        options.add_argument(f"--user-data-dir={profile}")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        return {
            "status": "success",
            "message": f"Opened {url} in the user browser",
            "data": None,
        }
    except Exception as e:
        logger.error(f"Failed to open browser for {url}: {str(e)}")
        return {"status": "error", "message": str(e), "data": None}


# Initialize WebScraper
scraper = WebScraper()


@mcp.tool
def scrape_website(url: str) -> Dict[str, Any]:
    """Scrape content from a specified URL"""
    try:
        content = scraper.fetch_content(url)
        return {
            "status": "success",
            "no. of characters": len(content),
            "message": "Website content scraped successfully",
            "data": {"content": content}
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": None
        }


@mcp.tool
def extract_links(url: str) -> Dict[str, Any]:
    """Extract all links from a specified URL"""
    try:
        links = scraper.extract_links(url)
        return {
            "status": "success",
            "no. of links": len(links),
            "message": "Links extracted successfully",
            "data": {"links": links}
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": None
        }


@mcp.tool
def download_pdfs_from_text(text: str) -> Dict[str, Any]:
    """Download all PDF links found in the provided text."""
    try:
        pdf_pattern = re.compile(r"https?://[^\s'\"<>]+?\.pdf", re.IGNORECASE)
        links = pdf_pattern.findall(text)
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(download_dir, exist_ok=True)
        downloaded_files: List[str] = []

        for link in links:
            # Remove trailing punctuation
            clean_link = link.rstrip(').,')
            file_name = os.path.basename(clean_link.split("?")[0])
            file_path = os.path.join(download_dir, file_name)
            logger.info(f"Downloading PDF from {clean_link} to {file_path}")
            response = requests.get(clean_link, timeout=30)
            response.raise_for_status()
            with open(file_path, "wb") as pdf_file:
                pdf_file.write(response.content)
            downloaded_files.append(file_path)

        return {
            "status": "success",
            "no. of files": len(downloaded_files),
            "message": "PDF files downloaded" if downloaded_files else "No PDF links found",
            "data": {"files": downloaded_files},
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": None,
        }

@mcp.tool
def ping() -> Dict[str, Any]:
    """Check if the server is responsive"""
    return {
        "status": "success",
        "message": "Pong",
        "data": {"timestamp": time.time()}
    }


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        scraper.cleanup()
