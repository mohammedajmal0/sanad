# monitoring

Production monitoring config and the dashboard queries behind [docs/success-metrics.md](../docs/success-metrics.md).

**Phase:** 7

## What goes here

- Production monitoring on sampled traces, using the same judges as `evals/`.
- One AI/BI dashboard for quality, latency, cost, adoption and top failure types. It's fed by MLflow traces, evaluation runs and gateway usage tables.

## You write

- TODO(human): the alert thresholds, recorded in [docs/runbook.md](../docs/runbook.md).

## Done when

The dashboard shows live traffic.
