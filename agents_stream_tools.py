import json
from typing import Any, Callable, Dict, Iterable, List, Optional

from ollama import chat, ChatResponse

from tools import (
    open_in_user_browser,
    scrape_website,
    extract_links,
    download_pdfs_from_text,
    ping,
)


# Map tool names to callable functions
TOOL_MAP: Dict[str, Callable[..., Any]] = {
    "open_in_user_browser": open_in_user_browser,
    "scrape_website": scrape_website,
    "extract_links": extract_links,
    "download_pdfs_from_text": download_pdfs_from_text,
    "ping": ping,
}


def _invoke_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a tool by name and return its result."""
    func = TOOL_MAP.get(name)
    if not func:
        return {"status": "error", "message": f"unknown tool {name}", "data": None}
    try:
        return func(**args)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc), "data": None}


def _stream_chat(messages: List[Dict[str, Any]]) -> Iterable[ChatResponse]:
    """Yield chat responses from Ollama with streaming enabled."""
    return chat(model="qwen3:4b", messages=messages, tools=list(TOOL_MAP.values()), stream=True)


def run(query: str) -> None:
    """Stream a response, executing tools as needed."""
    messages: List[Dict[str, Any]] = [{"role": "user", "content": query}]

    while True:
        final: Optional[ChatResponse] = None
        tool_calls = []

        for chunk in _stream_chat(messages):
            final = chunk
            if chunk.message.content:
                print(chunk.message.content, end="", flush=True)
            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)
        print()

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

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    run(query)
