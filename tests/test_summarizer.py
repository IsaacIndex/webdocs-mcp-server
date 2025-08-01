import json
from unittest.mock import patch
from summarizer import SummarizerAgent


def test_summarizer_run(tmp_path):
    log_file = tmp_path / "log.json"
    with open(log_file, "w") as f:
        json.dump([{"result": {"data": "x"}}], f)
    with patch("summarizer._collect", return_value="Answer"):
        result = SummarizerAgent(str(log_file)).run()
    assert result == "Answer"
