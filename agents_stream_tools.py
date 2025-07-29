import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

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


@dataclass
class StreamingAgent:
    """Simple tool-based agent with a plan/execute/observe loop."""

    query: str
    messages: List[Dict[str, Any]] = field(init=False)
    plan_index: Optional[int] = field(default=None, init=False)
    last_tool_output: Optional[str] = field(default=None, init=False)
    in_think: bool = field(default=False, init=False)
    debug: bool = False

    def __post_init__(self) -> None:
        self.messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": self.query},
        ]
        if self.debug:
            console.print(f"[magenta]Initialized messages: {self.messages}[/magenta]")

    def define_plan(self) -> List[Any]:
        """Ask the model for the next plan and return tool calls."""
        return self._chat_step()

    def execute_plan(self, tool_calls: List[Any]) -> None:
        """Run the tools suggested by the model."""
        for call in tool_calls:
            name = call.function.name
            args = call.function.arguments or {}
            for key, value in list(args.items()):
                if isinstance(value, str) and FULL_OUTPUT_PLACEHOLDER in value:
                    args[key] = value.replace(
                        FULL_OUTPUT_PLACEHOLDER, self.last_tool_output or ""
                    )

            result = _invoke_tool(name, args, debug=self.debug)
            minified = _minify_result(result)
            full_output = json.dumps(minified, separators=(",", ":"))
            self.last_tool_output = full_output
            truncated = full_output
            if len(full_output) > TRUNCATE_AT:
                omitted = len(full_output) - TRUNCATE_AT
                truncated = (
                    full_output[:TRUNCATE_AT]
                    + f"...\n[output truncated, {omitted} chars omitted; use {FULL_OUTPUT_PLACEHOLDER} for full output]"
                )
            self.messages.append({"role": "tool", "name": name, "content": truncated})

        self.plan_index = _trim_history(self.messages, self.plan_index)

    def observe_and_adjust(self) -> List[Any]:
        """Observe model output after tools and get the next plan."""
        return self._chat_step()

    def _chat_step(self) -> List[Any]:
        if self.debug:
            console.print(f"[magenta]Messages: {self.messages}[/magenta]")
        final: Optional[ChatResponse] = None
        tool_calls: List[Any] = []
        output_buffer = ""
        for chunk in _stream_chat(self.messages):
            final = chunk
            if chunk.message.content:
                text = chunk.message.content
                output_buffer += text
                if "<think>" in text:
                    self.in_think = True
                style = "yellow" if self.in_think else "green"
                if "</think>" in text:
                    self.in_think = False
                console.print(text, end="", style=style)
            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)
        console.print()
        if output_buffer:
            logger.info("agent output: %s", output_buffer)

        if not final:
            return []

        if self.debug and tool_calls:
            console.print(f"[magenta]Tool calls: {tool_calls}[/magenta]")

        assistant_message = {"role": "assistant", "content": output_buffer}
        if tool_calls:
            assistant_message["tool_calls"] = [_minify_tool_call(c) for c in tool_calls]
        self.messages.append(assistant_message)
        if self.debug:
            console.print(f"[magenta]Assistant message: {assistant_message}[/magenta]")
        if self.plan_index is None:
            self.plan_index = len(self.messages) - 1
        return tool_calls

    def run(self) -> None:
        tool_calls = self.define_plan()
        while tool_calls:
            self.execute_plan(tool_calls)
            tool_calls = self.observe_and_adjust()
        _trim_history(self.messages, self.plan_index)


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


def _invoke_tool(name: str, args: Dict[str, Any], *, debug: bool) -> Dict[str, Any]:
    """Invoke a tool by name and return its result."""
    func = TOOL_MAP.get(name)
    if debug:
        console.print(f"[cyan]Calling function: {name}[/cyan]")
        console.print(f"[cyan]Arguments: {args}[/cyan]")
        console.print()
    logger.info("calling function %s with args %s", name, args)
    if not func:
        return {"status": "error", "message": f"unknown tool {name}", "data": None}
    try:
        if inspect.iscoroutinefunction(func):
            result = asyncio.run(func(**args))
        else:
            result = func(**args)
        if debug:
            console.print(f"[cyan]Result: {result}[/cyan]")
            console.print()
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("error during tool execution: %s", exc)
        return {"status": "error", "message": str(exc), "data": None}


def _stream_chat(messages: List[Dict[str, Any]]) -> Iterable[ChatResponse]:
    """Yield chat responses from Ollama with streaming enabled."""
    model = get_setting("stream_model", "llama3.1:8b")
    return chat(model=model, messages=messages, tools=list(TOOL_MAP.values()), stream=True)


DEFAULT_SYSTEM_PROMPT = (
    "The web scraper defaults to Playwright mode. "
    "Use Selenium only when a user explicitly requests cookie-based browsing. "
    "Tool outputs may be truncated and might not be valid JSON. "
    "The full text is stored in memory. Use "
    f"{FULL_OUTPUT_PLACEHOLDER} to reference the previous full output when calling new tools."
    "DO NOT overthink, keep the reasoning straightforward"
)


def run(query: str, *, debug: bool = False) -> None:
    """Run the streaming agent on the given query."""
    logger.info("received query: %s", query)
    agent = StreamingAgent(query, debug=debug)
    agent.run()


if __name__ == "__main__":
    import argparse
    from tools.webscraper import scraper

    parser = argparse.ArgumentParser(description="run the streaming agent")
    parser.add_argument("query", nargs="*", help="agent query")
    parser.add_argument("--debug", action="store_true", help="enable debug mode")
    args = parser.parse_args()

    query = " ".join(args.query) if args.query else input("Query: ")
    logger.info("starting agent")
    try:
        run(query, debug=args.debug)
    finally:
        asyncio.run(scraper.cleanup())
        logger.info("agent shutdown")
