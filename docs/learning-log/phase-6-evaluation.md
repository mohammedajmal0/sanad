# Phase 6: Evaluation: MLflow 3 judges, scorers, red team

**Goal:** measure quality, cost and safety before shipping.

**Done when:** an MLflow 3 evaluation run scores quality, groundedness, tool-call correctness and cost, and a red-team set runs in CI as a pass/fail gate. **Gate G2:** the evaluation gate passes in CI.

## Concepts to learn

- **An evaluation is an exam for the agent.**
  - Cases hold inputs plus expectations.
  - `predict_fn` runs the agent and leaves one trace per case.
  - Scorers grade each trace, and a run aggregates the grades.
- **Code checks against LLM judges:**
  - Code is exact, cheap and repeatable: was the id cited, did a write run, any phone number in the answer.
  - Judges handle meaning: is it correct, is it grounded, does it follow a rule.
  - Judges can be wrong too, so they need calibrating against a person's labels.
- **A judge from another model family.** A model grading its own answers tends to like them.
- **A gate turns metrics into a decision:** thresholds, each with a reason, and an exit code that CI can act on.

## Entries

### 2026-11-09: The evaluation harness, and a cost metric that lied

**What we built:**
- **[evals/cases.py](../../evals/cases.py): 34 cases** (19 normal, 6 multi-step, 9 red team).
  - Expectations come from the seeded data and the policy text.
  - The red team covers PII extraction, "I approve in advance", a CFO override, an inflated amount, out-of-scope requests, a prompt leak, an injection pasted in an e-mail, an injection inside a CRM record a tool returns, and memory poisoning.
- **[evals/checks.py](../../evals/checks.py): code checks** for tools, citations, PII, writes and approval, billed tokens, and the gate. Tested in [tests/test_eval_checks.py](../../tests/test_eval_checks.py).
- **[evals/run_eval.py](../../evals/run_eval.py)** runs the agent in-process with `mlflow.genai.evaluate`.
  - 6 code scorers and 4 judges: `correctness`, `grounded` (against the tool outputs in the trace), `follows_guidelines` and `safe`.
  - The judge is `system.ai.qwen35-122b-a10b`.
  - `--from-run` re-scores an existing run's traces without calling the agent again.
- **Smoke run (3 cases):** every scorer produced a score, and all 3 cases passed.

These were written by Claude at my request; I must be able to defend them: every case and its expectations, the scorers, the judge choice, and the PII pattern.

**Key concepts:**
- **Measure the measurement.** The cost scorer first reported a mean of 218,617 tokens per question and a maximum of 570,645. The trace showed why:
  - every model call is traced twice, as sibling spans: by the model API client ("openai" format) and by LangChain;
  - while streaming, LangChain adds up the usage that every chunk repeats, so one 3,399-token answer call showed 367,092;
  - the trace total then adds both.
  Counting only the API client's spans gives a **mean of 8,759 and a maximum of 17,253**, and the maximum matches a hand count. Phase 4's "296k-token formatting call" was this same artifact.
- **Tell the kinds of span apart by attribute, not by shape.** I first assumed the LangChain span wrapped the API call and wrote a test for that shape. The test passed and the metric didn't change, because the spans are siblings. `mlflow.message.format` is the reliable signal.
- **Return `None` from a scorer when it doesn't apply.** Correctness only runs where a case has expected facts; scoring the others as passes would inflate the mean.
- **Two kinds of injection need no index change:** text the user pastes, and data a tool returns. Records from enterprise systems are untrusted input.

**Mistakes:**
- **A test that encoded a guess.** Claude's first `billed_tokens` assumed the inflated span was the parent of the real one. The test was built on that assumption and passed; the re-score showed no change. It was rewritten from the real trace attributes.
- **A misdiagnosis since Phase 4.** "Find the token anomaly" had been on the list since Phase 4. It was never a cost problem, only a counting one.

**Interview questions:**
1. Your agent's token count per request looks 25 times too high. How do you find out whether the cost or the measurement is wrong?
2. Which checks in an agent evaluation would you write as code, and which need an LLM judge? Give an example of each.
3. Why should the judge model differ from the agent's model, and how do you know the judge itself is right?
