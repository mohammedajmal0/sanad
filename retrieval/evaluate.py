"""Retrieval eval: for each question in eval_questions.csv, where does the right passage land
in the top 5, per chunking strategy? Prints recall@5, MRR and words@5, then every rank.

    DATABRICKS_CONFIG_PROFILE=sanad uv run python -m retrieval.evaluate

A retrieved card is a hit when it comes from the question's doc AND holds the whole answer
phrase. The rule is the same for every strategy, so the comparison is fair.
"""

import csv
import re
from pathlib import Path

from retrieval.search import DEPARTMENTS, STRATEGIES, search

K = 5
QUESTIONS = Path(__file__).parent / "eval_questions.csv"


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def contains(text: str, answer: str) -> bool:
    """Ignores case and all whitespace, because PDF line breaks land anywhere."""
    return squash(answer) in squash(text)


def first_hit_rank(hits: list[dict], doc_id: str, answer: str) -> int | None:
    """1-based rank of the first card from the right doc that holds the whole answer."""
    for rank, hit in enumerate(hits, start=1):
        if hit["doc_id"] == doc_id and contains(hit["chunk_to_retrieve"], answer):
            return rank
    return None


def summarize(ranks: list[int | None]) -> tuple[float, float]:
    """recall@K: share of questions with a hit in the top K. MRR: average of 1/rank, 0 if missed."""
    recall = sum(r is not None for r in ranks) / len(ranks)
    mrr = sum(1 / r for r in ranks if r is not None) / len(ranks)
    return recall, mrr


def main() -> None:
    questions = list(csv.DictReader(QUESTIONS.read_text().splitlines()))
    ranks, words = {}, {}  # (strategy, question id) -> rank, and words the LLM would read
    for strategy in STRATEGIES:
        for q in questions:
            # every department: this measures search quality, not permissions
            hits = search(q["question"], strategy, DEPARTMENTS, k=K)
            ranks[strategy, q["id"]] = first_hit_rank(hits, q["doc_id"], q["answer"])
            words[strategy, q["id"]] = sum(len(h["chunk_to_retrieve"].split()) for h in hits)

    print(f"| Strategy | Questions | n | recall@{K} | MRR | words@{K} |\n|---|---|---|---|---|---|")
    for strategy in STRATEGIES:
        for kind in ("all", "meaning", "code"):
            ids = [q["id"] for q in questions if kind in ("all", q["kind"])]
            recall, mrr = summarize([ranks[strategy, i] for i in ids])
            avg_words = sum(words[strategy, i] for i in ids) / len(ids)
            print(
                f"| {strategy} | {kind} | {len(ids)} | {recall:.2f} | {mrr:.2f} | {avg_words:.0f} |"
            )

    print("\nRank of the right card per question (- = not in the top 5):")
    print("id   kind     " + "".join(f"{s:>9}" for s in STRATEGIES))
    for q in questions:
        cells = "".join(f"{ranks[s, q['id']] or '-':>9}" for s in STRATEGIES)
        print(f"{q['id']}  {q['kind']:<8}{cells}  {q['question'][:60]}")


if __name__ == "__main__":
    main()
