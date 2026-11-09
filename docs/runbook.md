# Runbook

How to tell Sanad is unhealthy, how to triage it, and how to roll back. Written in Phase 7 and tested on the game day.

## Services

| Service | Runs on | Owner |
|---|---|---|
| Sanad agent and chat UI | Agent Runtime on Databricks Apps | TODO(human) |
| Mock systems MCP server | Databricks Apps | TODO(human) |
| Lakeflow pipeline and file-arrival job `sanad_ingest` | Databricks Jobs | TODO(human) |
| AI Search index | AI Search endpoint | TODO(human) |
| Model endpoint | Unity AI Gateway | TODO(human) |

## SLOs

TODO(human): set each target and say why it's that number.

| SLO | Target | Measured from |
|---|---|---|
| Availability | | |
| p95 latency | | Traces |
| Correctness on sampled traces | | MLflow judges |
| Cost per conversation | | Gateway usage tables |

## Alerts

TODO(human): set each threshold and the first action it triggers.

| Alert | Threshold | First action |
|---|---|---|
| | | |

## Triage

These three usually break first in production.

### Stale or broken index

- Symptoms: TODO(human)
- Check: TODO(human)
- Fix: TODO(human)

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

- Symptoms: TODO(human)
- Check: TODO(human)
- Fix: TODO(human)

## Rollback

### Roll back a prompt

TODO(human): steps using the MLflow prompt registry.

### Roll back a deploy

TODO(human): steps using bundle targets and the previous app version.

## Game-day log

| Date | What we broke | Detected by | Time to recover | Runbook gaps found |
|---|---|---|---|---|
