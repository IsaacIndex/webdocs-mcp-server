import asyncio
import inspect
import json
import logging
import os
import re
from typing import Any, Callable, Dict, Iterable, List, Optional

from rich.console import Console
from ollama import chat, ChatResponse

from settings import get_setting
from tools import (
    open_in_user_browser,
    scrape_website,
    extract_links,
    download_pdfs,
)

AVAILABLE_TOOLS = [
    "open_in_user_browser",
    "scrape_website",
    "extract_links",
    "download_pdfs",
]

console = Console()

TRUNCATE_AT = 2000
FULL_OUTPUT_PLACEHOLDER = "<FULL_TOOL_OUTPUT>"

TOOL_PATTERN = re.compile(r"<tool>(.*?)</tool>", re.DOTALL)
PLAN_PATTERN = re.compile(r"<plan>(.*?)</plan>", re.DOTALL)

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

TOOL_MAP: Dict[str, Callable[..., Any]] = {
    "open_in_user_browser": open_in_user_browser,
    "scrape_website": scrape_website,
    "extract_links": extract_links,
    "download_pdfs": download_pdfs,
}

PLANNER_PROMPT = (
    "List the sequence of tools you will call. "
    "Available tools are: "
    + ", ".join(AVAILABLE_TOOLS)
    + ". Respond ONLY with <plan>[\"TOOL_NAME\", ...]</plan> using those names."
    "Do not put the <plan> tag inside <think>."
)

EXECUTOR_PROMPT = (
    "You are the execution agent for {tool}. Given the query and previous output, "
    "return one <tool>{{\"name\": \"{tool}\", \"args\": {{...}}}}</tool>. "
    "Do not put the <tool> tag inside <think>."
)

SUMMARY_PROMPT = (
    "You are the summarizer agent. Use the last tool output to answer the question "
    "in <final>ANSWER</final>. Do not wrap <final> inside <think>."
)

DEFAULT_SYSTEM_PROMPT = (
    "The web scraper defaults to Playwright mode. "
    "Use Selenium only when a user explicitly requests cookie-based browsing. "
    "Tool outputs may be truncated and might not be valid JSON. The full text is stored in memory. "
    f"Use {FULL_OUTPUT_PLACEHOLDER} to reference the previous full output when calling new tools."
    " DO NOT overthink, keep the reasoning straightforward."
)


def _extract_plan(text: str) -> List[str]:
    match = PLAN_PATTERN.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    pattern = "|".join(re.escape(t) for t in AVAILABLE_TOOLS)
    found: List[str] = []
    for m in re.finditer(pattern, text):
        tool = m.group(0)
        if tool not in found:
            found.append(tool)
    return found


def _invoke_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
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


def _minify_result(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") == "error":
        return {"error": result.get("message")}
    if "data" in result:
        return {"data": result["data"]}
    return {}


def _stream_chat(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    *,
    tools: Optional[List[Any]] = None,
) -> Iterable[ChatResponse]:
    model = model or get_setting("stream_model", "llama3.1:8b")
    if tools is None:
        tools = list(TOOL_MAP.values())
    return chat(model=model, messages=messages, tools=tools, stream=True)


def _collect(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    *,
    tools: Optional[List[Any]] = None,
) -> str:
    in_think = False
    output_buffer = ""
    for chunk in _stream_chat(messages, model=model, tools=tools):
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
