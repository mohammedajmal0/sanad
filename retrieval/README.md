# retrieval

Parsing, chunking, index build and retrieval evaluation over the policy and KB documents.

**Phase:** 3

## Run order

1. Build the PDFs: `uv run --with markdown --with plutoprint python retrieval/build_corpus.py`
2. Upload them with the manifest: `databricks fs cp -r --overwrite retrieval/build/docs dbfs:/Volumes/sanad/ai/docs --profile sanad`
3. Run [chunks.sql](chunks.sql) in the SQL editor. It parses each PDF once, cuts every document three ways, and ends with a check that must return 0 rows.

## Tables

| Table | One row per | What's in it |
|---|---|---|
| `ai.parsed_docs` | PDF | Manifest metadata plus the raw `ai_parse_document` result (typed elements: title, section header, text) |
| `ai.chunks` | chunk | `strategy`, the metadata columns used as search filters, `chunk_to_embed` (what the search matches) and `chunk_to_retrieve` (what the LLM reads). Change data feed is on for the index. |

The three strategies, measured on 2026-11-08:

| `strategy` | How it cuts | Chunks | Avg words |
|---|---|---|---|
| `whole` | `ai_prep_search`: retrieval-sized pieces at natural boundaries. Our docs are smaller than one piece, so each stays whole. | 30 | 134 |
| `section` | One piece per heading, from the parser's `section_header` elements | 103 | 38 |
| `fixed` | 60-word windows every 50 words, blind to headings | 99 | 52 |

## Still to come

- A Delta Sync AI Search index with managed embeddings on `ai.chunks`, and hybrid queries with reranking.
- Permission-aware retrieval: AI Search has no row or column security, so pass the user's department or region as a filter.
- 40 question-and-expected-passage pairs, the ground truth for retrieval evaluation.

## Done when

One chunking strategy beats the others on recall@5, recorded with numbers in ADR 0003.
