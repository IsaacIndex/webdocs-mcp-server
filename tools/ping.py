from typing import Dict, Any
import time

from .mcp import mcp
from .prompt_utils import load_prompt


PROMPT = load_prompt("ping")


@mcp.tool(description=PROMPT)
def ping() -> Dict[str, Any]:
    return {
        "status": "success",
        "message": "Pong",
        "data": {"timestamp": time.time()},
    }


ping.__doc__ = PROMPT
