import os

# Ensure logging directory exists before importing main
os.makedirs(os.path.join(os.path.expanduser("~"), "Downloads"), exist_ok=True)

from langchain_ollama import ChatOllama  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402

# ollama's python client docs: https://github.com/jmorganca/ollama/blob/main/docs/api.md
from ollama import Client  # noqa: E402

import main  # noqa: E402

llm = ChatOllama(model="qwen3:4b")
client = Client()

# Use tools defined in main.py and convert them to LangChain tools
TOOLS = [
    tool(main.open_in_user_browser.fn),
    tool(main.scrape_website.fn),
    tool(main.extract_links.fn),
    tool(main.download_pdfs_from_text.fn),
    tool(main.ping.fn),
]

agent = create_react_agent(llm, TOOLS)


def chat(query: str, *, stream: bool = False) -> str:
    """Return agent response.

    When ``stream`` is ``True`` the response is printed token by token using
    :func:`langgraph.prebuilt.create_react_agent` streaming as described in the
    `LangGraph streaming docs <https://python.langchain.com/docs/guides/langgraph/streaming>`_.
    For details on the Ollama client see the
    `Ollama API docs <https://github.com/jmorganca/ollama/blob/main/docs/api.md>`_.
    """

    inputs = {"messages": [HumanMessage(content=query)]}
    if stream:
        tokens = []
        for _, mode, payload in agent.stream(inputs, stream_mode="messages"):
            if mode == "messages":
                message, _meta = payload
                if getattr(message, "content", None):
                    print(message.content, end="", flush=True)
                    tokens.append(message.content)
        print()
        return "".join(tokens)
    result = agent.invoke(inputs)
    messages = result.get("messages", [])
    return messages[-1].content if messages else ""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Interact with the agent")
    parser.add_argument("query", nargs="*", help="Question to ask")
    parser.add_argument("--stream", action="store_true", help="Stream tokens")
    args = parser.parse_args()

    question = " ".join(args.query) if args.query else input("Query: ")
    chat(question, stream=args.stream)
