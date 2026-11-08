# 0003: Retrieve `ai_prep_search` chunks, which keep our short documents whole

- **Status:** Accepted
- **Date:** 2026-11-08
- **Phase:** 3

## Context

The Phase 4 agent answers policy and how-to questions from 30 documents (10 policies, 20 knowledge-base articles, about 140 words each) through the AI Search index `sanad.ai.chunks_index`. Where the documents are cut decides which passage the agent finds and how much text it has to read.

`ai.chunks` holds three cuts side by side, told apart by a `strategy` column, so one index and one eval compare them fairly ([retrieval/README.md](../../retrieval/README.md)). The eval has 40 questions: 30 asked in different words than the document uses, and 10 that hinge on an exact code such as `INC-2026-1019`. It runs a hybrid search, takes the top 5 and allows all departments. A hit is a card from the right document that holds the whole verbatim answer phrase, so the same rule works for every cut.

Constraints:
- Free Edition gives one AI Search endpoint and no reranker ("Reranking is not yet enabled for this workspace"), so the cut must do the work a reranker would otherwise repair.
- `ai_prep_search` is Beta (Databricks docs, checked 2026-11-08), and [ADR 0001](0001-isolate-beta-features.md) says Beta features stay behind a thin layer.

## Options

1. **`whole`: `ai_prep_search`**, Databricks' managed chunker. It cuts at natural boundaries, but our documents are smaller than one of its pieces, so each one stays whole (30 cards). Won; see Decision.
2. **`section`: one card per heading**, hand-written from the parser's `section_header` elements (103 cards, about 38 words each). Missed 3 of 40:
   - q03, crowding: the call script's 4 section cards filled 4 of the 5 slots and pushed the policy out.
   - q04: the credit-limits section beat the credit-hold section.
   - q14, a vocabulary gap: "ChatGPT" in the question, "external AI tools" in the policy.
3. **`fixed`: 60-word windows every 50 words**, blind to headings (99 cards). Missed 3 of 40 (q03, q07, q14), and it cuts rules in half. In `fin-credit-notes`, the SAR 5,000 rule lands in a window without its "Approval limits" heading.
4. **`section` with at most 2 cards per document in the top 5.** Aimed at q03's crowding. It was never measured, so there are no numbers to choose it on. Trying it would mean a `search.py` change and a re-run.

## Decision

Option 1. Measured on 2026-11-08 with `python -m retrieval.evaluate`. Two runs gave identical results.

| Strategy | recall@5 | MRR | MRR, 10 code questions | words@5 |
|---|---|---|---|---|
| `whole` | **1.00** | **0.93** | **1.00** | 702 |
| `section` | 0.93 | 0.82 | 0.80 | **203** |
| `fixed` | 0.93 | 0.81 | 0.87 | 267 |

- **Head to head.** `whole` put the right card higher than `section` on 9 questions and lower on 1 (q09: rank 2 against rank 1), with 30 ties. Against `fixed` it was higher on 11 and lower on 1 (q09 again), with 28 ties.
- **Could it be chance?** recall@5 alone can't tell: only 3 questions differ, all in favour of `whole`, and a sign test gives p = 0.25. The ranks are stronger evidence: 9 of 10 against `section` (p = 0.02) and 11 of 12 against `fixed` (p = 0.006).
- **The price.** The agent reads 702 words from the top 5, about 1,000 tokens per question and 3.5 times `section`. At our scale that cost is small.

Restated by Claude at my request: our documents are short, about one page each. Cutting a one-page document into four cards made it easier for the search to grab the wrong card, or to fill all five slots with one document. Keeping each document whole found every answer, almost always in first place, and these documents fit easily in what an LLM can read. The cost is that the agent reads five pages instead of five paragraphs, around a thousand tokens per question. The cutter is Databricks' own, so a long document added later is cut at sensible places without new code from us. Because that cutter is Beta, it is used in exactly one place, and we have a measured fallback.

## Consequences

- The Phase 4 retrieval tool searches with `strategy = "whole"`, and `search()` in [search.py](../../retrieval/search.py) now defaults to it.
- No crowding: with one card per document, the top 5 are always 5 different documents, and each card can be cited as a document.
- The agent also reads the parts of each document that don't answer the question. Nothing measures yet whether that noise hurts the answer; the Phase 5 groundedness eval must check it.
- **The Beta dependency is kept thin (ADR 0001).** `ai_prep_search` appears in one CTE of [chunks.sql](../../retrieval/chunks.sql). The index, `search.py` and the agent only read columns of `ai.chunks`. If the function changes or disappears:
  - For short documents, the full parsed text gives almost the same card. The `words` CTE already builds it; only the header enrichment in `chunk_to_embed` would be lost.
  - For long documents, `section` is the measured fallback.
- Its chunk size can't be tuned: the docs list only the `version` and `schema` options.
- `section` and `fixed` stay in `ai.chunks` and the index (232 rows, no measurable cost), so the eval can be re-run whenever the corpus changes.
- Revisit when:
  - documents grow past one `ai_prep_search` piece, because then `whole` stops being whole and its cuts need the same eval;
  - the eval grows, because at 40 questions one question is 2.5 points;
  - the workspace gets a reranker, which targets exactly the `section` misses (q03, q04);
  - reading tokens becomes a real budget line.
