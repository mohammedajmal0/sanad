# agent

The Sanad Customer Service agent: an Agent Bricks project (the CLI is Beta). `agent.toml` declares bindings, `agent/agent.py` holds the LangGraph agent and `agent/tools/` its tools. It was scaffolded on 2026-11-08 with `agentbricks init --framework langgraph --name sanad-cs`. The template's own notes follow below.

**Phase:** 4: first the Customer Service agent up to Gate A, then the supervisor, two more specialists, approvals and memory. Phase 5 connects them to the mock CRM, ERP, ITSM and Teams through MCP ([mock_systems/](../mock_systems/)).

## Sanad setup (Free Edition, checked 2026-11-08)

- **Model:** `system.ai.gpt-oss-120b` (`MODEL` in [agent/agent.py](agent/agent.py)), through the AI Gateway. Free Edition offers no Claude model. List what it does offer with `agentbricks -p sanad experimental models list`.
- **System prompts:** `sanad.prompts.supervisor@production` and `sanad.prompts.customer_service@production` in the MLflow Prompt Registry, bound in `agent.toml`. Edit [agent/prompts/](agent/prompts/)`<name>.md`, then run `DATABRICKS_CONFIG_PROFILE=sanad uv run python -m agent.prompt <name>` to register a new version and move `@production`. It lives in its own schema (`CREATE SCHEMA sanad.prompts`), because deploy grants the app `MANAGE` there.
- **Answer:** every turn ends with one extra model call, with no tools, that returns the `Answer` schema ([agent/answer.py](agent/answer.py), [agent/schema.py](agent/schema.py)). LangChain's `response_format` doesn't work with gpt-oss behind the gateway: it ignores the forced tool call, and it rejects `response_format` together with tools.
- **No memory or session store yet.** Both were unbound after `init`, and the memory task later in Phase 4 binds them. Conversation history lives in process memory.
- **Tracing:** deployed runs trace to the MLflow experiment `/Shared/agentbricks_traces/sanad-cs-bevrqu`.
- **Deployed** as the Databricks App `agent-bricks-sanad-cs`, with its own service principal. Keep it stopped between uses: `databricks apps start|stop agent-bricks-sanad-cs --profile sanad`.
- **Supervisor and specialists ([ADR 0005](../docs/adr/0005-supervisor-calls-specialists-as-tools.md)):**
  - The supervisor calls `customer_service`, the Customer Service sub-agent wrapped as a tool, and the Genie agent `ops_analytics` (`ops_analytics_ask`, `_poll`, `_query_result`).
  - The Genie agent was bound with `agentbricks tools add genie-agent <space id> --name ops_analytics --auth user`.
- **Tools:** four UC functions bound in `agent.toml` with `auth = "user"` belong to the Customer Service sub-agent: `get_customer_summary`, `get_invoices`, `get_shipment_status` and `search_policies` ([tools/](../tools/), [ADR 0004](../docs/adr/0004-run-tools-as-the-asking-user.md)). They need the workspace's managed MCP servers preview, and the app's `mcp.functions` user scope, which `agentbricks deploy --allow-user-scope-update` adds. - **Writes:** `draft_credit_note` and `open_ticket` ([agent/tools/actions.py](agent/tools/actions.py)) pause for approval before they run (`REQUIRE_APPROVAL` in [agent/agent.py](agent/agent.py)). Credit notes above SAR 5,000 then wait for a manager. Until Phase 5 they are stand-ins that check the request and store nothing. The template's `get_current_time` and `send_message` were removed.

## Run

- **Tests:** `cd agent && uv run pytest` (own environment, Python 3.12).
- **Locally on an 8 GB laptop:** don't use `agentbricks dev`. It peaks above 2 GB at startup (local proxy plus an MLflow server), and `systemd-oomd` then kills the whole VS Code window it runs under. Run the server alone in a memory-capped unit instead (about 380 MB, no local tracing):

  ```bash
  systemd-run --user --unit=sanad-agent-dev -p MemoryMax=1500M --working-directory="$PWD" \
    --setenv=PATH="$PATH" "$(which uv)" run start-server
  curl -sS localhost:8000/api/invocations -H 'Content-Type: application/json' \
    -d "{\"id\":\"$(uuidgen)\",\"session_id\":\"$(uuidgen)\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}}"
  systemctl --user stop sanad-agent-dev
  ```

