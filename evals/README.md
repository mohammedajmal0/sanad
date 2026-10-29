# evals

MLflow 3 evaluation datasets, scorers, the red-team set and `run_eval.py`.

**Phase:** 6 (Gate B)

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
