# retrieval

Parsing, chunking, index build and retrieval evaluation over the policy and KB documents.

**Phase:** 3

## What goes here

- `ai_parse_document` into an elements table.
- Two chunking strategies (fixed-size and section-aware) into `ai.chunks`. Metadata: document type, department, effective date, language.
- A Delta Sync AI Search index with managed embeddings, and hybrid queries with reranking.
- Permission-aware retrieval: AI Search has no row or column security, so pass the user's department or region as a filter.

## You write

- TODO(human): 40 question-and-expected-passage pairs, the ground truth for retrieval evaluation.

## Done when

One chunking strategy beats the other on recall@5, recorded with numbers in ADR 0002.
