import os

# Ensure logging directory exists before importing main
os.makedirs(os.path.join(os.path.expanduser("~"), "Downloads"), exist_ok=True)

from langchain_ollama import ChatOllama  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402

import main  # noqa: E402

llm = ChatOllama(model="qwen3:4b")

# Use tools defined in main.py and convert them to LangChain tools
TOOLS = [
    tool(main.open_in_user_browser.fn),
    tool(main.scrape_website.fn),
    tool(main.extract_links.fn),
    tool(main.download_pdfs_from_text.fn),
    tool(main.ping.fn),
]

agent = create_react_agent(llm, TOOLS)


def run(query: str) -> str:
    """Return agent response for the given query."""
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    messages = result.get("messages", [])
    return messages[-1].content if messages else ""


def stream_response(query: str):
    """Yield the response text incrementally."""
    state = {"messages": [HumanMessage(content=query)]}
    previous = ""
    for step in agent.stream(state):
        messages = step.get("messages", [])
        if not messages:
            continue
        last = messages[-1]
        if isinstance(last, AIMessage):
            content = last.content
            delta = content[len(previous):] if content.startswith(previous) else content
            previous = content
            if delta:
                yield delta


if __name__ == "__main__":
    import sys

    stream_flag = "--stream" in sys.argv
    if stream_flag:
        sys.argv.remove("--stream")

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")

    if stream_flag:
        for chunk in stream_response(question):
            print(chunk, end="", flush=True)
        print()
    else:
        print(run(question))
