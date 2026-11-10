"""Phase 7: refresh the three small tables behind the success-metrics dashboard.

    cd agent && DATABRICKS_CONFIG_PROFILE=sanad uv run python ../monitoring/refresh_metrics.py

Frugal by design: the dashboard reads only these tables (tens of rows), never the system tables,
so opening it scans almost nothing and repeat views can come from the warehouse's result cache.
Run this after an evaluation or before a demo (about a minute of warehouse time); there is no
schedule. The tables hold counts only: no e-mails, IP addresses or question text.
Written by Claude at my request; I must be able to defend it.
"""

import datetime as dt
import tomllib
from collections import defaultdict
from pathlib import Path

import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem, StatementState

AGENT = Path(__file__).resolve().parents[1] / "agent"
APP = "agent-bricks-sanad-cs"
EVALS = "/Shared/sanad-evals"
WAREHOUSE = "Serverless Starter Warehouse"  # found by name, as databricks.yml does
# The baseline run counted tokens the old, inflated way (236,707 per question); re-score run
# 69cdd8a2 measured the same traces correctly (9,135). Without this the trend shows a fake drop.
BASELINE, RESCORE = "5fce068b613e48578597f63fe0f8d142", "69cdd8a278c140bc8c982bee7cab7f41"

EVAL_SCORES = """
CREATE OR REPLACE TABLE sanad.ops.eval_scores
COMMENT 'One row per full evaluation run (monitoring/refresh_metrics.py)' AS
WITH m AS (
  SELECT r.run_id, r.run_name, r.start_time, x.metric_name AS metric, x.latest_value AS value
  FROM system.mlflow.runs_latest r LATERAL VIEW explode(r.aggregated_metrics) e AS x
  WHERE r.experiment_id = :evals AND r.delete_time IS NULL AND r.status = 'FINISHED'
)
SELECT m.run_id, any_value(m.run_name) AS run_name, any_value(m.start_time) AS started,
  max(CASE WHEN m.metric = 'correctness/mean' THEN m.value END) AS correctness,
  max(CASE WHEN m.metric = 'grounded/mean' THEN m.value END) AS grounded,
  max(CASE WHEN m.metric = 'safe/mean' THEN m.value END) AS safe,
  max(CASE WHEN m.metric = 'follows_guidelines/mean' THEN m.value END) AS follows_guidelines,
  max(CASE WHEN m.metric = 'tool_choice/mean' THEN m.value END) AS tool_choice,
  max(CASE WHEN m.metric = 'no_pii/mean' THEN m.value END) AS no_pii,
  max(CASE WHEN m.metric = 'writes_need_approval/mean' THEN m.value END) AS writes_need_approval,
  max(CASE WHEN m.metric = 'no_false_claims/mean' THEN m.value END) AS no_false_claims,
  max(CASE WHEN m.metric = 'latency_s/p90' THEN m.value END) AS latency_p90_s,
  coalesce(max(t.value), max(CASE WHEN m.metric = 'billed_tokens/mean' THEN m.value END))
    AS tokens_per_question
FROM m LEFT JOIN m t
  ON m.run_id = :baseline AND t.run_id = :rescore AND t.metric = 'billed_tokens/mean'
WHERE m.run_name NOT LIKE 'smoke%'
GROUP BY m.run_id
HAVING correctness IS NOT NULL  -- full runs only: re-score runs carry cost metrics alone
"""

GATEWAY_DAILY = """
CREATE OR REPLACE TABLE sanad.ops.gateway_daily
COMMENT 'Model gateway requests per day, production (the app) vs testing (monitoring/refresh_metrics.py)' AS
SELECT date(event_time) AS day,
  CASE WHEN requester = :app_sp THEN 'production' ELSE 'testing' END AS source,
  count(*) AS requests, sum(total_tokens) AS tokens,
  percentile_approx(latency_ms, 0.9) / 1000.0 AS p90_latency_s,
  avg(CASE WHEN status_code >= 400 THEN 1.0 ELSE 0.0 END) AS error_rate
FROM system.ai_gateway.usage
WHERE workspace_id = :ws AND event_time >= date_sub(current_date(), 30)
GROUP BY ALL
"""


def run(w: WorkspaceClient, warehouse: str, sql: str, **params: str) -> None:
    result = w.statement_execution.execute_statement(
        statement=sql,
        warehouse_id=warehouse,
        wait_timeout="50s",
        parameters=[StatementParameterListItem(name=k, value=v) for k, v in params.items()],
    )
    if result.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"{sql.split('(')[0].strip()}: {result.status}")


def app_feedback_rows() -> list[tuple]:
    """Per day and source: questions, conversations, thumbs up/down and how many people gave them.

    From the app experiment's trace records (no spans needed, no warehouse). Production = traces
    the deployed app wrote (its code runs from /app/); the rest came from agentbricks dev.
    """
    name = tomllib.loads((AGENT / "agent.toml").read_text())["tracing"]["experiment_name"]
    experiment = mlflow.get_experiment_by_name(name)
    traces = mlflow.search_traces(
        locations=[experiment.experiment_id], include_spans=False, return_type="list"
    )
    days: dict = defaultdict(lambda: {"q": 0, "s": set(), "up": 0, "down": 0, "who": set()})
    for t in traces:
        source = t.info.trace_metadata.get("mlflow.source.name", "")
        day_utc = dt.datetime.fromtimestamp(t.info.request_time / 1000, dt.UTC).date().isoformat()
        key = (day_utc, "production" if source.startswith("/app/") else "dev")
        day = days[key]
        day["q"] += 1
        day["s"].add(t.info.trace_metadata.get("mlflow.trace.session"))
        for a in t.info.assessments:
            if a.name == "user_thumbs":
                day["up" if a.value else "down"] += 1
                day["who"].add(a.source.source_id)
    return [
        (day, src, d["q"], len(d["s"]), d["up"], d["down"], len(d["who"]))
        for (day, src), d in days.items()
    ]


def main() -> None:
    w = WorkspaceClient()
    mlflow.set_tracking_uri("databricks")
    warehouse = next(x.id for x in w.warehouses.list() if x.name == WAREHOUSE)
    run(w, warehouse, EVAL_SCORES, evals=mlflow.get_experiment_by_name(EVALS).experiment_id,
        baseline=BASELINE, rescore=RESCORE)  # fmt: skip
    run(w, warehouse, GATEWAY_DAILY, app_sp=w.apps.get(APP).service_principal_client_id,
        ws=str(w.get_workspace_id()))  # fmt: skip
    # Only dates, counts and two fixed labels go into the SQL text, so literals are safe here.
    values = ", ".join(
        f"(date'{day}', '{src}', {q}, {s}, {up}, {down}, {who})"
        for day, src, q, s, up, down, who in app_feedback_rows()
    )
    run(w, warehouse, f"""
CREATE OR REPLACE TABLE sanad.ops.app_feedback
COMMENT 'Questions, conversations and thumbs per day from the app trace records (monitoring/refresh_metrics.py)' AS
SELECT * FROM VALUES {values}
  AS v(day, source, questions, conversations, thumbs_up, thumbs_down, feedback_givers)
""")  # fmt: skip
    print("refreshed sanad.ops.eval_scores, gateway_daily, app_feedback")


if __name__ == "__main__":
    main()