- **Deploy:** `agentbricks -p sanad deploy --no-wait`, then `agentbricks -p sanad deployments wait agent-bricks-sanad-cs`. Repeat the wait if it exits 75. A first deploy takes about 3 minutes.
- **Ask the deployed agent:** `agentbricks -p sanad endpoint invoke agent-bricks-sanad-cs --path /api/invocations --json '<same body as the curl>'`

## What goes here

- **Phase 4:** the Customer Service agent; UC function tools (`get_customer_summary`, `get_invoices`, `get_shipment_status`); a retrieval tool that returns citations; a system prompt in the MLflow prompt registry; and a Pydantic answer schema (`answer`, `citations`, `confidence`, `next_action`).
- **Phase 4, after Gate A:**
  - the supervisor: done on 2026-11-09 ([ADR 0005](../docs/adr/0005-supervisor-calls-specialists-as-tools.md)), routing to Customer Service and Ops Analytics;
  - Ops Analytics: the Genie agent *Sanad Ops Analytics* exists since 2026-11-09 ([genie/](../genie/ops_analytics.geniespace.json), checked by [evals/ops_genie.py](../evals/ops_genie.py)). The supervisor task binds it with `agentbricks tools add genie-agent <space id>` and `auth = "user"`;
  - the Service Desk specialist: done on 2026-11-09, with `get_ticket_trend` plus `search_policies`. Each specialist's tools and routing description are in `SPECIALISTS` in [agent/agent.py](agent/agent.py);
  - an approval interrupt before every write;
  - session and memory stores in `agent.toml`.
- **Phase 5:** the mock systems behind a custom MCP server, with retries and a fallback on failure.
- **Agent logic stays in plain LangGraph modules, and the serving layer stays thin** ([ADR 0001](../docs/adr/0001-isolate-beta-features.md)). The template already splits it this way: `agent/agent.py:run_agent` uses no Agent Bricks types, and `runtime/` is the thin layer.

## Judgement calls

Since 2026-11-07, Claude writes these at my request, and each one is logged in the [learning log](../docs/learning-log/phase-4-agent.md):
- Phase 4: the system prompt, the answer schema and every tool description.
- Phase 4: the routing rules ([prompts/supervisor.md](agent/prompts/supervisor.md)) and the `customer_service` tool description.
- Later in Phase 4: the business rules (e.g. credit notes above SAR 5,000 need manager approval) and the approval message wording.

## Done when

- **Gate A:** the agent finds the seeded duplicate invoice, cites the refund policy, and the trace shows every tool call. **Passed on 2026-11-08** with [evals/gate_a.py](../evals/gate_a.py) `--local`, which uses the local server above plus `--setenv=MLFLOW_TRACKING_URI=databricks --setenv=MLFLOW_EXPERIMENT_NAME=/Shared/agentbricks_traces/sanad-cs-bevrqu`. The deployed agent gives the same answer, but **its traces arrive without spans**: the app's MLflow exporter can't reach the cloud storage host (`Failed to send trace to MLflow backend … storage.cloud.databricks.com … Max retries exceeded` in `agentbricks deployments logs`).
- **Phase 4 (tracker):** the supervisor routes a question to one of three specialists, calls a UC function tool, returns a schema-validated answer, and asks for approval before any write.

## Template notes (Agent Bricks 0.9.0, unchanged)

A LangGraph agent served by `databricks_agentkit.DurableAgentServer`. The managed runtime keeps invocation state and events in
memory during `agentbricks dev`. Deployment attaches a persistent Runtime Store, so invocation state and
events survive process loss and interrupted work can be recovered.

The generated project separates portable agent execution from the managed HTTP protocol:

```text
client -> runtime/main.py -> runtime/adapter.py -> agent/agent.py:run_agent
```

- `agent/agent.py` owns the framework-native agent, sessions, tools, MCP lifetime, and `run_agent`.
- `runtime/adapter.py` owns the agent-author integration hooks: runtime input/output translation plus
  `invoke` and `recover`.
- `runtime/main.py` constructs the server and registers those hooks.

To bring an existing LangGraph agent, run `agentbricks init --framework langgraph --existing .` in its
project and follow the generated prompt in your coding agent. The migration skill and this template share
[AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md), which owns integration requirements. This README owns
configuration and client examples; [AGENTS.md](AGENTS.md) provides the development map.

### Run locally

```bash
agentbricks dev
```

The API is available at `http://localhost:8000/api/invocations`, or on the port you pass with
`--app-port`. Requests can fail for a few seconds while the server starts; wait for
`Uvicorn running on ...` in the log.

