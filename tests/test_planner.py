import pytest
from planner import PlannerAgent, main
from unittest.mock import patch


def test_planner_run():
    with patch("planner._collect", return_value='<plan>["scrape_website"]</plan>'):
        plan = PlannerAgent("what is python").run()
    assert plan == ["scrape_website"]


def test_planner_cli_missing():
    with pytest.raises(SystemExit):
        main([])
