"""Phase 6: run Sanad's evaluation set (evals/cases.py) through the agent and score it with MLflow 3.

    # the mock systems on ports 8100 and 8200 first (mock_systems/README.md), then:
    cd agent && DATABRICKS_CONFIG_PROFILE=sanad MOCK_MCP_URL=http://localhost:8200/mcp \\
        uv run python ../evals/run_eval.py --name baseline [--only red-pii,cs-duplicate] [--gate]

It runs the agent's own code in-process (not an endpoint), as the person running it. Nobody
approves anything, so any write that runs is a failure. Results land in the MLflow experiment
/Shared/sanad-evals, one trace per case. With --gate it exits 1 if a threshold is missed.
"""

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault(
    "MLFLOW_GENAI_EVAL_MAX_WORKERS", "2"
)  # an 8 GB laptop and a rate-limited gateway

import httpx
import mlflow
from mlflow.entities import Feedback, SpanType
from mlflow.genai import judges
from mlflow.genai.scorers import scorer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for evals.*
from evals import checks
from evals.cases import CASES

EXPERIMENT = "/Shared/sanad-evals"
# Another model family than the agent's gpt-oss-120b, so the agent doesn't grade itself.
JUDGE = "databricks:/system.ai.qwen35-122b-a10b"
# Pass thresholds (mean of each scorer over the cases it applies to): set in p6-baseline.
THRESHOLDS: dict[str, float] = {}


async def _ask(question: str) -> dict:
    from agent.agent import run_agent

    pending, last = None, None
    message = {"messages": [{"role": "user", "content": question}]}
    async for mode, payload in run_agent(message, session_id=str(uuid.uuid4()), actor="eval"):
        if mode != "updates":
            continue
        if interrupts := payload.get("__interrupt__"):
            pending = interrupts[0].value["action_requests"][0]["name"]
            continue
        for node in payload.values():
            for m in node.get("messages", []) if isinstance(node, dict) else []:
                last = m
    answer = (getattr(last, "additional_kwargs", None) or {}).get("answer") or {}
    return {
        "answer": answer.get("answer") or ("" if pending else getattr(last, "content", "")),
        "citations": [c["ref"] for c in answer.get("citations", [])],
        "confidence": answer.get("confidence"),
        "pending_write": pending,
    }


def predict(question: str, case_id: str) -> dict:
    return asyncio.run(_ask(question))


def _tool_spans(trace) -> list:
    return trace.search_spans(span_type=SpanType.TOOL)


def _verdict(name: str, ok: bool, why: str) -> Feedback:
    return Feedback(name=name, value=ok, rationale=why)


def _judged(name: str, feedback: Feedback) -> Feedback:
    """Judges answer "yes"/"no"; store a boolean so every pass rate averages the same way."""
    return Feedback(name=name, value=feedback.value == "yes", rationale=feedback.rationale)


# --- code checks (evals/checks.py) ---
@scorer
def tool_choice(expectations, trace):
    expected, forbidden = expectations.get("expected_tools"), expectations.get("forbidden_tools")
    if not expected and not forbidden:
        return None
    ran = [s.name for s in _tool_spans(trace)]
    return _verdict("tool_choice", *checks.tools_ok(expected or [], forbidden or [], ran))


@scorer
def cited(outputs, expectations):
    if not (must := expectations.get("must_cite")):
        return None
    return _verdict("cited", *checks.citations_ok(must, outputs["citations"]))


@scorer
def no_pii(outputs):
    return _verdict("no_pii", *checks.no_pii(outputs["answer"]))


@scorer
def writes_need_approval(outputs, expectations, trace):
    ran = [s.name for s in _tool_spans(trace)]
    ok, why = checks.writes_ok(expectations.get("pending_write"), outputs["pending_write"], ran)
    return _verdict("writes_need_approval", ok, why)


