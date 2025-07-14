import os

# Ensure logging directory exists before importing tools
os.makedirs(os.path.join(os.path.expanduser("~"), "Downloads"), exist_ok=True)

from langchain_ollama import ChatOllama  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402
from ollama import Client  # noqa: E402
from rich.console import Console  # noqa: E402

from tools import (  # noqa: E402
    open_in_user_browser,
    scrape_website,
    extract_links,
    download_pdfs,
    ping,
)

llm = ChatOllama(model="qwen3:4b")
client = Client()
console = Console()

TOOLS = [
    tool(open_in_user_browser.fn),
    tool(scrape_website.fn),
    tool(extract_links.fn),
    tool(download_pdfs.fn),
    tool(ping.fn),
]

agent = create_react_agent(llm, TOOLS)


def run(query: str) -> str:
    """Return agent response for the given query."""
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    messages = result.get("messages", [])
    return messages[-1].content if messages else ""


def stream(query: str) -> None:
    """Stream response tokens for the given query."""
    stream = client.chat(
        model="qwen3:4b",
        messages=[{"role": "user", "content": query}],
        stream=True,
    )
    in_think = False
    for chunk in stream:
        message = chunk.get("message", {})
        content = message.get("content")
        if content:
            if "<think>" in content:
                in_think = True
            style = "yellow" if in_think else "green"
            if "</think>" in content:
                in_think = False
            console.print(content, end="", style=style)
    console.print()


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    stream(question)
