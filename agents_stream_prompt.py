import tempfile

from planner import PlannerAgent
from executor import ExecutorAgent
from summarizer import SummarizerAgent
from agent_utils import logger


def run(query: str) -> None:
    logger.info("received query: %s", query)
    scratch = tempfile.mkdtemp(prefix="agent-")
    plan = PlannerAgent(query).run()
    log_file = ExecutorAgent(plan, query, scratch).run()
    SummarizerAgent(log_file).run()


if __name__ == "__main__":
    import sys
    from tools.webscraper import scraper

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    logger.info("starting agent")
    try:
        run(query)
    finally:
        scraper.cleanup()
        logger.info("agent shutdown")
