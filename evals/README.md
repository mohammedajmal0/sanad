# evals

MLflow 3 evaluation datasets, scorers, the red-team set and `run_eval.py`.

**Phase:** 6 (Gate B)

## Gate A (Phase 4)

[gate_a.py](gate_a.py) asks the agent the Al-Faris question and checks that the `Answer` cites `INV-027711`, `INV-050001` and `fin-duplicate-invoices`, and that the MLflow trace has a span for every tool call. The pass/fail rule is tested in [tests/test_gate_a.py](../tests/test_gate_a.py). Passed on 2026-11-08 (`--local`). See the [agent README](../agent/README.md) for why the deployed app's traces have no spans.

## Ops Analytics check (Phase 4)

[ops_genie.py](ops_genie.py) asks the Genie agent *Sanad Ops Analytics* "Which region had the most late deliveries last quarter, and why?". It passes when the answer names Jeddah and Red Sea Cargo and the SQL doesn't average `late_rate`. The question is deliberately not one of the space's example SQLs. The rule is tested in [tests/test_ops_genie.py](../tests/test_ops_genie.py). Passed on 2026-11-09, after two rounds of tuning (see the learning log).

## Evaluation harness (Phase 6)

- **[cases.py](cases.py): 33 cases** (19 normal, 5 multi-step, 9 red team).
  - Each case says what a good answer must contain, cite or avoid: expected facts, citations, tools that must or mustn't run, the write it must pause on, and rules for the guidelines judge.
  - Expectations come from the seeded data and the policy text.
- **[checks.py](checks.py): code checks,** exact and repeatable, tested in [tests/test_eval_checks.py](../tests/test_eval_checks.py). They cover:
  - tool choice;
  - citations;
  - no PII (e-mails, Saudi mobile numbers);
  - writes never run and pause only where expected;
  - the gate.
- **[run_eval.py](run_eval.py): runs the agent in-process** and scores each case with MLflow 3 (`mlflow.genai.evaluate`), recording one trace per case in the experiment `/Shared/sanad-evals`.
  - Code scorers: `tool_choice`, `cited`, `no_pii`, `writes_need_approval`, `total_tokens`, `latency_s`.
  - LLM judges: `correctness`, `grounded` (against the tool outputs in the trace), `follows_guidelines` and `safe`. The judge is `system.ai.qwen35-122b-a10b`, a different model family from the agent's, so the agent never grades itself.
  - With `--gate`, it exits 1 if any threshold is missed.
- **It runs as the person running it,** so their groups decide what the tools return. Nobody approves anything in an evaluation, so any write that runs is a failure.

```bash
# the mock systems on ports 8100 and 8200 first (mock_systems/README.md)
cd agent && DATABRICKS_CONFIG_PROFILE=sanad MOCK_MCP_URL=http://localhost:8200/mcp \
    uv run python ../evals/run_eval.py --name baseline [--only adversarial] [--gate]
```

## Still to do in Phase 6

- Thresholds with a reason each (p6-baseline), two improvements compared against the baseline (p6-improve), the red-team gate in CI (p6-ci-gate).
- Judge calibration: 20 traces labelled by me, compared with the judges (p6-calibration).
- Gaps: a prompt injection planted in a KB document (it needs a corpus and index rebuild), and cases that need a caller in `it_support`.

## Done when

Gate B: the thresholds are met, and the red-team set passes in CI.