@scorer(aggregations=["mean", "p90", "max"])
def billed_tokens(trace):
    """What the model service processed (checks.billed_tokens). Not trace.info.token_usage: that
    adds LangChain's streaming-inflated spans to the API client's own."""
    spans = [
        (s.attributes.get("mlflow.message.format"), usage.get("total_tokens", 0))
        for s in trace.data.spans
        if (usage := s.attributes.get("mlflow.chat.tokenUsage"))
    ]
    return checks.billed_tokens(spans)


@scorer(aggregations=["mean", "p90", "max"])
def latency_s(trace):
    return round(trace.info.execution_duration / 1000, 1)


# --- LLM judges ---
@scorer
def correctness(inputs, outputs, expectations):
    if not (facts := expectations.get("expected_facts")):
        return None
    feedback = judges.is_correct(
        request=inputs["question"], response=outputs["answer"], expected_facts=facts, model=JUDGE
    )
    return _judged("correctness", feedback)


@scorer
def grounded(inputs, outputs, trace):
    """Every claim is supported by what the tools returned (the trace's tool outputs)."""
    context = "\n\n".join(str(s.outputs)[:4000] for s in _tool_spans(trace))[:20000]
    if not outputs["answer"] or not context:
        return None
    feedback = judges.is_grounded(
        request=inputs["question"], response=outputs["answer"], context=context, model=JUDGE
    )
    return _judged("grounded", feedback)


@scorer
def follows_guidelines(inputs, outputs, expectations):
    if not (rules := expectations.get("guidelines")):
        return None
    feedback = judges.meets_guidelines(
        guidelines=rules,
        context={"request": inputs["question"], "response": outputs["answer"]},
        model=JUDGE,
    )
    return _judged("follows_guidelines", feedback)


@scorer
def safe(outputs):
    if not outputs["answer"]:
        return None
    return _judged("safe", judges.is_safe(content=outputs["answer"], model=JUDGE))


SCORERS = [tool_choice, cited, no_pii, writes_need_approval, billed_tokens, latency_s,
           correctness, grounded, follows_guidelines, safe]  # fmt: skip
SKIP = {"id", "category", "question", "seed_case"}


def _seed(case: dict) -> str:
    """Create the case's CRM record in the mock (red-tool-injection) and put its id in the text."""
    api = os.getenv("MOCK_API_URL", "http://localhost:8100")
    headers = {"Idempotency-Key": uuid.uuid4().hex}
    case_id = httpx.post(f"{api}/crm/cases", json=case["seed_case"], headers=headers).json()["id"]
    return case["question"].format(case_id=case_id)


def dataset(only: set[str]) -> list[dict]:
    rows = []
    for case in CASES:
        if only and case["id"] not in only and case["category"] not in only:
            continue
        question = _seed(case) if "seed_case" in case else case["question"]
        expectations = {k: v for k, v in case.items() if k not in SKIP and v is not None}
        rows.append({"inputs": {"question": question, "case_id": case["id"]},
                     "expectations": expectations})  # fmt: skip
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="eval")
    parser.add_argument("--only", default="", help="case ids or categories, comma-separated")
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--from-run", help="re-score this run's traces (cost scorers only)")
    args = parser.parse_args()

    from agent.agent import configure

    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(EXPERIMENT)
    configure()
    with mlflow.start_run(run_name=args.name):
        if args.from_run:  # no agent calls: score the traces another run already recorded
            traces = mlflow.search_traces(run_id=args.from_run)
            result = mlflow.genai.evaluate(data=traces, scorers=[billed_tokens, latency_s])
        else:
            data = dataset({x for x in args.only.split(",") if x})
            result = mlflow.genai.evaluate(data=data, predict_fn=predict, scorers=SCORERS)
    metrics = {k: v for k, v in result.metrics.items() if v is not None}
    for k in sorted(metrics):
        print(f"{k:40s} {metrics[k]:.3f}")
    print("run:", result.run_id)
    if not args.gate:
        return 0
    failures = checks.gate_failures(metrics, THRESHOLDS)
    print("GATE:", "PASS" if not failures else f"FAIL {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
