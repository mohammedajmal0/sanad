# evals

MLflow 3 evaluation datasets, scorers, the red-team set and `run_eval.py`.

**Phase:** 6 (Gate B)

## Gate A (Phase 4)

[gate_a.py](gate_a.py) asks the agent the Al-Faris question and checks that the `Answer` cites `INV-027711`, `INV-050001` and `fin-duplicate-invoices`, and that the MLflow trace has a span for every tool call. The pass/fail rule is tested in [tests/test_gate_a.py](../tests/test_gate_a.py). Passed on 2026-11-08 (`--local`). See the [agent README](../agent/README.md) for why the deployed app's traces have no spans.

## Ops Analytics check (Phase 4)

[ops_genie.py](ops_genie.py) asks the Genie agent *Sanad Ops Analytics* "Which region had the most late deliveries last quarter, and why?". It passes when the answer names Jeddah and Red Sea Cargo and the SQL doesn't average `late_rate`. The question is deliberately not one of the space's example SQLs. The rule is tested in [tests/test_ops_genie.py](../tests/test_ops_genie.py). Passed on 2026-11-09, after two rounds of tuning (see the learning log).

## What goes here

- About 100 cases: 60 normal, 20 multi-step, 20 adversarial (an injected instruction hidden in a KB document, PII extraction attempts, out-of-scope requests).
- Built-in judges: Correctness, RetrievalGroundedness, Safety, RelevanceToQuery, Guidelines.
- Custom scorers: correct tool chosen, no PII leaked, cost per request, latency, task completed.
- Judge calibration: 20 traces labelled by you, compared against the judges.
- A baseline run plus two improvements (e.g. a new prompt version and reranking), compared.

## You write

- TODO(human): the adversarial cases.
- TODO(human): the guideline text for the Guidelines judge.
- TODO(human): the pass thresholds, with a reason for each.

## Done when

Gate B: your thresholds are met, for example correctness at least 0.85, groundedness at least 0.9 and zero PII leaks.
