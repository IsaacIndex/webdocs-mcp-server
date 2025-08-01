import argparse
import json
from typing import List, Optional

from agent_utils import (
    _collect,
    DEFAULT_SYSTEM_PROMPT,
    SUMMARY_PROMPT,
    logger,
)


class SummarizerAgent:
    def __init__(self, log_file: str, model: Optional[str] = None) -> None:
        self.log_file = log_file
        self.model = model

    def run(self) -> str:
        with open(self.log_file, "r", encoding="utf-8") as f:
            steps: List[dict] = json.load(f)
        last_output = json.dumps(steps[-1]["result"]) if steps else ""
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": json.dumps({"last_output": last_output})},
        ]
        output = _collect(messages, model=self.model)
        logger.info("summary complete")
        print(output)
        return output


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="summarizer component")
    parser.add_argument("--logs", required=True, help="executor log file")
    parser.add_argument("--model", default=None, help="ollama model")
    args = parser.parse_args(argv)

    SummarizerAgent(args.logs, model=args.model).run()


if __name__ == "__main__":
    main()
