"""The answer contract and the prompt's coverage of the tools. No workspace needed."""

import tomllib
from pathlib import Path

import pytest
from agent.prompt import SOURCE
from agent.schema import Answer
from pydantic import ValidationError

ROOT = Path(__file__).parents[1]
DOC = {"source": "document", "ref": "fin-duplicate-invoices", "title": "Duplicate Invoice Handling"}


def test_cited_answer_can_be_high_confidence():
    a = Answer(answer="Yes.", citations=[DOC], confidence="high", next_action="draft_credit_note")
    assert a.citations[0].ref == "fin-duplicate-invoices"


def test_uncited_answer_must_be_low_confidence():
    with pytest.raises(ValidationError, match="without citations"):
        Answer(answer="Probably a batch glitch.", citations=[], confidence="high", next_action="none")
    Answer(answer="The tools don't say.", citations=[], confidence="low", next_action="none")


def test_next_action_is_a_closed_list():
    with pytest.raises(ValidationError):
        Answer(answer="Done.", citations=[DOC], confidence="high", next_action="issue_refund")


def test_prompt_names_every_bound_tool():
    tools = tomllib.loads((ROOT / "agent.toml").read_text())["tools"]
    prompt = SOURCE.read_text()
    for tool in tools:
        assert tool["id"] in prompt, tool["id"]
