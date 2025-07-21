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
    download_pdfs,
    ping,
)

console = Console()

TRUNCATE_AT = 2000
FULL_OUTPUT_PLACEHOLDER = "<FULL_TOOL_OUTPUT>"


def _minify_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce tool result size by dropping unnecessary fields."""
    if result.get("status") == "error":
        return {"error": result.get("message")}
    if "data" in result:
        return {"data": result["data"]}
    return {}


def _minify_tool_call(call: Any) -> Dict[str, Any]:
    """Remove extraneous fields from a tool call object."""
    data = call.model_dump()
    data.pop("id", None)
    data.pop("type", None)
    return data


def _trim_history(messages: List[Dict[str, Any]], plan_index: Optional[int]) -> Optional[int]:
    """Keep the system prompt, user query, initial plan and recent messages."""
    if plan_index is None:
        for i, msg in enumerate(messages):
            if msg.get("role") == "assistant":
                plan_index = i
                break

    keep = {0, 1}
    if plan_index is not None:
        keep.add(plan_index)
    start = max(len(messages) - 4, max(keep) + 1 if keep else 0)
    keep.update(range(start, len(messages)))
    messages[:] = [m for i, m in enumerate(messages) if i in keep]
    return plan_index


project_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(project_dir, "logs")
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
    "open_in_user_browser": open_in_user_browser,
    "scrape_website": scrape_website,
    "extract_links": extract_links,
    "download_pdfs": download_pdfs,
    "ping": ping,
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
    return chat(model="llama3.1:8b", messages=messages, tools=list(TOOL_MAP.values()), stream=True)


DEFAULT_SYSTEM_PROMPT = (
    "The web scraper defaults to Playwright mode. "
    "Use Selenium only when a user explicitly requests cookie-based browsing. "
    "Tool outputs may be truncated and might not be valid JSON. "
    "The full text is stored in memory. Use "
    f"{FULL_OUTPUT_PLACEHOLDER} to reference the previous full output when calling new tools."
    "DO NOT overthink, keep the reasoning straightforward"
)


def run(query: str) -> None:
    """Stream a response, executing tools as needed."""
    logger.info("received query: %s", query)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    in_think = False
    last_tool_output: Optional[str] = None
    plan_index: Optional[int] = None

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

        assistant_message = {"role": "assistant", "content": output_buffer}
        if tool_calls:
            assistant_message["tool_calls"] = [_minify_tool_call(c) for c in tool_calls]
        messages.append(assistant_message)

        if not tool_calls:
            plan_index = _trim_history(messages, plan_index)
            break

        for call in tool_calls:
            name = call.function.name
            args = call.function.arguments or {}
            # replace placeholder with the stored full tool output
            for key, value in list(args.items()):
                if isinstance(value, str) and FULL_OUTPUT_PLACEHOLDER in value:
                    args[key] = value.replace(FULL_OUTPUT_PLACEHOLDER, last_tool_output or "")

            result = _invoke_tool(name, args)
            minified = _minify_result(result)
            full_output = json.dumps(minified, separators=(",", ":"))
            last_tool_output = full_output
            truncated = full_output
            if len(full_output) > TRUNCATE_AT:
                omitted = len(full_output) - TRUNCATE_AT
                truncated = (
                    full_output[:TRUNCATE_AT]
                    + f"...\n[output truncated, {omitted} chars omitted; use {FULL_OUTPUT_PLACEHOLDER} for full output]"
                )
            messages.append({"role": "tool", "name": name, "content": truncated})

        plan_index = _trim_history(messages, plan_index)


if __name__ == "__main__":
    import sys
    from tools.webscraper import scraper

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    logger.info("starting agent")
    try:
        run(query)
    finally:
        asyncio.run(scraper.cleanup())
        logger.info("agent shutdown")
