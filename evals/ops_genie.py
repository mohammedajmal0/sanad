"""Ops Analytics check: ask the Genie agent the pitch question, then check that
1. it names Jeddah (16.2% late in Q3 2026, under 2% everywhere else),
2. it says why: Red Sea Cargo (381 of 642 Jeddah deliveries late), and
3. its SQL doesn't average the per-row late_rate (a region's rate is SUM(late) / SUM(delivered)).

    DATABRICKS_CONFIG_PROFILE=sanad uv run python evals/ops_genie.py

The facts come from the seeded data (seed 42), checked with SQL on 2026-11-09. The question is
deliberately not one of the space's example SQLs, so a pass shows Genie generalizes.
"""

import re
import sys

TITLE = "Sanad Ops Analytics"  # databricks.yml; dev mode prefixes it with "[dev <user>] "
QUESTION = "Which region had the most late deliveries last quarter, and why?"
MUST_MENTION = ("Jeddah", "Red Sea Cargo")
AVERAGED_RATE = re.compile(r"avg\s*\(\s*[\w.`]*late_rate", re.IGNORECASE)


def genie_failures(answer: str, sql: list[str]) -> list[str]:
    """Empty list = the check passes. `answer` is Genie's text plus its result rows."""
    failures = [f"doesn't mention {n}" for n in MUST_MENTION if n.lower() not in answer.lower()]
    if not sql:
        failures.append("Genie wrote no SQL")
    if any(AVERAGED_RATE.search(q) for q in sql):
        failures.append("averages late_rate instead of SUM(late) / SUM(delivered)")
    return failures


def main() -> int:
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    space = next((s for s in w.genie.list_spaces().spaces if s.title.endswith(TITLE)), None)
    if space is None:
        print(f"No Genie space titled '{TITLE}': run databricks bundle deploy first")
        return 1
    msg = w.genie.start_conversation_and_wait(space.space_id, QUESTION)
    parts, sql = [], []
    for a in msg.attachments or []:
        if a.text:
            parts.append(a.text.content)
        if a.query:
            sql.append(a.query.query)
            res = w.genie.get_message_attachment_query_result(
                space.space_id, msg.conversation_id, msg.message_id, a.attachment_id
            ).statement_response.result
            parts += [" | ".join(map(str, row)) for row in (res and res.data_array) or []]
    answer = "\n".join(parts)
    print(f"Q: {QUESTION}\n\nSQL:\n" + "\n---\n".join(sql) + f"\n\nAnswer and rows:\n{answer}\n")
    failures = genie_failures(answer, sql)
    print("PASS" if not failures else "FAIL: " + "; ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
