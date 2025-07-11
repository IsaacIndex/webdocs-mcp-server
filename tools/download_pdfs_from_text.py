from typing import Dict, Any, List
import logging
import os
import re
import requests

from .mcp import mcp
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("download_pdfs_from_text")


@mcp.tool(description=PROMPT)
def download_pdfs_from_text(text: str) -> Dict[str, Any]:
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


download_pdfs_from_text.__doc__ = PROMPT


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="download pdf files referenced in text"
    )
    parser.add_argument("input", help="text or path to a file containing text")
    parser.add_argument(
        "--file",
        action="store_true",
        help="treat input argument as a file path",
    )
    args = parser.parse_args()

    text = Path(args.input).read_text() if args.file else args.input
    result = download_pdfs_from_text(text)
    print(json.dumps(result, indent=2))
