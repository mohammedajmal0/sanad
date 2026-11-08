# retrieval

Parsing, chunking, index build and retrieval evaluation over the policy and KB documents.

**Phase:** 3

## Run order

1. Build the PDFs: `uv run --with markdown --with plutoprint python retrieval/build_corpus.py`
2. Upload them with the manifest: `databricks fs cp -r --overwrite retrieval/build/docs dbfs:/Volumes/sanad/ai/docs --profile sanad`
3. Run [chunks.sql](chunks.sql) in the SQL editor. It parses each PDF once, cuts every document three ways, and ends with a check that must return 0 rows.
4. `databricks bundle deploy --profile sanad` creates the AI Search endpoint `sanad-search` and the index `sanad.ai.chunks_index` (both in [databricks.yml](../databricks.yml)). The first sync starts by itself.
5. After re-running `chunks.sql`, sync the index: `databricks vector-search-indexes sync-index sanad.ai.chunks_index --profile sanad`
6. Try it: `DATABRICKS_CONFIG_PROFILE=sanad uv run python -m retrieval.search "Who approves a SAR 7,000 credit note?"`

## Tables

| Table | One row per | What's in it |
|---|---|---|
| `ai.parsed_docs` | PDF | Manifest metadata plus the raw `ai_parse_document` result (typed elements: title, section header, text) |
| `ai.chunks` | chunk | `strategy`, `audience`, the metadata columns used as search filters, `chunk_to_embed` (what the search matches) and `chunk_to_retrieve` (what the LLM reads). Change data feed is on for the index. |

The three strategies, measured on 2026-11-08:

| `strategy` | How it cuts | Chunks | Avg words |
|---|---|---|---|
| `whole` | `ai_prep_search`: retrieval-sized pieces at natural boundaries. Our docs are smaller than one piece, so each stays whole. | 30 | 134 |
| `section` | One piece per heading, from the parser's `section_header` elements | 103 | 38 |
| `fixed` | 60-word windows every 50 words, blind to headings | 99 | 52 |

## The index and the search

- **Endpoint `sanad-search`, STANDARD.** Free Edition allows one endpoint. STANDARD applies filters before it searches, so a filtered query still returns k results.
- **Index `sanad.ai.chunks_index`.** Delta Sync, managed embeddings of `chunk_to_embed` with `databricks-gte-large-en`, triggered sync.
- **[search.py](search.py).** Hybrid query (meaning plus exact words), filtered on `strategy` and `audience`. No reranker: Free Edition answers "Reranking is not yet enabled for this workspace".
- **Known weakness.** Exact codes such as `INC-2026-1019` are found when asked alone (hybrid rank 3, meaning-only not in the top 5) but get lost inside a full sentence. The retrieval eval measures how often this happens.
- **Permission-aware retrieval.** AI Search has no row or column security, so every query carries the reader's `audience` filter: `all` (every policy) plus the reader's departments (their KB articles). With no department given, the reader sees policies only. See the [access matrix](../docs/access-matrix.md).

## Evaluation

[eval_questions.csv](eval_questions.csv) holds 40 questions written like an employee would ask them: 30 `meaning` questions and 10 `code` questions that hinge on an exact identifier (`INC-2026-1019`, `CL-2`). Every document is covered. Each row names the right document and a short verbatim **answer** phrase. A retrieved card is a hit when it comes from that document and holds the whole phrase, so the same rule works for every strategy. [tests/test_evaluate.py](../tests/test_evaluate.py) checks that every answer really is in its document.

Run: `DATABRICKS_CONFIG_PROFILE=sanad uv run python -m retrieval.evaluate` (120 queries, about a minute).

Results on 2026-11-08 (hybrid search, no reranker, all departments):

| Strategy | recall@5 | MRR | words@5 | Misses |
|---|---|---|---|---|
| `whole` | 1.00 | 0.93 | 702 | none |
| `section` | 0.93 | 0.82 | 203 | q03, q04, q14 |
| `fixed` | 0.93 | 0.81 | 267 | q03, q07, q14 |

words@5 is how many words the LLM would read from the top 5: the cost side. With 40 questions, one question is 2.5 points of recall, so `section` and `fixed` are a tie.

## Done when

One chunking strategy beats the others on recall@5, recorded with numbers in ADR 0003.
