"""MCP server for Najm's mock systems (Phase 5): the agent's tools for the ERP, ITSM, CRM and Teams.

It is an adapter: each tool calls the mock REST API (MOCK_API_URL) with a timeout and retries.
Retries are safe because a create sends one Idempotency-Key, made once per tool call and reused on
every attempt: if the first attempt reached the API but its reply was lost, the retry gets the same
record back. Tool descriptions and retry settings written by Claude at my request.

    MOCK_API_URL=http://localhost:8100 uv run --with-requirements mock_systems/requirements.txt \
        uvicorn mock_systems.mcp_server:app --port 8200          # MCP endpoint: /mcp
"""

import asyncio
import os
import uuid

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

API = os.getenv("MOCK_API_URL", "http://localhost:8100")
TIMEOUT_S = 5.0  # per attempt
ATTEMPTS = 3  # the first try plus two retries
BACKOFF_S = 0.5  # waits 0.5 s, then 1 s
transport: httpx.AsyncBaseTransport | None = None  # tests swap in httpx.MockTransport

# DNS-rebinding protection accepts only localhost Host headers by default. On Databricks Apps every
# request arrives through Databricks' authenticating proxy with the app's own host name, and that
# attack (a browser tricked into calling a local server) doesn't apply, so it is off there only.
on_apps = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP(
    "najm-mock-systems",
    stateless_http=True,
    transport_security=on_apps if os.getenv("DATABRICKS_APP_NAME") else None,
)


class Unavailable(RuntimeError):
    """The system did not answer after every attempt."""


async def _call(method: str, path: str, body: dict | None = None) -> dict | list:
    """One API call with a timeout. Retries timeouts, dropped connections and 5xx, never 4xx.

    Async on purpose: deployed, the API runs in this same process, and a blocking call would hold
    the event loop the API needs to answer it (it deadlocked until the timeout, 2026-11-09).
    """
    # ponytail: one key per tool call; derive it from the agent's tool_call_id to also cover a
    # whole tool call being replayed after a crash
    headers = {"Idempotency-Key": uuid.uuid4().hex} if method == "POST" else {}
    reached = False  # did any attempt possibly arrive? A refused connection never sent anything.
    async with httpx.AsyncClient(base_url=API, timeout=TIMEOUT_S, transport=transport) as client:
        for attempt in range(ATTEMPTS):
            try:
                response = await client.request(method, path, json=body, headers=headers)
            except httpx.TransportError as error:  # timeout, refused, reset
                failure = type(error).__name__
                reached |= not isinstance(error, httpx.ConnectError | httpx.ConnectTimeout)
            else:
                reached = True
                if response.status_code < 400:
                    return response.json()
                if response.status_code < 500:  # the request is wrong: repeating it won't help
                    raise ValueError(f"{response.status_code}: {response.json().get('detail')}")
                failure = f"HTTP {response.status_code}"
            if attempt + 1 < ATTEMPTS:
                await asyncio.sleep(BACKOFF_S * 2**attempt)
    system = path.split("/")[1].upper()
    outcome = ""
    if headers:  # a create: say exactly what we know about whether it was saved
        outcome = (" It may still have been saved, so do not try again; tell the user." if reached
                   else " The request never reached it, so nothing was saved.")  # fmt: skip
    raise Unavailable(
        f"The {system} is unavailable ({failure} after {ATTEMPTS} attempts).{outcome}"
    )


@mcp.tool()
async def create_credit_note(
    invoice_id: str, amount_sar: float, reason_code: str, reason: str
) -> dict:
    """Draft a credit note in Najm's ERP for one invoice. It is stored as awaiting_approval with
    the approver the Credit Note and Refund Policy (fin-credit-notes) requires for the amount; an
    AI may draft but never approve. invoice_id like INV-050001; amount_sar in SAR including VAT;
    reason_code from fin-credit-notes: DUP duplicate invoice, LATE late delivery, RET returned
    goods, PRC pricing error, OTH anything else; reason: one sentence, naming the original
    invoice."""
    body = {"invoice_id": invoice_id, "amount_sar": amount_sar, "reason_code": reason_code,
            "reason": reason}  # fmt: skip
    return await _call("POST", "/erp/credit-notes", body)


@mcp.tool()
async def get_credit_note(credit_note_id: str) -> dict:
    """Read one credit note from the ERP by its id (e.g. CN-000001): invoice, amount and status."""
    return await _call("GET", f"/erp/credit-notes/{credit_note_id}")


@mcp.tool()
async def create_ticket(category: str, summary: str, priority: str = "medium") -> dict:
    """Open an IT ticket in the ITSM. category is VPN, Email, Laptop, Password reset, ERP access or
    Printer; summary is one sentence; priority is low, medium or high."""
    body = {"category": category, "summary": summary, "priority": priority}
    return await _call("POST", "/itsm/tickets", body)


@mcp.tool()
async def get_ticket(ticket_id: str) -> dict:
    """Read one IT ticket from the ITSM by its id (e.g. TKT-100001): category, summary, status."""
    return await _call("GET", f"/itsm/tickets/{ticket_id}")


@mcp.tool()
async def create_case(account_id: str, subject: str) -> dict:
    """Open a customer case in the CRM for one account (e.g. ACC-00001), with a one-line subject."""
    return await _call("POST", "/crm/cases", {"account_id": account_id, "subject": subject})


@mcp.tool()
async def get_case(case_id: str) -> dict:
    """Read one customer case from the CRM by its id (e.g. CASE-000001): account, subject, status."""
    return await _call("GET", f"/crm/cases/{case_id}")


@mcp.tool()
async def post_teams_message(channel: str, text: str) -> dict:
    """Post a short summary to a Najm Teams channel (e.g. billing, it-ops)."""
    return await _call("POST", "/teams/messages", {"channel": channel, "text": text})


app = mcp.streamable_http_app()
