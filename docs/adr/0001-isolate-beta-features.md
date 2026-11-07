# 0001: Isolate Beta features behind a thin serving layer

- **Status:** Accepted (2026-11-07)
- **Date:** 2026-10-29
- **Phase:** 0

## Context

Two pieces Sanad depends on are in Beta: the Agent Bricks CLI (scaffolding, `agent.toml`, deploy to Agent Runtime) and Unity AI Gateway. Beta APIs and file layouts can change during the 8-week build. Several Databricks products were also renamed in 2026, so examples online often show older patterns.

## Options

1. **Build directly on Agent Bricks conventions everywhere**: fastest start. But a CLI or `agent.toml` change would ripple through graph, tools and tests.
2. **Plain LangGraph modules with a thin Databricks serving layer**: agent logic, state, routing and schemas live in framework-level Python. Only the serving and deploy wiring touches Agent Bricks.
3. **Avoid Beta features and use the legacy agent server only**: stable, but it skips Agent Runtime and Unity AI Gateway, which the JD and the production phase need.

## Decision

Option 2. Keep agent logic in plain LangGraph modules under `agent/`. Keep the Databricks-specific serving layer thin and in one place. If the Agent Bricks CLI changes, only that layer changes.

Restated by Claude at my request (2026-11-07): Beta tools change without warning. If the agent's logic is written in the Beta tool's own format, every change to that tool breaks the whole agent. If the logic is ordinary Python and only a small wrapper talks to the Beta tool, a change means fixing that one wrapper, and the logic can still be tested on a laptop without Databricks.

## Consequences

- Graph, tools and schemas can be unit-tested locally without Databricks.
- There is a little extra wiring between the plain modules and the serving layer.
- Revisit in Phase 7 if Unity AI Gateway can't be enabled on Free Edition and the 14-day trial is needed.
