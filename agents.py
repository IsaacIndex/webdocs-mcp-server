import os

# Ensure logging directory exists before importing main
os.makedirs(os.path.join(os.path.expanduser("~"), "Downloads"), exist_ok=True)

from langchain_ollama import ChatOllama  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel  # noqa: E402
import uvicorn  # noqa: E402

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


app = FastAPI()


class Query(BaseModel):
    query: str


@app.post("/agent")
def query_agent(payload: Query) -> dict[str, str]:
    """Run the LangChain agent with the provided query."""
    response = run(payload.query)
    return {"response": response}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="run as http server")
    parser.add_argument("query", nargs="*", help="query to run when not serving")
    args = parser.parse_args()

    if args.serve:
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8001")))
    else:
        question = " ".join(args.query) if args.query else input("Query: ")
        print(run(question))
