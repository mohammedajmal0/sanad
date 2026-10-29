# Runbook

How to tell Sanad is unhealthy, how to triage it, and how to roll back. Written in Phase 7 and tested on the game day.

## Services

| Service | Runs on | Owner |
|---|---|---|
| Sanad agent and chat UI | Agent Runtime on Databricks Apps | TODO(human) |
| Mock systems MCP server | Databricks Apps | TODO(human) |
| Lakeflow pipeline and generator job | Databricks Jobs | TODO(human) |
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

- Symptoms: TODO(human)
- Check: TODO(human)
- Fix: TODO(human)

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
