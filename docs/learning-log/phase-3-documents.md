# Phase 3: Documents for AI: parse, chunk, AI Search

**Goal:** prepare enterprise documents for retrieval.

**Done when:** parsed documents are chunked into a hybrid AI Search index with metadata filters, and test questions retrieve the right chunk.

## Read first

- [ai_parse_document](https://learn.microsoft.com/azure/databricks/sql/language-manual/functions/ai_parse_document)
- [Databricks AI Search](https://docs.databricks.com/gcp/en/ai-search/ai-search)

## Concepts to learn

- Parsing: a PDF becomes typed elements (title, section header, text, table), not one blob of text.
- Chunking: cutting documents into search-sized pieces. Fixed-size versus semantic (cut at headings), and why where you cut changes the answers.
- The two faces of a chunk: the text you embed (with title and headings) versus the text you hand to the LLM.
- Delta Sync index with managed embeddings: the index follows a Delta table through its change data feed.
- Hybrid search (keywords plus meaning) and reranking.
- AI Search has no row or column security, so permission-aware retrieval means passing the user's department or region as a filter.
- Retrieval metrics: recall@5 and MRR.

## Entries

### 2026-11-07: Policy and KB corpus as PDFs in a volume

**What we built:** 30 documents in [retrieval/corpus/](../../retrieval/corpus/): 10 policies and 20 knowledge-base articles across finance, logistics, customer service and IT, plus [manifest.csv](../../retrieval/corpus/manifest.csv) with each document's type, department, effective date and language. [build_corpus.py](../../retrieval/build_corpus.py) renders them to PDFs in `retrieval/build/docs/` (gitignored, generated), and they are uploaded with the manifest to the volume `sanad.ai.docs`. The corpus text was written by Claude at my request; I must be able to defend it.

**Key concepts:**
- PDFs, not Markdown: Najm's documents really arrive as PDFs, so parsing is part of the problem and the pipeline must handle it.
- Metadata lives in a manifest next to the files, not inside the text. It gets joined onto every chunk later as filter columns (department, type, date).
- The documents match the seeded data: the VPN 6.2 incident, the Jeddah port congestion and the duplicate-invoice procedure explain what the gold tables show, so an agent can connect a number to a policy.
- `uv run --with markdown --with plutoprint` borrows the PDF libraries for one run, so they never become project dependencies.

**Mistakes:**
- None recorded.

**Interview questions:**
1. Why keep document metadata in a separate manifest instead of extracting it from the PDF text, and when would you extract it instead?
2. A policy and a newer KB article disagree. How should retrieval handle that, and which metadata helps?
3. Why render test documents to PDF instead of indexing the Markdown directly?

### 2026-11-08: Parse once, chunk three ways

**What we built:** [retrieval/chunks.sql](../../retrieval/chunks.sql). `ai.parsed_docs` holds the 30 PDFs parsed once with `ai_parse_document` and joined to the manifest. `ai.chunks` holds three strategies side by side: `whole` (`ai_prep_search`, 30 chunks), `section` (one per heading, 103 chunks, about 38 words each) and `fixed` (60-word windows every 50 words, 99 chunks, about 52 words). Change data feed is on, ready for the index. I chose three strategies over two. The window size, the overlap and the title prefix on `section` and `fixed` chunks were drafted by Claude at my request; I must be able to defend them.

**Key concepts:**
- Parse once, chunk many: parsing is the billed LLM step, so its raw result is stored and every strategy reads that table.
- A chunk has two faces: `chunk_to_embed` (text plus title, headings, metadata: what the search matches on) and `chunk_to_retrieve` (what the LLM reads).
- `ai_prep_search` cuts into retrieval-sized pieces, and our docs (about 140 words) are smaller than one, so it kept each whole. It also enriched `chunk_to_embed`: it read the header line into Department, Document Type and Effective Date, and listed every section name.
- The parser returns typed elements (title, section_header, text, page_header), so "cut at headings" is a running count: `count_if(type = 'section_header') OVER (PARTITION BY doc_id ORDER BY pos)` gives each element its section number.
- A fair test changes one thing: `fixed` pieces are close to section size and both get the title, so `section` versus `fixed` tests where the cut falls, not size or context.
- Fixed cuts break rules in half. In `fin-credit-notes`, "Above SAR 1,000 and up to SAR 5,000: the regional sales" ends one piece and "manager" starts the next, and the SAR 5,000 rule lands in a piece without its "Approval limits" heading.
- One table, one index: the `strategy` column lets a single AI Search index serve all three through a filter.

**Mistakes:**
- Claude's plan assumed `ai_prep_search` would give section-sized "semantic" chunks. Measuring chunks per document (exactly 1.0) caught it before the eval was built on it. We added a hand-written `section` strategy and renamed the managed one `whole`.

**Interview questions:**
1. Your managed chunker returns one chunk per document. Is that a bug, and when is not chunking the right choice?
2. Why store the parser's output in a table instead of parsing inside the chunking query?
3. How would you choose a chunk size for a new corpus, and how would you prove the choice was right?
