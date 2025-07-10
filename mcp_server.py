import argparse
import logging
import os

from tools import mcp, scraper

parser = argparse.ArgumentParser(description="Web Scraper MCP Server")
parser.add_argument(
    "--log-level",
    default="WARNING",
    help="Logging level (debug, info, warning, error, critical)",
)
args, _ = parser.parse_known_args()

log_dir = os.path.join(os.path.expanduser("~"), "Documents", "webdocs-mcp-logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "mcp.log")
log_level = getattr(logging, args.log_level.upper(), logging.WARNING)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
)


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        scraper.cleanup()
