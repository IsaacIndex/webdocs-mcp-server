import json
import logging
import os
from typing import Any, Callable, Dict, Iterable, List

import re
import asyncio
import inspect

from rich.console import Console
from ollama import chat, ChatResponse

from settings import get_setting

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

TOOL_PATTERN = re.compile(r"<tool>(.*?)</tool>", re.DOTALL)
PLAN_PATTERN = re.compile(r"<plan>(.*?)</plan>", re.DOTALL)
FINAL_PATTERN = re.compile(r"<final>(.*?)</final>", re.DOTALL)
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
    model = get_setting("stream_model", "llama3.1:8b")
    return chat(model=model, messages=messages, stream=True)

PLANNER_PROMPT = (
    "List the sequence of tools you will call. Respond with <plan>[\"TOOL_NAME\", ...]</plan>."
)

EXECUTOR_PROMPT = (
    "You are the execution agent for {tool}. Given the query and previous output, "
    "return one <tool>{\"name\": \"{tool}\", \"args\": {...}}</tool>."
)

SUMMARY_PROMPT = (
    "You are the summarizer agent. Use the last tool output to answer the question in <final>ANSWER</final>."
)



def _collect(messages: List[Dict[str, Any]]) -> str:
    """Stream chat and return the accumulated content."""
    in_think = False
    output_buffer = ""
    for chunk in _stream_chat(messages):
        if chunk.message.content:
            text = chunk.message.content
            output_buffer += text
            if "<think>" in text:
                in_think = True
            style = "yellow" if in_think else "green"
            if "</think>" in text:
                in_think = False
            console.print(text, end="", style=style)
    console.print()
    if output_buffer:
        logger.info("agent output: %s", output_buffer)
    return output_buffer


def run(query: str) -> None:
    """Stream a response using planner, executor, and summarizer."""
    logger.info("received query: %s", query)

    console.print("[bold blue]define plan[/bold blue]")
    plan_output = _collect([
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": query},
    ])
    match = PLAN_PATTERN.search(plan_output)
    plan: List[str] = json.loads(match.group(1)) if match else []

    last_output = ""
    for tool_name in plan:
        console.print(f"[bold blue]run {tool_name}[/bold blue]")
        args_output = _collect([
            {"role": "system", "content": EXECUTOR_PROMPT.format(tool=tool_name)},
            {"role": "user", "content": json.dumps({"query": query, "last_output": last_output})},
        ])
        match = TOOL_PATTERN.search(args_output)
        args = json.loads(match.group(1)).get("args", {}) if match else {}
        result = _invoke_tool(tool_name, args)
        last_output = json.dumps(result)
    console.print("[bold blue]summarize[/bold blue]")
    _collect([
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": json.dumps({"query": query, "last_output": last_output})},
    ])


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
