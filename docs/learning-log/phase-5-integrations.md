# Phase 5: Integrations: mock CRM, ERP, ITSM, Teams, MCP

**Goal:** connect the agents to enterprise systems.

**Done when:** the agent reads the mock CRM, ERP and ITSM API and posts to the mock Teams webhook through a custom MCP server, with retries and a fallback on failure.

## Concepts to learn

- **An MCP server is an adapter.** Enterprise systems expose REST APIs, and an MCP server wraps them as tools an agent can discover and call.
- **Retries need idempotency.** A retried create must not make a duplicate, so every create carries a key and the API returns the first result for a repeated key.
- **Enforce rules in the system of record.** The ERP applies the SAR 5,000 rule, so no client, including the agent, can skip it.
- **Fallback.** When a system is down, the agent should say so clearly, not crash.

## Entries

### 2026-11-09: The mock enterprise API

**What we built:** [mock_systems/api.py](../../mock_systems/api.py), one FastAPI app with ERP credit notes, ITSM tickets, CRM cases and a Teams channel, held in memory.
- **Idempotent creates:** every create needs an `Idempotency-Key`. The same key returns the first record, and a reused key with a different request gets 409.
- **The ERP's rule:** a credit note above SAR 5,000 is stored as `waiting_for_manager`.
- **New ticket ids** start at `TKT-100001`, clear of the lakehouse's ids.
- **Tests:** 5 in [tests/test_mock_api.py](../../tests/test_mock_api.py).
- **Container files:** a Dockerfile and `compose.yaml`.
- **Smoke test:** run with uvicorn in a memory-capped unit, the same key twice returned one ticket (`TKT-100001`), an unknown id returned 404, and it used about 90 MB.

These were written by Claude at my request; I must be able to defend them: the endpoints and shapes, requiring the key on every create, 409 for a reused key, the ERP enforcing the limit without a "manager approved" flag, and in-memory state.

**Key concepts:**
- **An idempotency key makes a create safe to retry.** The client sends the same key on every attempt, and the server stores key → first result.
  - Returning 409 when the same key arrives with a different request catches a client bug that would otherwise silently return the wrong record.
- **Put the rule where it can't be skipped.** The SAR 5,000 limit now lives in the ERP mock. A "manager approved" flag would be a field the model could fill in, so there is none: a manager's approval needs its own client.
- **Mock only what the agent needs.** There's no invoice lookup in the mock ERP, because the agent reads invoices from the governed lakehouse through UC functions. The mock holds what the agent *creates*.

**Mistakes:**
- **The Docker build is not verified yet.** Docker Desktop isn't running, and starting its VM with about 2.5 GB free risks the out-of-memory kill from Phase 4. The image will be built when there's memory, or in CI (Phase 7).
- **uvicorn was missing at first.** Claude started the mock with `uv run uvicorn`, but uvicorn isn't in the root environment. `--with-requirements mock_systems/requirements.txt` runs it with exactly the container's packages.

**Interview questions:**
1. A client times out creating a ticket and retries. How does the server avoid a duplicate, and what should it do if the retry's body differs from the first request?
2. Why does the SAR 5,000 rule live in the ERP and not only in the agent?
3. Your mock systems keep state in memory. What breaks, and when would you add a database?

### 2026-11-09: The MCP server in front of the mock API

**What we built:** [mock_systems/mcp_server.py](../../mock_systems/mcp_server.py), a FastMCP server (streamable HTTP at `/mcp`).
- **Seven tools:** create and read for the ERP, ITSM and CRM, plus a Teams post.
- **Each tool calls the mock API** with a 5 s timeout and up to 3 attempts (backoff 0.5 s, then 1 s), retrying only timeouts, dropped connections and 5xx.
- **One `Idempotency-Key` per tool call,** reused on every attempt.
- **When everything fails,** it says the system is unavailable and, for a create, not to try again.
- **Tests:** 5 in [tests/test_mcp_server.py](../../tests/test_mcp_server.py), against a fake API.
- **Live run** with a real MCP client: all seven tools listed; `create_credit_note` drafted `CN-000001` in the mock ERP and `get_credit_note` read it back; a bad category came back as a tool error with the 422 detail.

