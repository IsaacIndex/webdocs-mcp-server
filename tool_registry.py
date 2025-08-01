from importlib import import_module
from typing import Callable, Dict, Any

from tools import __all__ as tool_names


def get_available_tools() -> Dict[str, Callable[..., Any]]:
    """Return mapping of tool names to callables discovered from tools package."""
    mapping: Dict[str, Callable[..., Any]] = {}
    for name in tool_names:
        try:
            module = import_module(f"tools.{name}")
        except Exception:
            continue
        func = getattr(module, name, None)
        if callable(func):
            mapping[name] = func
    return mapping
