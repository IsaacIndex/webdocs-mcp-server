import logging
from typing import Any, Dict

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from playwright.sync_api import sync_playwright

from .mcp import mcp
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("react_browser_task")


@mcp.tool(description=PROMPT)
def react_browser_task(url: str, goal: str) -> Dict[str, Any]:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        @tool
        def goto(target: str) -> str:
            page.goto(target)
            return f"navigated to {target}"

        @tool
        def click(selector: str) -> str:
            page.click(selector)
            return f"clicked {selector}"

        @tool
        def extract(selector: str) -> str:
            return page.inner_text(selector)

        @tool
        def page_content() -> str:
            return page.content()

        llm = ChatOllama(model="qwen3:4b")
        agent = create_react_agent(llm, [goto, click, extract, page_content])

        goto(url)
        result = agent.invoke({"messages": [HumanMessage(content=goal)]})
        messages = result.get("messages", [])
        final = messages[-1].content if messages else ""
        browser.close()
        return {
            "status": "success",
            "message": "interaction finished",
            "data": {"content": final},
        }


react_browser_task.__doc__ = PROMPT
