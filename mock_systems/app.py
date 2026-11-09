"""The mock systems as one Databricks App (p5-deploy): the REST API and the MCP server in one process.

The MCP tools still call the API over HTTP (MOCK_API_URL in app.yaml points at this same process),
so the deployed app keeps the timeouts, retries and idempotency keys the agent relies on.
"""

from contextlib import asynccontextmanager

from api import app
from mcp_server import app as mcp_app
from mcp_server import mcp


@asynccontextmanager
async def lifespan(_):
    async with mcp.session_manager.run():  # a mounted app's own lifespan doesn't run
        yield


app.router.lifespan_context = lifespan
app.mount("/", mcp_app)  # after the API's routes, so /mcp falls through to the MCP server
