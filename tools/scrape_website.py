from typing import Dict, Any
import logging
import re
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

from .mcp import mcp
from .webscraper import scraper
from .prompt_utils import load_prompt

logger = logging.getLogger(__name__)


PROMPT = load_prompt("scrape_website")
_stemmer = PorterStemmer()


def _tokenize(text: str) -> set[str]:
    tokens = word_tokenize(text)
    return { _stemmer.stem(t.lower()) for t in tokens if t.isalpha() }


def _filter_content(content: str, query: str, max_sentences: int = 5) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", content)
    query_tokens = _tokenize(query)
    scored: list[tuple[float, str]] = []
    for sentence in sentences:
        sent_tokens = _tokenize(sentence)
        if not sent_tokens:
            continue
        intersection = query_tokens & sent_tokens
        union = query_tokens | sent_tokens
        score = len(intersection) / len(union) if union else 0
        if score:
            scored.append((score, sentence.strip()))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return " ".join(sentences[:max_sentences])
    relevant = [s for _, s in scored[:max_sentences]]
    return " ".join(relevant)


@mcp.tool(description=PROMPT)
async def scrape_website(url: str, query: str) -> Dict[str, Any]:
    try:
        content = await scraper.fetch_content(url)
        content = _filter_content(content, query)
        return {
            "status": "success",
            "no. of characters": len(content),
            "message": "Website content scraped successfully",
            "data": {"content": content},
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": None,
        }


scrape_website.__doc__ = PROMPT


if __name__ == "__main__":
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="scrape relevant text from a website")
    parser.add_argument("url", help="page to scrape")
    parser.add_argument("query", help="information to look for")
    args = parser.parse_args()

    result = asyncio.run(scrape_website(args.url, args.query))
    print(json.dumps(result, indent=2))
