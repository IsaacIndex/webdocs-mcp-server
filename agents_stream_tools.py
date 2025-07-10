import json
import logging
import os
from typing import Any, Callable, Dict, Iterable, List, Optional

import asyncio
import inspect

from rich.console import Console
from ollama import chat, ChatResponse

from tools import (
    open_in_user_browser,
    scrape_website,
    extract_links,
    download_pdfs_from_text,
    ping,
)

console = Console()

log_dir = os.path.join(os.path.expanduser("~"), "Documents", "webdocs-mcp-logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "agent.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
)
logger = logging.getLogger(__name__)


# Map tool names to their underlying functions for Ollama
TOOL_MAP: Dict[str, Callable[..., Any]] = {
    "open_in_user_browser": open_in_user_browser.fn,
    "scrape_website": scrape_website.fn,
    "extract_links": extract_links.fn,
    "download_pdfs_from_text": download_pdfs_from_text.fn,
    "ping": ping.fn,
}

def _invoke_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a tool by name and return its result."""
    func = TOOL_MAP.get(name)
    console.print(f"[cyan]Calling function: {name}[/cyan]")
    console.print(f"[cyan]Arguments: {args}[/cyan]")
    console.print()
    logger.info("calling function %s with args %s", name, args)
    if not func:
        return {"status": "error", "message": f"unknown tool {name}", "data": None}
    try:
        if inspect.iscoroutinefunction(func):
            return asyncio.run(func(**args))
        return func(**args)
    except Exception as exc:  # noqa: BLE001
        logger.exception("error during tool execution: %s", exc)
        return {"status": "error", "message": str(exc), "data": None}


def _stream_chat(messages: List[Dict[str, Any]]) -> Iterable[ChatResponse]:
    """Yield chat responses from Ollama with streaming enabled."""
    return chat(model="qwen3:8b", messages=messages, tools=list(TOOL_MAP.values()), stream=True)


DEFAULT_SYSTEM_PROMPT = (
    "The web scraper defaults to Playwright mode. "
    "Use Selenium only when a user explicitly requests cookie-based browsing."
)


def run(query: str) -> None:
    """Stream a response, executing tools as needed."""
    logger.info("received query: %s", query)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    in_think = False

    while True:
        final: Optional[ChatResponse] = None
        tool_calls = []
        output_buffer = ""

        for chunk in _stream_chat(messages):
            final = chunk
            if chunk.message.content:
                text = chunk.message.content
                output_buffer += text
                if "<think>" in text:
                    in_think = True
                style = "yellow" if in_think else "green"
                if "</think>" in text:
                    in_think = False
                console.print(text, end="", style=style)
            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)
        console.print()
        if output_buffer:
            logger.info("agent output: %s", output_buffer)

        if not final:
            break
        messages.append(final.message.model_dump())

        if not tool_calls:
            break

        for call in tool_calls:
            name = call.function.name
            args = call.function.arguments or {}
            result = _invoke_tool(name, args)
            messages.append({"role": "tool", "name": name, "content": json.dumps(result)})


if __name__ == "__main__":
    import sys
    from tools.webscraper import scraper

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    logger.info("starting agent")
    try:
        run(query)
    finally:
        scraper.cleanup()
        logger.info("agent shutdown")
