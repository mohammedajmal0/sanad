"""MCP servers the agent adds itself, beyond the ones declared in ``agent.toml``.

Najm's mock enterprise systems (mock_systems/mcp_server.py, Phase 5):
- ``MOCK_MCP_URL`` (local runs): a plain MCP server, so no Databricks token is sent to it.
- ``MOCK_MCP_APP`` (deployed): the Databricks App ``sanad-mock-systems``, called with Databricks
  OAuth as the agent app's service principal, which has ``CAN_USE`` on it (databricks.yml).

Both are optional: if the server can't be found or is down when a turn starts, the agent runs
without these tools, and ``handle_tool_error=True`` turns a failed call into a tool message the
supervisor explains instead of an exception that ends the turn.
"""

import logging
import os
from functools import lru_cache

from databricks.sdk.errors import DatabricksError
from databricks_agentkit import workspace_client
from databricks_langchain import DatabricksMCPServer
from databricks_langchain.multi_server_mcp_client import MCPServer

logger = logging.getLogger(__name__)
NAME, TIMEOUT_S = "najm_systems", 30  # the timeout covers the server's 3 attempts of up to 5 s


@lru_cache(maxsize=1)
def _app_url(app_name: str) -> str:
    return workspace_client().apps.get(app_name).url


def build_mcp_servers() -> list[MCPServer]:
    if url := os.getenv("MOCK_MCP_URL"):  # e.g. http://localhost:8200/mcp
        return [MCPServer(name=NAME, url=url, handle_tool_error=True, timeout=TIMEOUT_S)]
    if app_name := os.getenv("MOCK_MCP_APP"):
        try:
            url = f"{_app_url(app_name)}/mcp"
        except DatabricksError:  # missing app or no permission: run without the systems
            logger.warning("Mock systems app %r not found; continuing without it.", app_name)
            return []
        return [
            DatabricksMCPServer(
                name=NAME,
                url=url,
                workspace_client=workspace_client(),
                handle_tool_error=True,
                timeout=TIMEOUT_S,
            )
        ]
    return []
