from typing import Dict, Any
import time

from .mcp import mcp


@mcp.tool
def ping() -> Dict[str, Any]:
    """Check if the server is responsive"""
    return {
        "status": "success",
        "message": "Pong",
        "data": {"timestamp": time.time()},
    }
