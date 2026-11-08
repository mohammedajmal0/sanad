"""Gate A: ask the deployed Customer Service agent about Al-Faris, then check that
1. it found the seeded duplicate (both invoice ids cited),
2. it cites the policy for duplicate invoices, and
3. its MLflow trace has a span for every tool call it made.

    databricks apps start agent-bricks-sanad-cs --profile sanad
    cd agent && DATABRICKS_CONFIG_PROFILE=sanad uv run python ../evals/gate_a.py [--local]
    databricks apps stop agent-bricks-sanad-cs --profile sanad

--local asks the agent at localhost:8000 instead (agent/README: run it with the MLFLOW_* env
below). The deployed app can't upload trace spans on this workspace: its exporter fails to
reach the cloud storage host (2026-11-08), so only the trace summary arrives and check 3 can
only pass locally.

"The refund policy" in Gate A is read as fin-duplicate-invoices: the procedure that says when
a duplicate is cancelled, credited or refunded (Claude's reading, at my request).
"""

import sys
import time
import uuid

APP = "agent-bricks-sanad-cs"
EXPERIMENT = "/Shared/agentbricks_traces/sanad-cs-bevrqu"  # agent/agent.toml [tracing]
QUESTION = "Why was Al-Faris Trading invoiced twice in September?"
MUST_CITE = {"INV-027711", "INV-050001", "fin-duplicate-invoices"}


def gate_failures(answer: dict | None, tool_calls: list[str], span_names: set[str]) -> list[str]:
    """Empty list = Gate A passes."""
    if not answer:
        return ["no structured Answer in the final message"]
    failures = []
    missing = MUST_CITE - {c["ref"] for c in answer["citations"]}
    if missing:
        failures.append(f"not cited: {sorted(missing)}")
    if not tool_calls:
        failures.append("the agent called no tools")
    untraced = [t for t in tool_calls if t not in span_names]
    if untraced:
        failures.append(f"tool calls with no trace span: {untraced}")
    return failures


def main() -> int:
    import requests
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.errors import NotFound

    w = WorkspaceClient()
    local = "--local" in sys.argv
    url = "http://localhost:8000" if local else w.apps.get(APP).url
    headers = {} if local else w.config.authenticate()
    session, started_ms = str(uuid.uuid4()), int(time.time() * 1000)
    body = {
        "id": str(uuid.uuid4()),
        "session_id": session,
        "input": {"messages": [{"role": "user", "content": QUESTION}]},
    }
    for _ in range(6):  # a just-started app reinstalls its packages first and answers 502
        resp = requests.post(f"{url}/api/invocations", json=body, headers=headers, timeout=300)
        if resp.status_code != 502:
            break
        time.sleep(10)
    resp.raise_for_status()
    messages = resp.json()["output"]["output"]
    tool_calls = [t["name"] for m in messages for t in (m.get("tool_calls") or [])]
    answer = messages[-1].get("additional_kwargs", {}).get("answer")

    # MLflow 3.18's search_traces/get_trace return nothing for these traces (2026-11-08), so read
    # them over REST. The stored session id is namespaced per user, so match on time and question.
    exp_id = w.experiments.get_by_name(EXPERIMENT).experiment.experiment_id
    span_names: set[str] = set()
    for _ in range(12):  # traces are exported asynchronously; wait up to a minute
        listed = w.api_client.do(
            "GET", "/api/2.0/mlflow/traces", query={"experiment_ids": exp_id, "max_results": 20}
        )
        mine = [
            t
            for t in listed.get("traces", [])
            if t["timestamp_ms"] >= started_ms
            and {"key": "mlflow.trace.request", "value": QUESTION} in t["request_metadata"]
        ]
        if mine:
            trace_id = mine[0]["request_id"]
            try:  # the trace is listed before its spans are uploaded
                spans = w.api_client.do(
                    "GET", "/api/2.0/mlflow/get-trace-artifact", query={"request_id": trace_id}
                )["spans"]
            except NotFound:
                spans = None
            if spans:
                span_names = {sp["name"] for sp in spans}
                print("trace:", trace_id, f"({len(spans)} spans)")
                break
        time.sleep(5)

    print("tool calls:", tool_calls)
    print("cited:", [c["ref"] for c in answer["citations"]] if answer else None)
    failures = gate_failures(answer, tool_calls, span_names)
    print("GATE A:", "PASS" if not failures else f"FAIL {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
