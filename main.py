import argparse
import logging
import os

from tools import mcp, scraper

parser = argparse.ArgumentParser(description="Web Scraper MCP Server")
parser.add_argument(
    "--log-level",
    default="INFO",
    help="Logging level (debug, info, warning, error, critical)",
)
args, _ = parser.parse_known_args()

log_file = os.path.join(os.path.expanduser("~"), "Downloads", "mcp.log")
log_level = getattr(logging, args.log_level.upper(), logging.INFO)
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
