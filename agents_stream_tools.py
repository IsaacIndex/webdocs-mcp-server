import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

import re

import asyncio
import inspect

from rich.console import Console
from ollama import chat, ChatResponse

from settings import get_setting

from tool_registry import get_available_tools

TOOL_MAP: Dict[str, Callable[..., Any]] = get_available_tools()
AVAILABLE_TOOLS = list(TOOL_MAP.keys())

console = Console()

TRUNCATE_AT = 2000
FULL_OUTPUT_PLACEHOLDER = "<FULL_TOOL_OUTPUT>"

PLAN_PATTERN = re.compile(r"<plan>(.*?)</plan>", re.DOTALL)
TOOL_PATTERN = re.compile(r"<tool>(.*?)</tool>", re.DOTALL)

PLANNER_PROMPT = (
    "You are Planner. Output ONLY newline-separated JSON objects:\n"
    '{"tool": "<registry_name>", "purpose": "<brief reasoning>"}'
    "\nAvailable tools: "
    + ", ".join(AVAILABLE_TOOLS)
)

EXECUTOR_PROMPT = (
    "You are Executor. Decide the best arguments for this tool. "
    "Output JSON ONLY:\n{\"tool\": \"<same>\", \"args\": {...}}"
)

SUMMARY_PROMPT = (
    "You are the summarizer agent. Mention which tools executed. "
    "Produce a concise final report using the plan and execution logs. "
    "Answer inside <final>ANSWER</final>. Do not wrap <final> inside <think>."
)

DEFAULT_SYSTEM_PROMPT = (
    "The web scraper defaults to Playwright mode. "
    "Use Selenium only when a user explicitly requests cookie-based browsing. "
    "Tool outputs may be truncated and might not be valid JSON. "
    "The full text is stored in memory. Use "
    f"{FULL_OUTPUT_PLACEHOLDER} to reference the previous full output when calling new tools."
    " DO NOT overthink, keep the reasoning straightforward."
)


@dataclass(kw_only=True)
class _BaseAgent:
    debug: bool = False

    def _chat(self, messages: List[Dict[str, Any]], *, tools: Optional[List[Any]] = None) -> str:
        if self.debug:
            console.print(f"[magenta]Messages: {messages}[/magenta]")
        output_buffer = ""
        for chunk in _stream_chat(messages, tools=tools):
            if chunk.message.content:
                text = chunk.message.content
                output_buffer += text
                console.print(text, end="", style="green")
        console.print()
        return output_buffer


@dataclass
class PlannerAgent(_BaseAgent):
    query: str
    shared: Dict[str, Any]

    def run(self) -> List[Dict[str, Any]]:
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "system", "content": PLANNER_PROMPT},
        ]
        if self.shared.get("summary"):
            messages.append({"role": "system", "content": f"Previous summary: {self.shared['summary']}"})
        messages.append({"role": "user", "content": self.query})
        output = self._chat(messages)
        plan = _extract_plan(output)
        self.shared["plan"] = output
        self.shared["plan_json"] = plan
        return plan


@dataclass
class ExecutorAgent(_BaseAgent):
    plan: List[Dict[str, Any]]
    query: str
    shared: Dict[str, Any]

    def run(self) -> str:
        tool_map = get_available_tools()
        results = []
        last_output = ""
        executed = []
        for step in self.plan:
            messages = [
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "system", "content": EXECUTOR_PROMPT},
                {"role": "user", "content": json.dumps({"query": self.query, "step": step})},
            ]
            output = self._chat(messages)
            match = TOOL_PATTERN.search(output)
            if not match:
                continue
            data = json.loads(match.group(1))
            name = data.get("tool")
            args = data.get("args", {})
            result = _invoke_tool(name, args, tool_map=tool_map, debug=self.debug)
            executed.append(name)
            results.append({"tool": name, "args": args, "result": result})
            last_output = json.dumps(_minify_result(result), separators=(",", ":"))
        self.shared["execution"] = json.dumps(results)
        self.shared["executed"] = executed
        return last_output


@dataclass
class SummarizerAgent(_BaseAgent):
    query: str
    shared: Dict[str, Any]

    def run(self, last_output: str) -> str:
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "system", "content": f"Plan: {self.shared.get('plan', '')}"},
            {"role": "system", "content": f"Execution: {self.shared.get('execution', '')}"},
            {"role": "system", "content": f"Tools executed: {', '.join(self.shared.get('executed', []))}"},
            {"role": "user", "content": json.dumps({"query": self.query, "last_output": last_output})},
        ]
        output = self._chat(messages)
        self.shared["summary"] = output
        return output


@dataclass
class StreamingAgent(_BaseAgent):
    query: str
    shared: Dict[str, Any]

    def run(self) -> None:
        console.print("[bold blue]define plan[/bold blue]")
        planner = PlannerAgent(self.query, self.shared, debug=self.debug)
        plan = planner.run()
        console.print("[bold blue]execute plan[/bold blue]")
        executor = ExecutorAgent(plan, self.query, self.shared, debug=self.debug)
        last_output = executor.run()
        console.print("[bold blue]summarize[/bold blue]")
        summarizer = SummarizerAgent(self.query, self.shared, debug=self.debug)
        summarizer.run(last_output)



def _minify_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce tool result size by dropping unnecessary fields."""
    if result.get("status") == "error":
        return {"error": result.get("message")}
    if "data" in result:
        return {"data": result["data"]}
    return {}


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




def _extract_plan(text: str) -> List[Dict[str, Any]]:
    """Return a list of plan objects from the model output."""
    match = PLAN_PATTERN.search(text)
    if not match:
        return []
    plan_lines = [ln.strip() for ln in match.group(1).splitlines() if ln.strip()]
    plan: List[Dict[str, Any]] = []
    for line in plan_lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "tool" in obj:
            plan.append(obj)
    return plan


def _invoke_tool(
    name: str,
    args: Dict[str, Any],
    *,
    tool_map: Optional[Dict[str, Callable[..., Any]]] = None,
    debug: bool,
) -> Dict[str, Any]:
    """Invoke a tool by name and return its result."""
    mapping = tool_map or TOOL_MAP
    func = mapping.get(name)
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


def _stream_chat(
    messages: List[Dict[str, Any]], *, tools: Optional[List[Any]] = None
) -> Iterable[ChatResponse]:
    """Yield chat responses from Ollama with streaming enabled."""
    model = get_setting("stream_model", "llama3.1:8b")
    if tools is None:
        tools = list(TOOL_MAP.values())
    return chat(model=model, messages=messages, tools=tools, stream=True)


def run(query: str, *, debug: bool = False) -> None:
    """Run the streaming agent on the given query."""
    logger.info("received query: %s", query)
    shared_state: Dict[str, Any] = {"plan": "", "execution": "", "summary": ""}
    agent = StreamingAgent(query=query, shared=shared_state, debug=debug)
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
