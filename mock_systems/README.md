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
- **The ERP enforces Najm's SAR 5,000 rule itself.** Above that, a credit note is stored as `waiting_for_manager`. There is no "manager approved" flag a client could set.
- **Tests:** [tests/test_mock_api.py](../tests/test_mock_api.py).
- **Run:**
  - with Docker: `docker compose -f mock_systems/compose.yaml up --build -d`, served on port 8100;
  - without Docker: `uv run --with-requirements mock_systems/requirements.txt uvicorn mock_systems.api:app --port 8100`.
- **Next:** the MCP server in front of this API (`p5-mcp-server`).

## You write

Mostly plumbing that Claude Code can draft. Run `/explain-back` on the idempotency and failure handling before you commit it.

## Done when

Stopping the mock API produces a graceful answer instead of a crash.
