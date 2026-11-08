"""Search the policy and KB index: hybrid (meaning plus exact words), filtered.

Smoke test against the live index (the profile comes from the environment, never from code):
    DATABRICKS_CONFIG_PROFILE=sanad uv run python -m retrieval.search "Who approves a SAR 7,000 credit note?"
    DATABRICKS_CONFIG_PROFILE=sanad uv run python -m retrieval.search "How do I issue a credit note?" it
The words after the question are the reader's departments (default: all of them).
"""

import json
import sys

from databricks.sdk import WorkspaceClient

INDEX = "sanad.ai.chunks_index"  # declared in databricks.yml
STRATEGIES = ("whole", "section", "fixed")  # see retrieval/chunks.sql
DEPARTMENTS = ("finance", "logistics", "customer_service", "it")
COLUMNS = ["chunk_id", "doc_id", "title", "audience", "chunk_to_retrieve"]


def build_filters(strategy: str, audiences: tuple[str, ...] = ()) -> dict:
    """AI Search has no row security, so every query carries the reader's audience filter.
    Fails closed: with no departments given, the reader sees policies (audience 'all') only."""
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}, expected one of {STRATEGIES}")
    return {"strategy": strategy, "audience": ["all", *audiences]}


def search(
    question: str,
    strategy: str = "whole",  # ADR 0003
    audiences: tuple[str, ...] = (),
    k: int = 5,
    w: WorkspaceClient | None = None,
) -> list[dict]:
    """Top k chunks for the question, best first, as dicts of COLUMNS plus 'score'."""
    w = w or WorkspaceClient()
    # shortcut: no reranker. Free Edition answers "Reranking is not yet enabled for this
    # workspace" (2026-11-08). On a workspace that has it, pass reranker=RerankerConfig(
    # model="databricks_reranker", parameters=...(columns_to_rerank=["title", "chunk_to_retrieve"])).
    resp = w.vector_search_indexes.query_index(
        index_name=INDEX,
        columns=COLUMNS,
        query_text=question,
        query_type="HYBRID",
        filters_json=json.dumps(build_filters(strategy, audiences)),
        num_results=k,
    )
    names = [c.name for c in resp.manifest.columns]
    return [dict(zip(names, row)) for row in resp.result.data_array or []]


if __name__ == "__main__":
    question, audiences = sys.argv[1], tuple(sys.argv[2:]) or DEPARTMENTS
    for strategy in STRATEGIES:
        print(f"\n== {strategy}  (audiences: all + {', '.join(audiences)})")
        for hit in search(question, strategy, audiences):
            text = hit["chunk_to_retrieve"].replace("\n", " ")[:90]
            print(f"  {float(hit['score']):.3f}  {hit['chunk_id']:<40} {text}")
