from typing import Dict, Any, List
import logging
import os
import re
import requests

from .mcp import mcp

logger = logging.getLogger(__name__)


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
