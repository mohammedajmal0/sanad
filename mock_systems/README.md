# mock_systems

A FastAPI mock of Najm's CRM, ERP, ITSM and a Teams channel. It runs locally in Docker Compose and is exposed to the agent as a custom MCP server.

**Phase:** 5

## Built

- **[api.py](api.py) (p5-mock-api, 2026-11-09):** one FastAPI app with four mock systems, holding state in memory:

  | System | Create | Read |
  |---|---|---|
  | ERP | `POST /erp/credit-notes` | `GET /erp/credit-notes/{id}` |
  | ITSM | `POST /itsm/tickets` | `GET /itsm/tickets/{id}` |
  | CRM | `POST /crm/cases` | `GET /crm/cases/{id}` |
  | Teams | `POST /teams/messages` | `GET /teams/messages?channel=` |

- **Every create needs an `Idempotency-Key` header.** Sending the same key again returns the first record, so a retry can't make a duplicate. Reusing a key with a different request returns 409.
- **The ERP follows the Credit Note and Refund Policy (`fin-credit-notes`).**
  - Every credit note is stored as `awaiting_approval`, with the approver the policy names for its amount: the team lead up to SAR 1,000, the regional sales manager up to 5,000, the finance manager above that, plus the CFO above 50,000.
  - It needs a reason code: `DUP`, `LATE`, `RET`, `PRC` or `OTH`.
  - An AI may draft but never approve, so there's no approval flag a client could set.
- **Tests:** [tests/test_mock_api.py](../tests/test_mock_api.py).
- **Run:**
  - with Docker: `docker compose -f mock_systems/compose.yaml up --build -d`, served on port 8100;
  - without Docker: `uv run --with-requirements mock_systems/requirements.txt uvicorn mock_systems.api:app --port 8100`.
- **[mcp_server.py](mcp_server.py) (p5-mcp-server, 2026-11-09):** the agent's seven tools over this API: `create_credit_note`, `get_credit_note`, `create_ticket`, `get_ticket`, `create_case`, `get_case` and `post_teams_message`.
  - Each call has a 5 s timeout and up to 3 attempts. Only timeouts, dropped connections and 5xx are retried, never 4xx.
  - Each create sends **one** `Idempotency-Key` on every attempt.
  - When every attempt fails, it says the system is unavailable and, for a create, not to try again.
  - The MCP endpoint is `/mcp` (streamable HTTP), served on port 8200, and it calls the API at `MOCK_API_URL`.
  - Tests: [tests/test_mcp_server.py](../tests/test_mcp_server.py).
- **Deployed (p5-deploy, 2026-11-09):** the Databricks App `sanad-mock-systems`, declared in [databricks.yml](../databricks.yml).
  - [app.py](app.py) serves the API and mounts the MCP server at `/mcp` in one process, and the MCP tools call the API on the same port. The tools are async, because sync tools deadlocked: the HTTP call waited on the event loop it was blocking.
  - Deploy and start: `databricks bundle deploy --profile sanad`, then `databricks bundle run sanad_mock_systems --profile sanad`.
  - State is in memory, so a restart empties it. Stop it with `databricks apps stop sanad-mock-systems --profile sanad`.
  - [ADR 0006](../docs/adr/0006-mock-systems-behind-a-custom-mcp-app.md) records the design.
- **Run both:**
  - with Docker: `docker compose -f mock_systems/compose.yaml up --build -d`;
  - without Docker: run the API command above, then `MOCK_API_URL=http://localhost:8100 uv run --with-requirements mock_systems/requirements.txt uvicorn mock_systems.mcp_server:app --port 8200`.

## You write

Mostly plumbing that Claude Code can draft. Run `/explain-back` on the idempotency and failure handling before you commit it.

## Done when

Stopping the mock API produces a graceful answer instead of a crash.
