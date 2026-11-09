"""The answer contract and the prompt's coverage of the tools. No workspace needed."""

import json
import tomllib
from pathlib import Path

import pytest
from agent.answer import specialist_citations
from agent.prompt import PROMPTS
from agent.schema import Answer
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import ValidationError

ROOT = Path(__file__).parents[1]
DOC = {"source": "document", "ref": "fin-duplicate-invoices", "title": "Duplicate Invoice Handling"}


def test_cited_answer_can_be_high_confidence():
    a = Answer(answer="Yes.", citations=[DOC], confidence="high", next_action="draft_credit_note")
    assert a.citations[0].ref == "fin-duplicate-invoices"


def test_uncited_answer_must_be_low_confidence():
    with pytest.raises(ValidationError, match="without citations"):
        Answer(
            answer="Probably a batch glitch.", citations=[], confidence="high", next_action="none"
        )
    Answer(answer="The tools don't say.", citations=[], confidence="low", next_action="none")


def test_next_action_is_a_closed_list():
    with pytest.raises(ValidationError):
        Answer(answer="Done.", citations=[DOC], confidence="high", next_action="issue_refund")


def test_a_genie_answer_is_cited_as_a_query():
    link = {"source": "query", "ref": "https://host/genie/spaces/x", "title": "Late rate"}
    assert Answer(answer="Jeddah.", citations=[link], confidence="high", next_action="none")


def test_specialist_citations_come_from_this_turn_only():
    def specialist(ref):
        return ToolMessage(json.dumps({"citations": [{**DOC, "ref": ref}]}), tool_call_id="t")

    messages = [
        HumanMessage("earlier turn"),
        specialist("old-policy"),
        HumanMessage("this turn"),
        ToolMessage('{"rows": []}', tool_call_id="g"),  # e.g. Genie: not an Answer
        specialist("fin-duplicate-invoices"),
    ]
    assert [c.ref for c in specialist_citations(messages)] == ["fin-duplicate-invoices"]


def test_each_prompt_names_the_tools_it_owns():
    # UC function tools belong to the Customer Service agent; the Genie agent and the
    # customer_service specialist are the supervisor's tools.
    prompt = {p.stem: p.read_text() for p in PROMPTS.glob("*.md")}
    assert "customer_service" in prompt["supervisor"]
    for tool in tomllib.loads((ROOT / "agent.toml").read_text())["tools"]:
        owner = "supervisor" if tool["source"]["kind"] == "genie_agent" else "customer_service"
        assert tool["id"] in prompt[owner], (owner, tool["id"])
