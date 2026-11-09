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
| Supervisor | `customer_service` and the Genie agent `ops_analytics` as tools ([ADR 0005](adr/0005-supervisor-calls-specialists-as-tools.md)); mock Teams webhook (Phase 5) | Conversation memory | Post a summary to a Teams channel |
| Customer Service | UC functions `get_customer_summary`, `get_invoices`, `get_shipment_status`; policy retrieval (`search_policies`) with citations | `gold` ERP and CRM tables; returns and SLA policies | Draft a credit note; open a case. Credit notes above SAR 5,000 need manager approval |
| Ops Analytics | Genie agent *Sanad Ops Analytics* ([definition](../genie/ops_analytics.geniespace.json), deployed by the bundle) | `gold.delivery_sla_by_region`; the late rate is `SUM(late) / SUM(delivered)` | None (read-only) |
| Service Desk | Similar-ticket search; KB retrieval; mock ITSM API via MCP | Past tickets; KB articles | Create, update or route a ticket (idempotency key on create) |

## Models

- **Primary: `system.ai.gpt-oss-120b`**, through the AI Gateway. Free Edition offers no Claude model. On 2026-11-08, `agentbricks experimental models list` showed gemma-3-12b, gpt-oss-120b and -20b, llama-4-maverick, llama-3.1-8b, llama-3.3-70b, qwen3-next-80b and qwen35-122b. gpt-oss-120b called tools correctly in the first smoke test, locally and deployed. Chosen by Claude at my request.
- **Fallback:** a second model through the same gateway, for example `system.ai.meta-llama-3-3-70b-instruct` (Phase 7).

## Answer shape

Every answer follows the Pydantic schema in [agent/agent/schema.py](../agent/agent/schema.py):
- `answer`: plain text.
- `citations`: each a `document` (doc_id), a `record` (invoice, order, shipment or account id), or a `query` (an Ops Analytics answer, cited by the Genie `deep_link` that opens its SQL and rows).
- `confidence`: `high`, `medium` or `low`. An answer without citations must be `low`.
- `next_action`: `none`, `draft_credit_note`, `open_case` or `ask_user`.

The chat shows `answer`, and the whole object is in the final message's `additional_kwargs["answer"]`. The system prompts are `sanad.prompts.supervisor@production` and `sanad.prompts.customer_service@production` in the MLflow Prompt Registry. Their sources are in [agent/agent/prompts/](../agent/agent/prompts/).

## Known limitations

TODO(human): add each limitation as you find it, especially during the Phase 6 red-team runs and the Phase 7 game day.

## Latest evaluation scores

Filled in from MLflow evaluation runs starting in Phase 6. Targets live in [success-metrics.md](success-metrics.md).

| Run | Date | Correctness | Groundedness | Safety | PII leaks | p95 latency | Cost per request |
|---|---|---|---|---|---|---|---|
