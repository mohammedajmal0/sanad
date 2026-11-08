# Phase 4: Agents: LangGraph supervisor, UC tools, structured output, memory

**Goal:** build agents that use tools and apply business rules safely.

**Done when:** the supervisor routes a question to one of three specialists, calls a UC function tool, returns a schema-validated answer, and asks for approval before any write.

**First milestone, Gate A:** the Customer Service agent finds the seeded duplicate invoice, cites the refund policy, and the trace shows every tool call.

## Read first

- [Agent Bricks CLI](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli)
- [Deploy agents on Databricks](https://docs.databricks.com/aws/en/agents/deploy/)

## Concepts to learn

- **Three layers.** The framework (LangGraph: which tool next, when to answer). The agent server (DurableAgentServer: HTTP, streaming, sessions). The runtime (Agent Runtime on Databricks Apps: hosting, URL, service principal).
- **Tools.** The model picks a tool by reading its name and description. The tool's output is the evidence the answer rests on.
- **Unity Catalog function tools run as the app's service principal** (`auth = "app"`), not as the person asking. Row filters and masks then see the service principal.
- **Tracing.** Every model call and tool call becomes a span in an MLflow trace, which is how Gate A proves what the agent did.
- **Human-in-the-loop.** A tool listed for approval pauses the graph, and a new request resumes it.

## Entries

### 2026-11-08: Scaffold the agent with the Agent Bricks CLI

**What we built:** the Agent Bricks project in [agent/](../../agent/), scaffolded with `agentbricks init --framework langgraph --name sanad-cs` (CLI 0.9.0, Beta).
- **Changes from the template:** the memory and session stores were unbound for now, and the model is `system.ai.gpt-oss-120b`.
- **Smoke tests:** it ran locally and was deployed once as the Databricks App `agent-bricks-sanad-cs`, now stopped. Both times the model called the sample tool. The deployed run left a trace in `/Shared/agentbricks_traces/sanad-cs-bevrqu`.
- **Lint and tests:** the root lint skips the template's `agent/runtime/`, and the root pytest runs only `tests/`.

The model choice and the README's run recipe were written by Claude at my request; I must be able to defend them.

**Key concepts:**
- The template already follows ADR 0001: `agent/agent.py:run_agent` uses no Agent Bricks types, and `runtime/` is the thin layer that serves it. A CLI change should touch `runtime/` and `agent.toml`, not the graph.
- **Free Edition shapes the platform choices:**
  - No Claude model is offered, so `experimental models list` decides what's possible.
  - Deploy works without memory and session stores.
  - An app keeps using compute until it is stopped.
- `agentbricks dev` is a convenience, not the agent. It wraps `databricks apps run-local` and adds a local MLflow server. The agent server alone (`uv run start-server`) uses about 380 MB.
- A tool result is evidence, so its format matters. `get_current_time` returns a time with no timezone, and the model labelled it "UTC" both times: wrong on the laptop (IST), right on the app (which runs in UTC). Sanad's tools must return values that can't be misread: timezones, currencies, units.
- Linux puts each app's processes in a cgroup. `systemd-oomd` kills the whole cgroup under memory pressure, so a child process can take its parent app down with it. `systemd-run --user -p MemoryMax=…` gives a process its own capped cgroup.

**Mistakes:**
- **VS Code was killed.** Claude ran `agentbricks dev` inside VS Code on a 7 GB laptop. It peaked above 2 GB at startup, and `systemd-oomd` killed the whole VS Code window twice, ending the session each time. The journal showed the cause. Fixed by running the agent server alone in a memory-capped user unit (recipe in the agent README).
- **Wrong Python version.** `uv` first built the agent's environment on Python 3.14. Pinned to 3.12 with `agent/.python-version`, matching the project standard.

**Interview questions:**
1. Your UC function tools run as the app's service principal. How do you make sure an account manager only sees their own region's customers through the agent?
2. Why keep the agent graph separate from the server that hosts it, and what does that buy you when the platform is in Beta?
3. A tool returns a timestamp without a timezone, and the model confidently calls it UTC. What does that teach you about designing tool outputs?
