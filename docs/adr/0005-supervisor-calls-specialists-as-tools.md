# 0005: The supervisor calls each specialist as a tool

- **Status:** Accepted
- **Date:** 2026-11-09
- **Phase:** 4

## Context

Phase 4 is done when "the supervisor routes a question to one of three specialists". Two specialists exist:
- **Customer Service:** a LangGraph agent with four UC function tools, its own prompt and the `Answer` schema.
- **Ops Analytics:** the Genie agent *Sanad Ops Analytics*, bound in `agent.toml` (`genie_agent`, `auth = "user"`), which gives three tools: `ops_analytics_ask`, `_poll` and `_query_result`.

Service Desk follows in its own task.

The scenario asks the supervisor to route, to combine answers to two-part questions, and to ask clarifying questions ([scenario](../scenario.md)).

Constraints:
- The only model is `gpt-oss-120b`. It ignores forced tool calls and rejects a JSON schema together with tools (see `agent/agent/answer.py`).
- Approvals (`HumanInTheLoopMiddleware`) and the session checkpointer must keep working.

## Options

1. **Specialists as tools of a tool-calling supervisor.** Won; see Decision.
2. **A router node:** one classification call picks a specialist, then a fixed edge runs it. Lost.
   - It's cheaper: one call instead of three, and a deterministic path.
   - But it can't send a two-part question to two specialists, or ask before routing, without growing into option 1.
3. **The `langgraph-supervisor` package.** Lost. It's a new dependency for what `create_agent` plus `@tool` already does, and it hands over the message history in its own format.
4. **The managed Agent Bricks Supervisor Agent.** Lost. It's a no-code product outside this LangGraph project, and it would hide the routing this project exists to show.

## Decision

Option 1, in `agent/agent/agent.py`:
- **Customer Service:** the old agent becomes a sub-agent with only the UC tools. It's wrapped as one tool, `customer_service(question)`, which returns its `Answer`.
- **Ops Analytics:** the Genie tools are given to the supervisor directly. Genie is already an agent, so it needs no wrapper.
- **Routing:** the supervisor prompt `sanad.prompts.supervisor` holds the routing rules. The tool descriptions do the rest.
- **What stays on the supervisor:** the local tools, the approval gate and the checkpointer, so approvals and sessions work as before.
- **Specialists are stateless.** The sub-agent runs with `checkpointer=False`, so it never sees the conversation. That's why the supervisor prompt requires every question it sends to stand on its own.
- **Genie answers are cited** as `source: "query"` with Genie's `deep_link`, which opens the SQL and its rows.

Evidence, 2026-11-09, on the local agent:

| Test | Result |
|---|---|
| Gate A question | Routed to `customer_service`; the specialist's citations were kept unchanged in the final `Answer` (traces `tr-5d5bbe…`, `tr-068fe1…`) |
| Gate A pass rate, Customer Service prompt v1 | 1 of 3. The sub-agent sometimes stopped after the summary, or before `search_policies`. Same prompt, model and question as the single pass on 2026-11-08 |
| Gate A pass rate, Customer Service prompt v2 (two rules made explicit) | 4 of 4 |
| "Which region had the most late deliveries last quarter, and why?" | Only `ops_analytics_ask`: Jeddah 16.2%, Red Sea Cargo; cited as a `query` |
| Deployed app (`--allow-user-scope-update` added the `genie` scope), same question | Only `ops_analytics_ask`, run as me. The answer mis-stated 59.3% as a share of all Jeddah deliveries; it is Red Sea Cargo's own rate |
| Two-part question (Al-Faris duplicate, plus the worst carrier in Jeddah) | Split into two self-contained questions, one per specialist, then combined. The supervisor's format step once dropped the specialist's policy citation, so the specialists' citations are now carried over in code (`agent/agent/answer.py`) |

## Consequences

- **More model calls:** about three more per question, for the supervisor's pick, its reply and its format step.
- **Gate A gets weaker:** it sees only the top-level tool call (`customer_service`). The sub-agent's calls are nested spans in the same trace, but the gate doesn't check them.
- **A LangGraph workaround:** a nested graph inherits `durability="sync"` from the supervisor's run. With `checkpointer=False`, it then fails with `AttributeError: _put_checkpoint_fut` (LangGraph 1.2.20). The sub-agent is called with `durability="async"`; remove that when LangGraph fixes it.
- **The specialists' citations are kept in code, not by the model.** `StructuredAnswer` merges in any citation a specialist returned this turn. A specialist's own format step can still under-cite; one run cited only one of the two duplicate invoices. Phase 6 measures this with a citation scorer.
- **Sub-agent tokens may stream to the chat as typing deltas.** The final output comes only from the supervisor. Revisit with the chat UI in Phase 7.
- **The Genie binding names a development-target space id.** Production needs its own space and id (Phase 7).
- **A new specialist is one tool plus routing rules.** Service Desk will follow the Customer Service pattern.
