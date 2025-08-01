import argparse
import json
import os
from typing import Any, Dict, List, Optional

from agent_utils import (
    _collect,
    _invoke_tool,
    _minify_result,
    TOOL_PATTERN,
    DEFAULT_SYSTEM_PROMPT,
    EXECUTOR_PROMPT,
    logger,
)


class ExecutorAgent:
    def __init__(
        self,
        plan: List[str],
        query: str,
        scratch_dir: str,
        model: Optional[str] = None,
    ) -> None:
        self.plan = plan
        self.query = query
        self.scratch_dir = scratch_dir
        self.model = model

    def _get_args(self, tool_name: str, last_output: str) -> Dict[str, Any]:
        user_text = json.dumps({"query": self.query, "last_output": last_output})
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "system", "content": EXECUTOR_PROMPT.format(tool=tool_name)},
            {"role": "user", "content": user_text},
        ]
        output = _collect(messages, model=self.model)
        match = TOOL_PATTERN.search(output)
        if not match:
            return {}
        data = json.loads(match.group(1))
        return data.get("args", {})

    def run(self) -> str:
        os.makedirs(self.scratch_dir, exist_ok=True)
        log_path = os.path.join(self.scratch_dir, "log.json")
        results = []
        last_output = ""
        for tool_name in self.plan:
            args = self._get_args(tool_name, last_output)
            result = _invoke_tool(tool_name, args)
            full = json.dumps(_minify_result(result), separators=",:")
            results.append({"tool": tool_name, "args": args, "result": result})
            last_output = full
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info("wrote executor logs to %s", log_path)
        return log_path


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="executor component")
    parser.add_argument("--plan", required=True, help="plan json")
    parser.add_argument("--query", required=True, help="original query")
    parser.add_argument("--scratch_dir", required=True, help="working directory")
    parser.add_argument("--model", default=None, help="ollama model")
    args = parser.parse_args(argv)

    plan = json.loads(args.plan)
    agent = ExecutorAgent(plan, args.query, args.scratch_dir, model=args.model)
    log_file = agent.run()
    print(log_file)


if __name__ == "__main__":
    main()