Every request supplies a UUID `id`.
That ID is the invocation identifier and idempotency key. Supply the stable application session as
the top-level `session_id`; agent-specific values live inside the opaque `input` object:

```bash
SESSION_ID=$(uuidgen)
INVOCATION_ID=$(uuidgen)

curl -sS http://localhost:8000/api/invocations \
  -H 'Content-Type: application/json' \
  -d "{\"id\":\"$INVOCATION_ID\",\"session_id\":\"$SESSION_ID\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"What time is it? Use your tool.\"}]}}"
```

Reuse `SESSION_ID` for multi-turn conversation state. Generate a new `INVOCATION_ID` for each turn.
Retrying the same request with the same invocation ID returns the persisted result; changing the
request while reusing the ID returns `409`.

### Long-term memory

The Session Store keeps one conversation's state, keyed by the top-level `session_id`. The Memory Store
keeps facts the agent recalls across conversations, keyed by `actor`: `runtime/adapter.py` reads
`input.actor` and passes it to `memory_tools(actor)`. If you leave out `actor`, it defaults to the
`session_id`, so long-term memory won't carry across sessions. For memory that persists, pass a stable
`actor`, such as the end user's ID, from trusted application context. With a request-user
(`auth = "user"`) tool bound, the adapter also namespaces a supplied `actor` to the signed-in user; see
[Request-user authorization](#request-user-authorization).

Memory is off by default under `agentbricks dev`, so try it against the deployed app: two
invocations with different `session_id`s and the same `actor`.

```bash
ACTOR=user-123

# Conversation 1: the agent saves a fact with its memory tool.
agentbricks --profile <profile> endpoint invoke agent-bricks-<name> --path /api/invocations \
  --json "{\"id\":\"$(uuidgen)\",\"session_id\":\"$(uuidgen)\",\"input\":{\"actor\":\"$ACTOR\",\"messages\":[{\"role\":\"user\",\"content\":\"Remember that I prefer answers as bullet points.\"}]}}"

# Conversation 2: a new session_id, same actor, so the agent can recall it.
agentbricks --profile <profile> endpoint invoke agent-bricks-<name> --path /api/invocations \
  --json "{\"id\":\"$(uuidgen)\",\"session_id\":\"$(uuidgen)\",\"input\":{\"actor\":\"$ACTOR\",\"messages\":[{\"role\":\"user\",\"content\":\"How do I like my answers formatted?\"}]}}"
```

### Invocation modes

- Foreground: omit `background` and `stream`; the response contains the agent result under `output`.
- Foreground streaming: set `stream: true`; the response is SSE backed by persisted events.
- Background: set `background: true`; poll the returned `status_url`.
- Background streaming: set both flags; the `202` response includes `status_url` and `events_url`.

```bash
INVOCATION_ID=$(uuidgen)
curl -sN http://localhost:8000/api/invocations \
  -H 'Content-Type: application/json' \
  -d "{\"id\":\"$INVOCATION_ID\",\"session_id\":\"$SESSION_ID\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"Count to three.\"}]},\"stream\":true}"

INVOCATION_ID=$(uuidgen)
curl -sS http://localhost:8000/api/invocations \
  -H 'Content-Type: application/json' \
  -d "{\"id\":\"$INVOCATION_ID\",\"session_id\":\"$SESSION_ID\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"Summarize durable agents.\"}]},\"background\":true}" | jq
curl -sS "http://localhost:8000/api/invocations/$INVOCATION_ID" | jq
```

SSE records contain events translated by `runtime/adapter.py`: token `delta`s, completed `message`s,
and HITL `interrupt`s. Replay from a cursor with
`GET /api/invocations/{id}/events?after={sequence}`.

A message's `content` is its answer text. Models that reason (Claude 5.x) add a separate
`{"role": "assistant", "content": [{"type": "reasoning", ...}]}` message before the answer.

### Human approval

`draft_credit_note` and `open_ticket` are gated by `HumanInTheLoopMiddleware`. Start a turn asking
for a credit note or a ticket. When the output or event stream contains an `interrupt`, submit a new invocation with the same
application session:

```json
{
  "id": "<new-uuid>",
  "session_id": "<same-session-id>",
  "input": {
    "resume": {"decisions": [{"type": "approve"}]}
  }
}
```

For OBO tools (`auth = "user"`), the same signed-in user submits the approval as a new
invocation. Keep the same `session_id` and, if supplied, `input.actor`. The new request supplies
its own user credentials; the paused invocation's credentials are discarded. The browser normally
uses its existing authenticated session, so approval does not require a page refresh or another
login unless that session has expired. Automatic crash recovery still cannot recover OBO work.

Malformed middleware decisions return `INVALID_APPROVAL` before the resume value is checkpointed,
so the user can correct the decision and submit it with a new invocation ID.

The default checkpointer is process-local. Bind a managed Session Store to preserve multi-turn and
paused LangGraph state across restarts (session stores are off by default in `agentbricks dev`; the
binding takes effect after `agentbricks deploy`):

```bash
agentbricks sessions bind my-agent-sessions
```

### Crash recovery

Deployment with a Runtime Store supports invocation recovery after worker loss. Graph checkpoint
persistence requires a Session Store separately. Recovery can replay work, so tools must tolerate
repeated side effects. See [Recovery and durability](AGENTKIT_CONTRACT.md#recovery-and-durability).

### Chat app

The browser UI is included by default. It generates a stable application session ID in local
storage, sends it as the top-level `session_id`, and generates a fresh invocation UUID per turn.
Use `agentbricks init --framework langgraph --disable-chat-app` for API-only output.

### Configure and deploy

- Change the model, instructions, tools, graph, and framework-native execution in `agent/agent.py`.
- Change `runtime/adapter.py` only to map a different application input/output contract.
- Add local tools under `agent/tools/`; modules are auto-discovered.
- Add MCP servers in `agent/mcps.py` or with `agentbricks tools add mcp`.
- Bind long-term memory with `agentbricks memory bind <store>`; `agentbricks deploy` creates the
  store if it doesn't exist. Memory and session stores are off by default in `agentbricks dev` (the
  chat app shows "Not connected" for memory locally) and connect after deploy. To start with
  memories already in the store, create it and add entries before you bind and deploy:

  ```bash
  agentbricks memory stores create --name <store>    # prints a Store ID
  agentbricks memory entries create --store <Store ID> --actor-id you@example.com \
    --path /preferences/style.md --content "Prefers concise answers."
  ```

  `--path` is the entry's key in the store, not a file on your machine; the deployed chat app uses
  the signed-in user's email as the actor.
- Route the agent's model through a Unity Gateway model service you own with
  `agentbricks experimental models bind`, then search for a better model and prompt on your own
  eval set with `agentbricks experimental models upgrade`. These commands are experimental, so
  their flags may change between releases.

```bash
agentbricks --profile <profile> deploy agent-langgraph --source .
```

When deployment provisions a dedicated Runtime Store, only the app-owned
`databricks_agentkit_runtime_<hash>` schema and runtime tables are added. Managed Runtime Store
deployments use their own default schema.

To keep a session on one app replica (sticky routing), set the `X-Routing-Key` request header to your
stable session id on every call. It is a routing hint only: non-blank, no more than 128 UTF-8 bytes,
used verbatim, and it takes precedence over the legacy `__Host-databricks-app-router` cookie. It is not
authentication and is never used as the application's session id. Send that separately as the
top-level `session_id` in the request body.

## Request-user authorization

Declared tools in `agent.toml` select `auth = "user"` or `auth = "app"`; legacy missing auth
continues to use the application/default identity. Deployed user tools require the request resolver
and never fall back to application credentials. Model, memory-service, session-service, and custom
MCP server credentials are unchanged.

`runtime/main.py` derives the invocation policy after `configure()`. The runtime adapter namespaces
public session IDs and actor values for the request owner, then passes only `workspace_client_for`
to the framework-native agent. Internal session keys are never returned to clients.

User-policy invocations use the existing Runtime for synchronous, streaming, and background calls,
including status polling, event replay, and invocation-ID idempotency. The Runtime Store persists no
credential; request-user authentication remains process-local for the active first attempt. A
replacement attempt fails with `MCP_USER_AUTH_RECOVERY_UNSUPPORTED` before agent code runs.
Interactive approval uses a new authenticated invocation and rebuilds tools with that request's
credentials. The agent's existing namespaced memory, conversation store, and checkpointer behavior
is unchanged; OBO does not add another saver.

Existing generated projects must update their copies of `agent/agent.py` and `runtime/adapter.py`
to remove the OBO pause/resume rejection guards. Upgrading the installed package alone does not
rewrite these files. Keep the runtime's automatic-recovery guard.
