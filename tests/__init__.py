import sys
import types

# provide dummy mcp package for tests
sys.modules.setdefault("mcp", types.ModuleType("mcp"))
sys.modules.setdefault("mcp.server", types.ModuleType("mcp.server"))
fastmcp_module = types.ModuleType("fastmcp")


class _FastMCP:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def tool(self, *args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper

    def run(self) -> None:
        pass


fastmcp_module.FastMCP = _FastMCP

sys.modules.setdefault("mcp.server.fastmcp", fastmcp_module)
ollama_mod = types.ModuleType("langchain_ollama")
ollama_mod.ChatOllama = object
sys.modules.setdefault("langchain_ollama", ollama_mod)
lc_core = types.ModuleType("langchain_core")
msgs = types.ModuleType("messages")
msgs.HumanMessage = object
lc_core.messages = msgs
sys.modules.setdefault("langchain_core", lc_core)
sys.modules.setdefault("langchain_core.messages", msgs)
tools_mod = types.ModuleType("tools")


def _tool(fn=None, **kwargs):
    def decorator(f):
        return f
    return decorator(fn) if fn else decorator


tools_mod.tool = _tool
lc_core.tools = tools_mod
sys.modules.setdefault("langchain_core.tools", tools_mod)
prebuilt_mod = types.ModuleType("prebuilt")


def _create_react_agent(*args, **kwargs):
    return object()


prebuilt_mod.create_react_agent = _create_react_agent
langgraph_mod = types.ModuleType("langgraph")
langgraph_mod.prebuilt = prebuilt_mod
sys.modules.setdefault("langgraph", langgraph_mod)
sys.modules.setdefault("langgraph.prebuilt", prebuilt_mod)
