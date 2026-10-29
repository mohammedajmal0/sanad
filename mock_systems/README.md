# mock_systems

A FastAPI mock of Najm's CRM, ERP, ITSM and a Teams channel. It runs locally in Docker Compose and is exposed to the agent as a custom MCP server.

**Phase:** 5

## What goes here

- REST endpoints for CRM, ERP and ITSM reads and writes, plus a Teams webhook.
- An idempotency key on ticket creation, so a retried call can't create a duplicate.
- A Dockerfile and Docker Compose setup for local dev.
- The MCP server, deployed on Databricks Apps (one of the three Free Edition apps).

## You write

Mostly plumbing that Claude Code can draft. Run `/explain-back` on the idempotency and failure handling before you commit it.

## Done when

Stopping the mock API produces a graceful answer instead of a crash.
