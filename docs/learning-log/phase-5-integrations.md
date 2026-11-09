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

### 2026-11-09: Fallback when a system is down (Phase 5 gate)

**What we built:**
- **The adapter now says exactly what it knows** ([mcp_server.py](../../mock_systems/mcp_server.py)):
  - when every attempt was a refused connection, the request never left, so the message is "nothing was saved";
  - a timeout or 5xx after connecting means it may have arrived, so the message is "may still have been saved, do not try again".
- **Supervisor prompt, version 8:** pass that on in the tool's own words, and never add "nothing was done" unless the tool says so.
- **Runbook:** the "Tool timeouts" section is filled in (symptoms, checks, fixes, and never re-sending a failed write blindly).
- **Tests:** 6 in [tests/test_mcp_server.py](../../tests/test_mcp_server.py), including the timeout case.
- **Results on the local agent:**
  - **(a) Mock API stopped, MCP server up.** The credit note was approved, and the tool returned "The ERP is unavailable (ConnectError after 3 attempts). The request never reached it, so nothing was saved." The answer said the ERP was unavailable, with HTTP 200 and no second attempt at the write. A read gave the same kind of answer.
  - **(b) MCP server stopped too.** The log said "Failed to fetch optional MCP tools from server 'najm_systems'; continuing without it." The agent answered in 21 s, with no tool calls, that the ERP can't be reached and a person must draft the credit note.

**The Phase 5 gate is met:** stopping the mock API produces a graceful answer instead of a crash.

These were written by Claude at my request; I must be able to defend them: telling "never sent" apart from "maybe saved", the new supervisor wording, and the runbook section.

**Key concepts:**
- **Two places to fail, two fallbacks:**
  - The server is down when a turn starts: discovery is optional, so the agent runs without those tools and says so.
  - The server is up but the system behind it is down: the tool returns an error message, and the model explains it.
- **Only code knows whether a write might have happened.** A refused connection sent nothing; a timeout may have delivered the request. The model can't tell them apart, so the adapter states which one happened.
- **Graceful means honest.** The first version's answer said "no action was taken" while the tool said "may still have been saved". Being polite isn't enough; the claim has to match what's known.

**Mistakes:**
- **A dishonest "no action was taken".** The first fallback answer said it although the tool said the credit note "may still have been saved". That was true for a refused connection only by luck. Fixed in the adapter, which states exactly what it knows, and in the prompt, which passes it on.

**Interview questions:**
1. Your agent's integration is down. What should the user see, and what must the agent never do next?
2. How can an integration know whether a failed create might still have been saved, and why shouldn't the model decide that?
3. Tools are discovered every turn. What does that buy you during an outage, and what does it cost?

### 2026-11-09: The mock systems on Databricks Apps (Phase 5 done)

**What we built** ([ADR 0006](../adr/0006-mock-systems-behind-a-custom-mcp-app.md)):
- **One Databricks App,** `sanad-mock-systems`, declared in [databricks.yml](../../databricks.yml), with `CAN_USE` for the agent's service principal.
  - [mock_systems/app.py](../../mock_systems/app.py) serves the API and mounts the MCP server at `/mcp`, and the MCP tools call the API on the same port.
- **The MCP tools are async now.**
- **DNS-rebinding protection is off on Apps only,** where every request comes through Databricks' authenticating proxy.
- **The agent finds the app by name** (`MOCK_MCP_APP` in `agent/app.yaml`) and calls it with Databricks OAuth as its service principal ([agent/agent/mcps.py](../../agent/agent/mcps.py)).
- **Results on Databricks:**
  - My MCP client listed the deployed app's 7 tools, and a post returned `MSG-000001`.
  - The deployed agent paused with "Draft a credit note of SAR 1440.71 for INV-050001? Reason: … fin-duplicate-invoices". On approve, the mock ERP held `CN-000001`, status `drafted`, which I read directly from the app's API.
  - Memory: told two preferences, the agent saved both (in one `remember` call), and a new session recalled the role and both preferences.

**Phase 5 is done.** The agent reads and writes the mock ERP, ITSM and CRM, and posts to the mock Teams, through a custom MCP server, with retries and a fallback on failure.

These were written by Claude at my request; I must be able to defend them: one app instead of two, async tools, turning off DNS-rebinding protection on Apps only, finding the app by name, the `CAN_USE` grant, and the recall rule (supervisor prompt v9).

**Key concepts:**
- **A sync tool in an async server blocks everything.** FastMCP runs a plain function on the event loop. When the tool called the API in the same process, the API couldn't answer until the tool gave up: 16.5 s and three timeouts. Async tools fixed it, and the create took 0.04 s.
- **The same code can behave differently once deployed.** Locally the API was a separate process, so the deadlock never showed. Running the combined app locally before the 10-minute deploy found it.
- **A proxy changes the Host header.** Protection that trusts only `localhost` breaks behind any proxy. Decide where it applies, rather than turning it off everywhere.
- **Find services by name, not by URL.** The app's URL is environment-specific, so the agent looks it up at runtime, and no URL is hard-coded.

**Mistakes:**
- **The sync-tool deadlock,** above. It was found locally, before the deploy.
- **A claim of absence.** In one of two runs, "What do you remember about me?" got "I don't have any saved facts about you yet" without calling `recall`. Supervisor prompt v9 says to call `recall` first. Not yet re-run: it's a Phase 6 eval case.
- **An unexplained failure.** One deployed memory request returned a body without `output`. Two re-runs returned HTTP 200, and the logs were unavailable while the app was stopping, so the cause is unknown. Next time, print the status and body before parsing.

**Interview questions:**
1. Your MCP server works locally but deadlocks when deployed in the same process as the API it calls. Why, and what are two ways to fix it?
2. Why can DNS-rebinding protection be off for an app behind Databricks' proxy but must stay on for a local server?
3. Your agent calls the mock systems as its service principal. What do you lose compared with calling them as the user, and how would you get that back?
