import json
from unittest.mock import patch

from planner import PlannerAgent
from executor import ExecutorAgent
from summarizer import SummarizerAgent


def test_full_flow(tmp_path):
    with patch("planner._collect") as mock_collect, \
            patch("executor._collect") as exec_collect, \
            patch("summarizer._collect") as summ_collect, \
            patch("executor._invoke_tool", return_value={"data": "ok"}):
        mock_collect.side_effect = ['<plan>["scrape_website"]</plan>']
        exec_collect.side_effect = ['<tool>{"name":"scrape_website","args":{}}</tool>']
        summ_collect.return_value = "summary"
        plan = PlannerAgent("test").run()
        log_file = ExecutorAgent(plan, "test", str(tmp_path)).run()
        result = SummarizerAgent(log_file).run()
    assert result == "summary"
    with open(log_file) as f:
        steps = json.load(f)
    assert steps[0]["tool"] == "scrape_website"
