"""Retrieval eval: the metric maths, the matching rule, and the ground truth itself.
A typo in the ground truth would otherwise look like a retrieval miss."""

import csv
from pathlib import Path

import pytest

from retrieval.evaluate import QUESTIONS, contains, first_hit_rank, summarize

CORPUS = Path(__file__).parents[1] / "retrieval" / "corpus"


def test_recall_and_mrr_can_disagree():
    # A: rank 1 for half the questions, misses the rest. B: rank 5 every time.
    assert summarize([1, None, 1, None]) == pytest.approx((0.5, 0.5))
    assert summarize([5, 5, 5, 5]) == pytest.approx((1.0, 0.2))


def test_match_ignores_case_and_pdf_line_breaks():
    assert contains(
        "Above SAR 5,000: the finance\nmanager.", "above sar 5,000: the finance manager"
    )


def test_hit_needs_the_right_doc_and_the_whole_answer():
    hits = [
        {"doc_id": "other-doc", "chunk_to_retrieve": "the finance manager"},
        {"doc_id": "fin-doc", "chunk_to_retrieve": "... approved by the finance"},  # cut in half
        {"doc_id": "fin-doc", "chunk_to_retrieve": "the finance manager approves"},
    ]
    assert first_hit_rank(hits, "fin-doc", "the finance manager") == 3
    assert first_hit_rank(hits[:2], "fin-doc", "the finance manager") is None


def test_ground_truth_is_true():
    rows = list(csv.DictReader(QUESTIONS.read_text().splitlines()))
    manifest = {
        r["doc_id"] for r in csv.DictReader((CORPUS / "manifest.csv").read_text().splitlines())
    }
    assert len(rows) == 40
    assert len({r["id"] for r in rows}) == 40
    assert {r["doc_id"] for r in rows} == manifest  # every doc covered, no unknown doc
    for r in rows:
        assert r["kind"] in ("meaning", "code"), r["id"]
        assert contains((CORPUS / f"{r['doc_id']}.md").read_text(), r["answer"]), r["id"]
