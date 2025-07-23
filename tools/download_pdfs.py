from typing import Dict, Any, List
import logging
import os
from urllib.parse import urlparse
import requests

from .mcp import mcp
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)

PROMPT = load_prompt("download_pdfs")


@mcp.tool(description=PROMPT)
def download_pdfs(links: List[str]) -> Dict[str, Any]:
    """Download PDF files from a list of links."""
    try:
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(download_dir, exist_ok=True)
        downloaded_files: List[str] = []

        for idx, link in enumerate(links):
            clean_link = link.rstrip(').,')
            parsed = urlparse(clean_link)
            file_name = os.path.basename(parsed.path.rstrip("/"))
            if not file_name:
                file_name = f"download_{idx}.pdf"
            elif not file_name.lower().endswith(".pdf"):
                file_name += ".pdf"
            file_path = os.path.join(download_dir, file_name)
            logger.info("Downloading PDF from %s to %s", clean_link, file_path)
            response = requests.get(clean_link, timeout=30)
            response.raise_for_status()
            with open(file_path, "wb") as pdf_file:
                pdf_file.write(response.content)
            downloaded_files.append(file_path)

        return {
            "status": "success",
            "no. of files": len(downloaded_files),
            "message": "PDF files downloaded" if downloaded_files else "No files downloaded",
            "data": {"files": downloaded_files},
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "message": str(e),
            "data": None,
        }


download_pdfs.__doc__ = PROMPT


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="download pdf files from provided links")
    parser.add_argument("links", nargs="*", help="list of pdf URLs")
    parser.add_argument("--file", action="store_true", help="treat positional arguments as a file containing links")
    args = parser.parse_args()

    if args.file:
        text = Path(args.links[0]).read_text()
        links = [line.strip() for line in text.splitlines() if line.strip()]
    else:
        links = args.links

    result = download_pdfs(links)
    print(json.dumps(result, indent=2))
