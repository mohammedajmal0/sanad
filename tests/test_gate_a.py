"""Gate A's pass/fail rule, without calling the agent."""

from evals.gate_a import gate_failures

CITED = {
    "citations": [
        {"source": "record", "ref": "INV-027711", "title": "get_invoices"},
        {"source": "record", "ref": "INV-050001", "title": "get_invoices"},
        {"source": "document", "ref": "fin-duplicate-invoices", "title": "Duplicate Invoices"},
    ]
}
CALLS = ["sanad__ai__get_customer_summary", "sanad__ai__get_invoices"]


def test_passes_when_cited_and_traced():
    assert gate_failures(CITED, CALLS, set(CALLS) | {"invoke"}) == []


def test_fails_when_one_duplicate_is_missing():
    one = {"citations": CITED["citations"][::2]}
    assert gate_failures(one, CALLS, set(CALLS)) == ["not cited: ['INV-050001']"]


def test_fails_when_a_tool_call_has_no_span():
    assert gate_failures(CITED, CALLS, {CALLS[0]}) == [
        "tool calls with no trace span: ['sanad__ai__get_invoices']"
    ]


def test_fails_without_a_structured_answer():
    assert gate_failures(None, CALLS, set(CALLS)) == ["no structured Answer in the final message"]
