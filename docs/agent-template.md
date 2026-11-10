# Agent template: start the next agent from Sanad

Sanad's reusable parts, and how to start a new governed agent with them. Use it to build, for example, a procurement or HR agent on the same platform. Nothing here is copied code: each row points to the working file in this repo, so the template can't drift from what runs.

**Time to scaffold:** not measured yet. Record the first real use in [success-metrics.md](success-metrics.md) (JD measure "reusable, maintainable delivery").

## 1. Scaffold the project (10 minutes)

```bash
agentbricks init <name> --framework langgraph   # LangGraph agent, chat UI, runtime, tests
cd <name> && agentbricks dev                      # runs locally
```

Then copy the parts below. Each row says what to change.

## 2. The reusable parts

| Part | Why it exists | Copy from | Change |
|---|---|---|---|
| **Answer contract** | Every turn ends in a checked object: answer, citations, confidence, next action. The UI, evaluations and audits all read it | [agent/agent/schema.py](../agent/agent/schema.py) | The `next_action` labels for your domain |
| **Formatter with code-written citations and fixed replies** | The model formats; code adds citations, writes exact refusals (`FIXED_REPLY`) and never loses a turn on bad JSON | [agent/agent/answer.py](../agent/agent/answer.py) | The fixed sentences |
| **Approval gate, default deny** | Every write tool pauses for a person; a new write tool is gated until someone decides otherwise | `approval_rules` and `_approval_request` in [agent/agent/agent.py](../agent/agent/agent.py) | The approval text per write tool |
| **Supervisor + specialists as tools** | One router, small focused specialists, each with only its own tools ([ADR 0005](adr/0005-supervisor-calls-specialists-as-tools.md)) | `SPECIALISTS` in [agent/agent/agent.py](../agent/agent/agent.py) | Your specialists and their descriptions |
| **Tools as Unity Catalog functions, run as the asking user** | Row filters and grants decide what each person sees; a hidden row gives 0 rows, not an error ([ADR 0004](adr/0004-run-tools-as-the-asking-user.md)) | [tools/functions.sql](../tools/functions.sql) (`get_invoice` is the shortest example) | Tables, the region guard join, the COMMENT (it's the tool description the model reads) |
| **Prompts in the registry** | Versioned, and rolled back in under a minute with an alias | [agent/agent/prompt.py](../agent/agent/prompt.py), [agent/agent/prompts/](../agent/agent/prompts/) | The prompts themselves |
| **Model service** | Fallback model, rate limits and gateway-side logging in one governed object | [governance/sanad_agent_model.json](../governance/sanad_agent_model.json), then `agentbricks experimental models bind` | Limits sized to your calls per question |
| **Evaluation harness** | Cases with expectations, code checks, LLM judges from another model family, gates that exit 1 | [evals/](../evals/) (`cases.py`, `checks.py`, `run_eval.py`) | Cases and thresholds (keep a reason for each) |
| **CI** | Tests on every push; red-team gate; deploy only after both | [.github/workflows/ci.yml](../.github/workflows/ci.yml) | Job names |
| **Metrics dashboard** | The eight success measures from small summary tables, refreshed on demand | [monitoring/refresh_metrics.py](../monitoring/refresh_metrics.py), [dashboards/sanad_metrics.lvdash.json](../dashboards/sanad_metrics.lvdash.json) | The app and experiment names |
| **Runbook** | SLOs with reasons, alerts, triage, rollback, game-day log | [docs/runbook.md](runbook.md) | Services and thresholds |

## 3. Day-one checklist

1. Write the agent card first ([agent-card.md](agent-card.md) shape): users, tools, data, what it may change.
2. One read tool as a UC function, with a grant to one group and a check query.
3. One specialist prompt, registered at `@production`.
4. Ten evaluation cases, with at least three red-team ones, and run them: `run_eval.py --only <ids>`.
5. Deploy, ask one question, and add a row to the runbook's game-day log after breaking something on purpose.

## 4. Don't copy

- Najm's prompts, cases and seeded data: they encode one business.
- The Free Edition workarounds noted in the runbook (stopped app compute, no trace spans). Check whether your workspace needs them.
