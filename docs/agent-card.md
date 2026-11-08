# Agent card: Sanad

## Purpose

Sanad answers billing, delivery, analytics and IT-support questions for Najm Supply Co. staff. It uses live ERP, CRM and ITSM data plus policy and KB documents. It proposes actions, and it executes them only after a human approves.

## Users

| Group | Uses | Sees |
|---|---|---|
| `account_managers` | Customer Service agent | Their region's customers only; contact PII masked unless granted |
| `ops_managers` | Ops Analytics agent | Gold tables, read-only |
| `it_support` | Service Desk agent | Tickets and KB articles |

## Agents and tools

| Agent | Tools | Data | Write actions (approval required) |
|---|---|---|---|
| Supervisor | Routing; mock Teams webhook | Conversation memory | Post a summary to a Teams channel |
| Customer Service | UC functions `get_customer_summary`, `get_invoices`, `get_shipment_status`; policy retrieval with citations | `gold` ERP and CRM tables; returns and SLA policies | Draft a credit note; open a case. Credit notes above SAR 5,000 need manager approval |
| Ops Analytics | Genie agent over gold tables | `gold` tables; metric definitions | None (read-only) |
| Service Desk | Similar-ticket search; KB retrieval; mock ITSM API via MCP | Past tickets; KB articles | Create, update or route a ticket (idempotency key on create) |

## Models

- **Primary: `system.ai.gpt-oss-120b`**, through the AI Gateway. Free Edition offers no Claude model. On 2026-11-08, `agentbricks experimental models list` showed gemma-3-12b, gpt-oss-120b and -20b, llama-4-maverick, llama-3.1-8b, llama-3.3-70b, qwen3-next-80b and qwen35-122b. gpt-oss-120b called tools correctly in the first smoke test, locally and deployed. Chosen by Claude at my request.
- **Fallback:** a second model through the same gateway, for example `system.ai.meta-llama-3-3-70b-instruct` (Phase 7).

## Answer shape

Every answer follows a Pydantic schema: `answer`, `citations`, `confidence`, `next_action`. It is defined in Phase 4.

## Known limitations

TODO(human): add each limitation as you find it, especially during the Phase 6 red-team runs and the Phase 7 game day.

## Latest evaluation scores

Filled in from MLflow evaluation runs starting in Phase 6. Targets live in [success-metrics.md](success-metrics.md).

| Run | Date | Correctness | Groundedness | Safety | PII leaks | p95 latency | Cost per request |
|---|---|---|---|---|---|---|---|
