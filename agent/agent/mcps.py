"""MCP servers the agent adds itself, beyond the ones declared in ``agent.toml``.

Najm's mock enterprise systems (mock_systems/mcp_server.py, Phase 5), when ``MOCK_MCP_URL`` is set.
They are optional: if the server is down when a turn starts, ``mcp_tools`` logs a warning and the
agent runs without them, and ``handle_tool_error=True`` turns a failed call into a tool message
the supervisor can explain instead of an exception that ends the turn.
"""

import os

from databricks_langchain.multi_server_mcp_client import MCPServer


def build_mcp_servers() -> list[MCPServer]:
    url = os.getenv("MOCK_MCP_URL")  # e.g. http://localhost:8200/mcp
    if not url:
        return []
    # Plain MCP: no Databricks token is sent to it. p5-deploy adds Databricks auth for the server
    # on Databricks Apps. The timeout covers the server's own retries (3 attempts of up to 5 s).
    return [MCPServer(name="najm_systems", url=url, handle_tool_error=True, timeout=30)]
