import argparse
import json
from typing import List, Optional

from agent_utils import (
    _collect,
    _extract_plan,
    DEFAULT_SYSTEM_PROMPT,
    PLANNER_PROMPT,
    logger,
)


class PlannerAgent:
    def __init__(self, task: str, model: Optional[str] = None) -> None:
        self.task = task
        self.model = model

    def run(self) -> List[str]:
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": self.task},
        ]
        output = _collect(messages, model=self.model)
        plan = _extract_plan(output)
        logger.info("planner plan: %s", plan)
        return plan


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="planner component")
    parser.add_argument("--task", required=True, help="task to plan")
    parser.add_argument("--model", default=None, help="ollama model")
    args = parser.parse_args(argv)

    plan = PlannerAgent(args.task, model=args.model).run()
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
