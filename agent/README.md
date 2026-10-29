# agent

The Agent Bricks project: `agent.toml`, the LangGraph graph, prompts and schemas.

**Phases:** 4 (first agent, Gate A) and 5 (supervisor, three specialists, actions, memory)

> `agentbricks init --framework langgraph` in Phase 4 scaffolds files here and may write its own README. Merge this one into it then.

## What goes here

- Phase 4: the Customer Service agent, a retrieval tool that returns citations, a system prompt in the MLflow prompt registry, and a Pydantic answer schema (`answer`, `citations`, `confidence`, `next_action`).
- Phase 5: a supervisor graph, Ops Analytics (Genie agent) and Service Desk specialists, an approval interrupt before every write, session and memory stores in `agent.toml`, and retries with backoff.
- Agent logic stays in plain LangGraph modules. The Databricks serving layer stays thin ([ADR 0001](../docs/adr/0001-isolate-beta-features.md)).

## You write

- TODO(human): the system prompt and the answer schema (Phase 4).
- TODO(human): routing rules, business rules (e.g. credit notes above SAR 5,000 need manager approval) and the approval message wording (Phase 5).

## Done when

- Gate A: the agent finds the seeded duplicate invoice, cites the refund policy, and the trace shows every tool call.
- Phase 5: a question needing two agents works, and every write pauses for approval.
