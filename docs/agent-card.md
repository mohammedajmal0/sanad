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
| Supervisor | `customer_service`, `service_desk` and the Genie agent `ops_analytics` as tools ([ADR 0005](adr/0005-supervisor-calls-specialists-as-tools.md)); Najm's systems through the MCP server in `mock_systems/`: `create_credit_note`, `create_ticket`, `create_case`, `post_teams_message`, and `get_*` reads | Session store `sanad-sessions`; memory store `sanad-memory` (the user's own preferences only, never tool data) | Post a summary to a Teams channel (`post_teams_message`); every write below is also called by the supervisor and pauses for approval |
| Customer Service | UC functions `get_customer_summary`, `get_invoices`, `get_invoice`, `get_shipment_status`; policy retrieval (`search_policies`) with citations | `gold` ERP and CRM tables; returns and SLA policies | Draft a credit note (`create_credit_note`). The ERP holds every draft for the approver `fin-credit-notes` names for its amount: team lead, regional sales manager, finance manager, or finance manager plus CFO. Open a CRM case (`create_case`) |
| Ops Analytics | Genie agent *Sanad Ops Analytics* ([definition](../genie/ops_analytics.geniespace.json), deployed by the bundle) | `gold.delivery_sla_by_region`; the late rate is `SUM(late) / SUM(delivered)` | None (read-only) |
| Service Desk | UC function `get_ticket_trend` (incident check: busiest days against a typical day); KB retrieval (`search_policies`); mock ITSM through MCP | Past tickets; KB articles | Open a ticket (`create_ticket`, with an idempotency key); update or route one (later) |

## Models

- **Primary: `system.ai.gpt-oss-120b`**, through the AI Gateway. Free Edition offers no Claude model. On 2026-11-08, `agentbricks experimental models list` showed gemma-3-12b, gpt-oss-120b and -20b, llama-4-maverick, llama-3.1-8b, llama-3.3-70b, qwen3-next-80b and qwen35-122b. gpt-oss-120b called tools correctly in the first smoke test, locally and deployed. Chosen by Claude at my request.
- **Fallback:** a second model through the same gateway, for example `system.ai.meta-llama-3-3-70b-instruct` (Phase 7).

## Answer shape

Every answer follows the Pydantic schema in [agent/agent/schema.py](../agent/agent/schema.py):
- `answer`: plain text.
- `citations`: each a `document` (doc_id), a `record` (invoice, order, shipment or account id), or a `query` (an Ops Analytics answer, cited by the Genie `deep_link` that opens its SQL and rows).
- `confidence`: `high`, `medium` or `low`. An answer without citations must be `low`.
- `next_action`: `none`, `draft_credit_note`, `open_case`, `open_ticket`, `ask_user`, `out_of_scope` or `decline_memory`. For the last two, code writes the reply (`FIXED_REPLY` in [agent/agent/answer.py](../agent/agent/answer.py)).

The chat shows `answer`, and the whole object is in the final message's `additional_kwargs["answer"]`. The system prompts are `sanad.prompts.supervisor@production` and `sanad.prompts.customer_service@production` in the MLflow Prompt Registry. Their sources are in [agent/agent/prompts/](../agent/agent/prompts/).

## Known limitations

Found during Phases 6 and 7. Written by Claude at my request; I must be able to defend each one.

- **Production traces have no spans.** Deployed traces keep their record (id, duration, request and answer preview) and the user's thumbs, but not the step-by-step spans: the app can't reach cloud storage on this workspace. Debug a production answer from the app log, or replay it locally. The upgrade path is MLflow's trace storage in Unity Catalog tables (it needs the "OpenTelemetry on Databricks" preview, which this Free Edition workspace doesn't offer: checked in Settings → Previews on 2026-11-10). Decided to keep it simple. For a demo, show full traces from an evaluation run (`/Shared/sanad-evals`).
- **The answer formatter sometimes returns empty output.** It happened in 1 of 5 local replays of one conversation, and on one deployed turn. The turn no longer fails: the user gets the agent's own reply, marked "not checked against the answer format", and the app log has a WARNING. The cause is unknown.
- **Latency depends on the model gateway.** On a slow gateway day, p90 was 72–76 s against a 60 s target. Two of the seven model calls in a typical turn only format the Answer JSON.
- **No counts across customers for invoices.** Customer Service looks up one customer at a time; Ops Analytics covers delivery performance. "How many invoices are there?" has no tool behind it (evaluation case `fb-invoice-count`).
- **Vague questions get a question back.** "Duplicate invoices" without a customer gets "which customer?" (rule 5), which is honest but not as helpful as listing flagged duplicates.
- **A gateway refusal fails the turn.** If the model service refuses (rate limit), the user sees "Request failed"; the fallback model covers a failing destination, not a refusal (game day, 2026-11-10).
- **Evaluations are single-turn.** Every case is one fresh question, so failures that only show on a follow-up turn (like the formatter crash) aren't covered.

## Latest evaluation scores

Filled in from MLflow evaluation runs starting in Phase 6. Targets live in [success-metrics.md](success-metrics.md).

| Run | Date | Correctness | Groundedness | Safety | PII leaks | p90 latency | Billed tokens per question (mean) |
|---|---|---|---|---|---|---|---|
| baseline `5fce068b` | 2026-11-10 | 0.933 | 0.950 | 0.962 | 0 | 45 s | 9,135 |
| gate-check-1 `bd0fd808` (4 workers) | 2026-11-10 | 0.875 | 0.955 | 1.000 | 0 | 72.3 s | 10,801 |
