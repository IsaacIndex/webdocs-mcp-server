import argparse
import logging
import os
import asyncio

from tools import mcp, scraper

parser = argparse.ArgumentParser(description="Web Scraper MCP Server")
parser.add_argument(
    "--log-level",
    default="WARNING",
    help="Logging level (debug, info, warning, error, critical)",
)
args, _ = parser.parse_known_args()

project_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(project_dir, "logs")
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
        asyncio.run(scraper.cleanup())
