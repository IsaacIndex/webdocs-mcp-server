import json
from unittest.mock import patch
from executor import ExecutorAgent


def test_executor_run(tmp_path):
    plan = ["scrape_website"]
    fake_result = {"data": "ok"}
    with patch("executor._collect", return_value='<tool>{"name":"scrape_website","args":{}}</tool>'):
        with patch("executor._invoke_tool", return_value=fake_result):
            agent = ExecutorAgent(plan, "query", str(tmp_path))
            log_file = agent.run()
    with open(log_file) as f:
        data = json.load(f)
    assert data[0]["result"] == fake_result
