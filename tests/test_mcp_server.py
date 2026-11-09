"""The MCP adapter's retry rules, against a fake API (httpx.MockTransport). No network."""

import asyncio

import httpx
import pytest

from mock_systems import mcp_server


@pytest.fixture
def api(monkeypatch):
    """Answer with the given responses in order; record each request's Idempotency-Key."""
    keys = []

    def use(*responses):
        def handler(request):
            keys.append(request.headers.get("Idempotency-Key"))
            reply = responses[len(keys) - 1]
            if isinstance(reply, Exception):
                raise reply
            return reply

        monkeypatch.setattr(mcp_server, "transport", httpx.MockTransport(handler))
        return keys

    monkeypatch.setattr(mcp_server, "BACKOFF_S", 0)
    return use


def test_server_errors_are_retried_with_one_key(api):
    keys = api(httpx.Response(503), httpx.Response(502), httpx.Response(201, json={"id": "TKT-1"}))
    assert asyncio.run(mcp_server.create_ticket("VPN", "VPN drops")) == {"id": "TKT-1"}
    assert len(keys) == 3 and len(set(keys)) == 1  # the same key on every attempt


def test_a_bad_request_is_not_retried(api):
    keys = api(httpx.Response(422, json={"detail": "bad category"}))
    with pytest.raises(ValueError, match="422"):
        asyncio.run(mcp_server.create_ticket("Coffee", "x"))
    assert len(keys) == 1


def test_refused_connections_mean_nothing_was_saved(api):
    down = httpx.ConnectError("refused")
    keys = api(down, down, down)
    with pytest.raises(mcp_server.Unavailable, match="ERP is unavailable.*nothing was saved"):
        asyncio.run(mcp_server.create_credit_note("INV-050001", 1440.71, "duplicate"))
    assert len(keys) == 3


def test_a_timeout_after_connecting_may_have_saved_it(api):
    slow = httpx.ReadTimeout("no reply")
    api(slow, httpx.ConnectError("refused"), httpx.ConnectError("refused"))
    with pytest.raises(mcp_server.Unavailable, match="may still have been saved"):
        asyncio.run(mcp_server.create_ticket("VPN", "VPN drops"))


def test_reads_send_no_key(api):
    keys = api(httpx.Response(200, json={"id": "CN-000001"}))
    assert asyncio.run(mcp_server.get_credit_note("CN-000001")) == {"id": "CN-000001"}
    assert keys == [None]


def test_the_server_offers_seven_tools():
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert names == {"create_credit_note", "get_credit_note", "create_ticket", "get_ticket",
                     "create_case", "get_case", "post_teams_message"}  # fmt: skip
