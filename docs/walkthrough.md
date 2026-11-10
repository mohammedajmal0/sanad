# Walkthrough: give the agent a new tool in 30 minutes

For an engineer new to this repo. You'll add a tool, give it to a specialist, prove it with an evaluation case, and ship it. It is the same path Sanad's `get_invoice` took on 2026-11-10 (see the Phase 6 learning log).

**The exercise:** "How many invoices are there?" has no tool behind it today. The agent once answered that "the available data does not include invoice records", which is false. Evaluation case `fb-invoice-count` checks it. You'll add a tool that counts the caller's invoices.

**Before you start:** `databricks auth login --profile sanad` works, and you've read [agent-template.md](agent-template.md) §2.

## 0–5 min: Orient

- The supervisor routes, and specialists own tools: `SPECIALISTS` in [agent/agent/agent.py](../agent/agent/agent.py).
- Tools are SQL functions that run **as the person asking**, so row filters apply ([ADR 0004](adr/0004-run-tools-as-the-asking-user.md)).
- Every answer ends in the `Answer` schema with citations ([agent/agent/schema.py](../agent/agent/schema.py)).

## 5–12 min: Write the tool

Copy `get_invoice` in [tools/functions.sql](../tools/functions.sql) §8 and change it:

- **Name and signature:** `sanad.ai.count_invoices()`, returning invoices and flagged invoices per region.
- **The region guard:** read `silver.invoices` through a join on `gold.customer_360`, so callers count only their own region.
- **The COMMENT:** it's the description the model reads. Say when to use the tool ("how many invoices…") and when not to (a single customer's invoices → `get_invoices`).
- **The grant:** `GRANT EXECUTE … TO account_managers`, plus a check query with its expected result.

Run it on the warehouse and check the result by hand.

## 12–17 min: Give it to a specialist

1. Add a `[[tools]]` entry in [agent/agent.toml](../agent/agent.toml).
2. Add the id to Customer Service's set in `SPECIALISTS` (if you forget, it lands on the supervisor; `agent/tests/test_answer_schema.py` checks this).
3. Add one rule to [customer_service.md](../agent/agent/prompts/customer_service.md): which questions use it.
4. Register the prompt: `cd agent && DATABRICKS_CONFIG_PROFILE=sanad uv run python -m agent.prompt customer_service`.

## 17–25 min: Prove it

1. Add `"expected_tools": [CS, "count_invoices"]` to `fb-invoice-count` in [evals/cases.py](../evals/cases.py).
2. Start the mock systems ([mock_systems/README.md](../mock_systems/README.md)), then run only that case and its neighbours:

   ```bash
   cd agent && DATABRICKS_CONFIG_PROFILE=sanad MOCK_MCP_URL=http://localhost:8200/mcp \
     uv run python ../evals/run_eval.py --name count-invoices --only fb-invoice-count,cs-unknown,cs-summary
   ```

3. Open the run in `/Shared/sanad-evals` and read the trace: did the supervisor route to Customer Service, and did it call the new tool?

**The lesson Sanad learned four times:** a prompt rule can break other cases. Before you ship, run the whole set once (about 22 minutes).

## 25–30 min: Ship

1. `uv run pytest` (repo root and `agent/`), then commit.
2. Start the app's compute in the Apps UI, then `cd agent && agentbricks --profile sanad deploy sanad-cs --source .`.
3. Ask the deployed agent the question, then refresh the dashboard: `uv run python ../monitoring/refresh_metrics.py`.
4. If it goes wrong, roll back the prompt alias ([runbook](runbook.md#roll-back-a-prompt)).

## Check yourself

- Why does the tool join `customer_360` instead of reading `silver.invoices` directly?
- What would the agent do if the COMMENT were vague?
- Why run three cases first and the whole set before shipping?
