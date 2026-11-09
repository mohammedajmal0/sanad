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
