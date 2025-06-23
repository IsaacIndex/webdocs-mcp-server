import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import importlib
import pytest

required_modules = [
    "fastapi",
    "langchain_ollama",
    "langchain_core",
    "langgraph",
    "fastmcp",
    "selenium",
]
for module in required_modules:
    if importlib.util.find_spec(module) is None:
        pytest.skip(f"{module} not available", allow_module_level=True)

import agents  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

def test_agent_endpoint(monkeypatch):
    def fake_run(query: str) -> str:
        return "dummy response"
    monkeypatch.setattr(agents, "run", fake_run)
    client = TestClient(agents.app)
    resp = client.post("/agent", json={"query": "hello"})
    assert resp.status_code == 200
    assert resp.json() == {"response": "dummy response"}
