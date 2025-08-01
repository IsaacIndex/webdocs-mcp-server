import json
from unittest.mock import patch

import agents_stream_tools as ast


def test_planner_produces_plan():
    shared = {"plan": "", "execution": "", "summary": "", "plan_json": []}
    out = "<plan>{\"tool\": \"scrape_website\", \"purpose\": \"grab\"}\n</plan>"
    with patch.object(ast.PlannerAgent, "_chat", return_value=out):
        plan = ast.PlannerAgent("q", shared).run()
    assert plan and plan[0]["tool"] in ast.AVAILABLE_TOOLS
    assert shared["plan_json"] == plan


def test_executor_dynamic_tool_invocation():
    shared = {"plan": "plan", "execution": "", "summary": "", "plan_json": []}
    tool_map = {"scrape_website": lambda url: {"data": url}}
    step = {"tool": "scrape_website", "purpose": "grab"}
    with patch("agents_stream_tools.get_available_tools", return_value=tool_map):
        with patch.object(ast.ExecutorAgent, "_chat", return_value='<tool>{"tool":"scrape_website","args":{"q":"latest cars"}}</tool>'):
            with patch("agents_stream_tools._invoke_tool", return_value={"data": "ok"}) as inv:
                result = ast.ExecutorAgent([step], "latest cars", shared).run()
    inv.assert_called_once_with("scrape_website", {"q": "latest cars"}, tool_map=tool_map, debug=False)
    assert json.loads(result)["data"] == "ok" or result == ""


def test_full_pipeline():
    shared = {"plan": "", "execution": "", "summary": "", "plan_json": []}
    planner_out = "<plan>{\"tool\": \"scrape_website\", \"purpose\": \"grab\"}\n</plan>"
    with patch.object(ast.PlannerAgent, "_chat", return_value=planner_out):
        with patch.object(ast.ExecutorAgent, "_chat", return_value='<tool>{"tool":"scrape_website","args":{}}</tool>'):
            with patch("agents_stream_tools._invoke_tool", return_value={"data": "ok"}):
                with patch.object(ast.SummarizerAgent, "_chat", return_value="<final>done</final>"):
                    agent = ast.StreamingAgent(query="q", shared=shared)
                    agent.run()
    assert shared["summary"] == "<final>done</final>"