These were written by Claude at my request; I must be able to defend them: the tool names and descriptions, the timeout, the attempt count and backoff, what is retried, and the "do not try again" message.

**Key concepts:**
- **Retry only what can succeed next time.** A timeout or a 503 may pass on a retry. A 422 means the request is wrong and will fail the same way every time.
- **Make the key once per operation, not once per attempt.** Then a retry after a lost reply returns the first record. A new key per attempt would turn every lost reply into a duplicate.
- **"Unavailable" isn't "nothing happened."** After a failed create, the record may still exist, so the honest message is "may have been saved, don't retry, tell the user" rather than "nothing changed".
- **A tool error is a result, not a crash.** FastMCP turns an exception into `isError: true` with its message, so the agent can explain the failure.

**Mistakes:**
- **Still open:** the key is made per tool call. If the agent's whole tool call is replayed after a crash, it gets a new key. Deriving the key from the agent's `tool_call_id` would close that gap, and it's marked in the code.

**Interview questions:**
1. Which failures should an integration retry, and which must it never retry? Give an example of each.
2. Why must the idempotency key be created before the first attempt and reused, and what goes wrong if each attempt makes its own?
3. Your create call failed after every retry. What do you tell the user, and why not "nothing was changed"?

### 2026-11-09: The agent writes to Najm's systems through MCP

**What we built:**
- **The MCP server is wired in.** [agent/agent/mcps.py](../../agent/agent/mcps.py) adds it when `MOCK_MCP_URL` is set, as a plain MCP server, so no Databricks token is sent to it. `handle_tool_error=True` turns a failed call into a message the supervisor can explain.
- **The supervisor gets every MCP tool that isn't a UC function.**
- **Default-deny approvals:** `approval_rules` gates every one of these tools except reads (`get_*`), so a write tool the server adds later is gated before anyone remembers to list it.
- **Stand-ins removed:** the Phase 4 `actions.py` is gone, and the SAR 5,000 rule now lives in the mock ERP.
- **Supervisor prompt, version 7:** names the four writes and the three reads, and adds a rule for an unavailable system.
- **Result on the local agent against the live mock:**
  - asked for a credit note, the turn paused; on approve, the ERP stored `CN-000002` and the answer quoted its id;
  - "What is the status of that credit note now?" called `get_credit_note`, with no approval pause, and answered "drafted";
  - "Post a one-line summary … to the billing channel" paused; on approve, `MSG-000001` appeared in the mock #billing channel.

These were written by Claude at my request; I must be able to defend them: default deny for approvals, the approval texts, plain MCP for a local server, the new supervisor rules, and the `create_credit_note` reason description.

**Key concepts:**
- **Default deny beats a list.** Gating "everything except reads" means the safe choice happens automatically. A list of writes is safe only until someone forgets to update it.
- **Never send a workspace token to a server you don't run inside Databricks.** The Databricks MCP client attaches workspace credentials, so a local or third-party server gets the plain client.
- **The approval text is part of the safety design.** The approver judges the call by its arguments, so they must be readable: amount, invoice and reason.
- **Discovery failure is already handled.** `mcp_tools` treats extra servers as optional: if the server is down when a turn starts, the agent runs without those tools.

**Mistakes:**
- **An invented policy code in a write.** The first credit note's reason said "policy code DUP", which no tool returned; the tool description asked the model to "name the policy". The description now asks for the `doc_id` exactly as a specialist cited it, and the re-run showed "fin-duplicate-invoices". In this run the approval step was the only human check, and I approved automatically; a real approver would have to catch it.
- **A stale tool name in a test.** An earlier reformat had split a test line, so Claude's text replacement missed it. The test failed and caught that a renamed tool would have lost its manager note in the approval text.

**Interview questions:**
1. Your MCP server adds a new tool next month. How do you make sure the agent can't call it without approval, before anyone reviews it?
2. Why must a Databricks token never reach a non-Databricks MCP server, and how does the agent avoid it?
3. A write's arguments contain a detail no tool returned. Where can you catch it, and which layer should?
