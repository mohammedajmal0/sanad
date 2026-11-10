# monitoring

Production monitoring config and the dashboard queries behind [docs/success-metrics.md](../docs/success-metrics.md).

**Phase:** 7

## What goes here

- Production monitoring on sampled traces, using the same judges as `evals/`.
- One AI/BI dashboard for quality, latency, cost, adoption and top failure types. It's fed by MLflow traces, evaluation runs and gateway usage tables.

## Success-metrics dashboard (2026-11-10)

`Sanad success metrics` (dashboards/sanad_metrics.lvdash.json, deployed by the bundle) reads three small tables in `sanad.ops`:

| Table | From | Grain |
|---|---|---|
| `eval_scores` | `system.mlflow.runs_latest`, experiment `/Shared/sanad-evals` | one row per full evaluation run |
| `gateway_daily` | `system.ai_gateway.usage` | day × production (the app's principal) / testing |
| `app_feedback` | the app experiment's trace records (MLflow API) | day × production / dev: questions, conversations, thumbs |

Refresh them on demand (about a minute of warehouse time; no schedule):

    cd agent && DATABRICKS_CONFIG_PROFILE=sanad uv run python ../monitoring/refresh_metrics.py

Frugal by design: the dashboard never scans system tables, and the tables hold counts only (no e-mails, IP addresses or question text).

## You write

- TODO(human): the alert thresholds, recorded in [docs/runbook.md](../docs/runbook.md).

## Done when

The dashboard shows live traffic.
