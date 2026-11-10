# Runbook

How to tell Sanad is unhealthy, how to triage it, and how to roll back. Written in Phase 7 and tested on the game day (2026-11-10). The SLOs, alerts and triage steps were written by Claude at my request; I must be able to defend each one.

## Services

| Service | Runs on | Owner |
|---|---|---|
| Sanad agent and chat UI (`agent-bricks-sanad-cs`) | Agent Runtime on Databricks Apps | me |
| Mock systems MCP server (`sanad-mock-systems`) | Databricks Apps (bundle) | me |
| Lakeflow pipeline and file-arrival job `sanad_ingest` | Databricks Jobs (bundle) | me |
| AI Search index `sanad.ai.chunks_index` | AI Search endpoint | me |
| Model service `sanad.ai.sanad_agent_model` (gpt-oss-120b, fallback Llama 3.3 70B) | Unity Gateway | me |

Both apps stop when idle on Free Edition. Start the compute (Apps UI → Start) before deploying: `agentbricks deploy` waits for it but never starts it.

## SLOs

| SLO | Target | Why that number | Measured from |
|---|---|---|---|
| Availability | 99% of turns complete (not "Request failed") per week | A failed turn loses the user's question; at demo scale, one failure in 100 is noticeable but survivable | App log (`Invocation execution failed`), trace records |
| p90 latency | ≤ 60 s | A manager waiting longer than a minute goes back to the three old systems (Phase 6 threshold) | Evaluation runs; `sanad.ops.gateway_daily.p90_latency_s` per model call |
| Correctness | ≥ 85% on the evaluation set | Phase 6 floor: allows two misses in about 15 judged cases. No production judges: they would cost model calls on every sampled turn | `sanad.ops.eval_scores` (dashboard) |
| Cost | ≤ 15,000 billed tokens per question | Phase 6 ceiling: about 60% above the baseline (9,135), so a prompt loop shows up but normal variation doesn't | Evaluation runs; production tokens per day in `gateway_daily` |

Latency depends on the shared model gateway: on 2026-11-10 it was 72–76 s with no change on our side (see the Phase 6 log).

## Alerts

Frugal by design: there is no always-on alerting. These are checked whenever `monitoring/refresh_metrics.py` runs (after an evaluation or before a demo), plus the CI gate on every push.

| Alert | Threshold | First action |
|---|---|---|
| Red-team gate fails in CI | any threshold in the `red-team` gate | Nothing deploys (`deploy` needs it). Read the failing cases, as in Phase 6 |
| Thumbs-up rate drops | below 70% once there are at least 10 thumbs | Read the 👎 turns: the request in the trace record, the model calls in `sanad.ops.sanad_agent_model_payload`, and the app log |
| Production gateway errors | `error_rate` above 5% on a day | `databricks ai-gateway get-model-service model-services/sanad.ai.sanad_agent_model` for its limits; see "Gateway refusal" below |
| Production token spike | over 500,000 tokens on a day | Look for a loop in the inference table. The service caps the app at 1M tokens an hour |
| Formatter fallbacks | more than 5 "StructuredAnswer fell back" warnings in a day of app log | Replay one locally with tracing on, to catch the empty output (agent card, Known limitations) |

## Triage

These three usually break first in production.

### Stale or broken index

- **Symptoms:** answers say no policy covers something that one does, or cite an older version of a policy; `search_policies` returns nothing for a question that used to work (for example "How soon must we tell a customer about a duplicate invoice?" should return `fin-duplicate-invoices`).
- **Check:**
  1. Run the check query in [tools/functions.sql](../tools/functions.sql) §6: `SELECT doc_id, title FROM sanad.ai.search_policies('We billed a customer twice. How soon must we tell them?')`.
  2. In Catalog Explorer, open `sanad.ai.chunks_index`: is the index online, and when did it last sync?
  3. A 403 means the caller lacks `SELECT` on the index (ADR 0004), not a broken index.
- **Fix:** sync the index from its source table (Catalog Explorer → the index → Sync now), then re-run the check query. If the source table is stale, re-run the Phase 3 pipeline first.

### Tool timeouts (mock systems, Genie, UC functions)

Written by Claude at my request (p5-fallback, 2026-11-09); the game day tests it.

- **Symptoms:**
  - an answer says "the ERP / ITSM / CRM / Teams is unavailable";
  - or the supervisor says a system "can't be reached right now", meaning its tools were missing for that turn;
  - turns take about 15 s longer than usual, from retries against a slow system;
  - for Genie, `ops_analytics_ask` returns `timed_out` with ids.
