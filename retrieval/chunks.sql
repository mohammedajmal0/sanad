-- Phase 3: parse the policy and KB PDFs once, then chunk them three ways into ai.chunks.
-- Run in the SQL editor on a serverless SQL warehouse (ai_prep_search needs DBR 18.2+,
-- which the Serverless Starter Warehouse has). Input: the PDFs and manifest.csv in
-- /Volumes/sanad/ai/docs/ (see retrieval/README.md). Safe to re-run: CREATE OR REPLACE.
-- Chunk sizes drafted by Claude at my request on 2026-11-08.

-- 1. Parse each PDF once. ai_parse_document is an LLM call (slow and billed), so its
--    result is kept here and every chunking strategy reads this table instead.
CREATE OR REPLACE TABLE sanad.ai.parsed_docs
COMMENT 'One row per PDF in the docs volume: manifest metadata plus the ai_parse_document result'
AS
SELECT
  m.doc_id, m.title, m.doc_type, m.department,
  CAST(m.effective_date AS DATE) AS effective_date, m.language,
  f.path,
  ai_parse_document(f.content) AS parsed
FROM read_files('/Volumes/sanad/ai/docs/*.pdf', format => 'binaryFile') AS f
JOIN read_files('/Volumes/sanad/ai/docs/manifest.csv', format => 'csv', header => true) AS m
  ON f.path LIKE concat('%/', m.doc_id, '.pdf');

-- 2. Chunks cut three ways, in one table. The AI Search index (next task) follows it through
--    the change data feed, and queries filter on `strategy` to compare them.
--    chunk_to_embed is what the search matches on, chunk_to_retrieve is what the LLM reads.
--      whole   : ai_prep_search. It cuts at natural boundaries into retrieval-sized pieces,
--                and our docs (about 140 words) are smaller than one, so each stays whole.
--      section : one piece per heading, cut by hand from the parser's section_header elements.
--      fixed   : 60-word windows every 50 words, blind to headings.
CREATE OR REPLACE TABLE sanad.ai.chunks
COMMENT 'Search-sized pieces of the policy and KB documents, cut three ways (see strategy)'
TBLPROPERTIES (delta.enableChangeDataFeed = true)
AS
WITH whole AS (
  SELECT *, explode(variant_get(ai_prep_search(parsed), '$.document.contents', 'ARRAY<VARIANT>')) AS c
  FROM sanad.ai.parsed_docs
),
elements AS (
  SELECT doc_id, title, doc_type, department, effective_date, language,
    pos, e:type::STRING AS type, e:content::STRING AS content,
    -- running count of headings so far = the section this element belongs to
    count_if(e:type::STRING = 'section_header') OVER (PARTITION BY doc_id ORDER BY pos) AS section_no
  FROM sanad.ai.parsed_docs, LATERAL variant_explode(parsed:document:elements) AS t(pos, key, e)
),
section AS (
  SELECT doc_id, title, doc_type, department, effective_date, language, section_no,
    array_join(transform(array_sort(collect_list(struct(pos, content))), x -> x.content), '\n') AS text
  FROM elements
  WHERE section_no > 0 -- before the first heading there is only the page header and the title
  GROUP BY ALL
  HAVING count_if(type = 'text') > 0 -- a heading with no text under it is not worth a piece
),
words AS (
  SELECT *,
    split(trim(concat_ws(' ', transform(parsed:document:elements::ARRAY<VARIANT>,
                                        e -> e:content::STRING))), r'\s+') AS w
  FROM sanad.ai.parsed_docs
),
fixed AS (
  -- Docs average about 140 words and sections about 40, so 60-word pieces are close to a
  -- section's size: section versus fixed compares where the cut falls, not how big pieces are.
  -- shortcut: words stand in for tokens; use a tokenizer if size must match a model limit.
  SELECT *, array_join(slice(w, first_word + 1, 60), ' ') AS text
  FROM words
  LATERAL VIEW posexplode(sequence(0, greatest(size(w) - 11, 0), 50)) win AS pos, first_word
)
-- audience: who may retrieve the chunk. AI Search has no row security, so the caller
-- filters on it. Rule (drafted by Claude): policies are for all staff, a KB article
-- only for its own department.
SELECT *, CASE WHEN doc_type = 'policy' THEN 'all' ELSE department END AS audience
FROM (
SELECT
  concat('whole:', doc_id, ':', c:chunk_position::INT) AS chunk_id,
  'whole' AS strategy,
  doc_id, title, doc_type, department, effective_date, language,
  c:chunk_position::INT AS chunk_position,
  c:chunk_to_retrieve::STRING AS chunk_to_retrieve,
  c:chunk_to_embed::STRING AS chunk_to_embed -- enriched by ai_prep_search: department, sections
FROM whole
UNION ALL
SELECT concat('section:', doc_id, ':', section_no), 'section',
  doc_id, title, doc_type, department, effective_date, language,
  section_no, text, concat(title, '\n', text) -- heading is already the first line of text
FROM section
UNION ALL
SELECT concat('fixed:', doc_id, ':', pos), 'fixed',
  doc_id, title, doc_type, department, effective_date, language,
  pos, text, concat(title, '\n', text)
FROM fixed
);

-- 3. Check, expect 0 rows: a document with no chunks in some strategy (for example,
--    it failed to parse) can never be found by the agent under that strategy.
SELECT m.doc_id, s.strategy
FROM read_files('/Volumes/sanad/ai/docs/manifest.csv', format => 'csv', header => true) AS m
CROSS JOIN (VALUES ('whole'), ('section'), ('fixed')) AS s(strategy)
LEFT ANTI JOIN sanad.ai.chunks AS c
  ON c.doc_id = m.doc_id AND c.strategy = s.strategy;