- **Check:**
  1. **Mock systems:** `curl -s <mock api>/health` and `curl -s -o /dev/null -w '%{http_code}' <mcp server>/mcp`.
  2. **Agent logs:**
     - "Failed to fetch optional MCP tools from server 'najm_systems'" means the MCP server was down when the turn started;
     - the tool message "is unavailable (ConnectError after 3 attempts)" means the API is down behind a running MCP server.
  3. **Genie:** `databricks genie list-spaces` and the space's warehouse state.
  4. **UC functions:** a direct `SELECT * FROM sanad.ai.<function>(...)` on the warehouse; a cold warehouse adds tens of seconds.
- **Fix:**
  - Restart whichever is down: API first, then the MCP server. New turns pick the tools up again with no agent restart, because tools are discovered every turn.
  - **Never re-send a failed write blindly.**
    - "The request never reached it, so nothing was saved": the user can safely ask again.
    - "It may still have been saved": read the record first, then decide, because a retried create with a new key could duplicate it.
  - A slow, not down, system: the adapter tries 3 times with a 5 s timeout. Raise `TIMEOUT_S` in `mock_systems/mcp_server.py` only if the system is known to be slow, and keep the agent's MCP timeout (30 s in `agent/agent/mcps.py`) above the adapter's worst case.

### Prompt regression

- **Symptoms:** thumbs-up rate falls after a prompt change; the red-team gate fails in CI; follows guidelines or tool choice drops on the dashboard. Phase 6 saw all three: one rule fixed a case and broke two others.
- **Check:**
  1. Which version is live: `mlflow.genai.load_prompt("prompts:/sanad.prompts.supervisor@production").version` (and the same for `customer_service`).
  2. Compare the last two evaluation runs on the dashboard, then read the failing cases one by one.
- **Fix:** roll the alias back (below, under a minute and no redeploy), then re-run only the failing cases: `run_eval.py --only <ids>`.

### Gateway refusal (found on the game day)

- **Symptoms:** "Request failed … PermissionDeniedError" or "RateLimitError" in the chat UI; the turn fails rather than answering. The fallback model doesn't help: it covers a destination failing, not the service refusing.
- **Check:** `databricks ai-gateway get-model-service model-services/sanad.ai.sanad_agent_model` for the rate limits; `gateway_daily` for today's production requests and tokens.
- **Fix:**
  - A real spike: wait for the minute or hour to renew, or raise the limit with `update-model-service … config.rate_limits` and record why.
  - A loop: find it in the inference table first.
  - **Known gap:** the agent doesn't turn a gateway refusal into a friendly answer. That would be a catch around the model call, like the formatter fallback.

## Rollback

### Roll back a prompt

Tested on the game day: v13 → v12 in about 40 s, back in 14 s, with no redeploy (the agent loads `@production` on every turn, in eval and deployed alike).

```python
import mlflow
mlflow.set_registry_uri("databricks-uc")
mlflow.genai.set_prompt_alias("sanad.prompts.supervisor", alias="production", version=12)
```

Then confirm with `load_prompt(...@production).version`, and write down the version you left and why.

### Roll back a deploy

Code, `agent.toml` and the bundle are all in git, so a rollback is a deploy of the last good commit:

1. Find it: `git log --oneline` (each deploy-worthy change is its own commit).
2. Agent: `git checkout <good> -- agent && cd agent && agentbricks --profile sanad deploy sanad-cs --source .` (start the app compute first if it's stopped).
3. Bundle resources (mock systems, dashboards, Genie space, pipeline): `git checkout <good> -- databricks.yml dashboards genie mock_systems pipelines && databricks bundle deploy --profile sanad`.
4. Ask one question (for example "Which region is Al-Faris Trading in?"), then restore the working tree with `git checkout HEAD -- .` and fix forward on a branch.

A prompt problem doesn't need this: roll back the alias instead.

## Game-day log

| Date | What we broke | Detected by | Time to recover | Runbook gaps found |
|---|---|---|---|---|
| 2026-11-09 | Mock API stopped, then the MCP server too (Phase 5) | The answer named the unavailable system | Restart, then the next turn worked | The "nothing was done" claim was dishonest; fixed in the adapter and prompt |
| 2026-11-10 | Supervisor prompt rolled back v13 → v12 | Confirmed the agent loads v12's text | ~40 s, then 14 s back | None: the steps above worked as written |
| 2026-11-10 | App's gateway limit set to 0 requests/min | The turn failed: `PermissionDeniedError … rate limit is set to 0` | Limit restored in seconds | No friendly answer on refusal (now under "Gateway refusal"). The fallback model doesn't cover refusals |
| 2026-11-10 | Formatter returned empty output (found by a user's 👎, not staged) | "Request failed" in the UI, then the app log | Fixed in code the same evening | Turns now fall back to the agent's reply, flagged |
