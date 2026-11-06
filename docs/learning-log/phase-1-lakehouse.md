# Phase 1: Synthetic data and the medallion pipeline

**Goal:** turn Najm's fake CRM, ERP and ITSM data into clean, governed tables the agents can trust.

**Done when:** the pipeline graph is green, expectation metrics are visible, and the seeded Al-Faris duplicate invoice appears in `gold.invoice_issues`.

## Read first

- [Lakeflow Spark Declarative Pipelines best practices](https://docs.azure.cn/en-us/databricks/ldp/best-practices)

## Concepts to learn

- Medallion architecture: bronze (raw, as received), silver (cleaned and typed), gold (business-ready answers).
- Streaming table (processes only new data) versus materialized view (a stored query result kept up to date).
- Auto Loader: picks up only new files from a folder.
- Expectations: data-quality rules that warn, drop or fail.

## Entries

### 2026-11-06: Synthetic data generator with seeded problems

**What we built:** [data_gen/generate.py](../../data_gen/generate.py) creates 2,000 accounts, about 4,000 contacts, 50,000 orders with invoices and shipments, and about 10,000 IT tickets for Nov 2025 to Oct 2026. CRM and ERP data is written as CSV (batch exports) and tickets as JSON lines, one file per month (an event stream). `seed_problems()` plants three problems, the ground truth for evaluation:

| Problem | What was planted | How it shows in the data |
|---|---|---|
| Duplicate invoice | Al-Faris Trading's order `ORD-027711` invoiced twice, same amount, 4 days apart | `INV-027711` (14 Sep) and `INV-050001` (18 Sep), both 1,440.71 SAR |
| Late deliveries | Carrier Red Sea Cargo struggles in Jeddah in Q3 2026 | Jeddah's late rate is 16%; the other regions are 1 to 2% |
| VPN incident | A software update on Monday 19 Oct 2026 breaks the VPN | 30 VPN tickets that Monday, fading to 3 by Friday; normal is about 2 a day |

[tests/test_data_gen.py](../../tests/test_data_gen.py) checks that the same seed gives the same data, that the row counts are right, and that each planted problem is present.

**Key concepts:**
- Fixed random seed: `random.Random(42)` gives the same "random" data every run, so the eval's right answers never move.
- Signal versus noise: the base data already has about 3% late deliveries and about 2 VPN tickets a day. A planted problem must stand out from that background.
- Cause, not just symptom: lateness is tied to one carrier in one region, so the agent can answer "why", not only "where".
- Tests first as a spec: the three ground-truth tests were written before the seeding code, and they defined "done".
- Dropped Faker: its `ar_SA` locale produced US-format phone numbers, so plain Python name lists gave more realistic data with one less dependency.

**Mistakes:**
- TODO(human): add anything you got wrong or had to look up.

**Interview questions:**
1. Why does synthetic test data need a fixed seed, and what breaks without one?
2. How do you make a seeded anomaly detectable without making it trivially obvious?
3. Why plant a cause (one carrier in one region) and not just a symptom (random late deliveries)?

### 2026-11-07: Unity Catalog setup, upload, and the bronze layer

**What we built:** CLI login (OAuth profile `sanad`), the `sanad` catalog with five schemas and the `sanad.bronze.landing` volume ([setup.sql](../../pipelines/setup.sql)). Data files were uploaded to the volume, with October's tickets held back for a streaming demo. [bronze.py](../../pipelines/transformations/bronze.py) defines six Auto Loader streaming tables, and [databricks.yml](../../databricks.yml) deploys the pipeline `sanad_medallion` (serverless, dev target). First run: all six tables match the source row counts, and the Al-Faris duplicate is in `bronze.erp_invoices`.

**Key concepts:**
- OAuth login with a named profile: no token or workspace URL in the repo.
- Auto Loader (`cloudFiles`): a streaming read that remembers which files it already ingested.
- Bronze stores everything as strings, plus lineage columns `source_file` and `ingested_at`. Auto Loader adds `_rescued_data` for values that don't fit.
- Metadata-driven bronze: one loop over a `SOURCES` dict, with a helper function so each table keeps its own folder (Python closures bind late).
- One pipeline writes to several schemas by naming tables `bronze.x`, `silver.x`, `gold.x` (Free Edition allows one active pipeline).
- Bundle in development mode: the pipeline shows as "[dev <user>] sanad_medallion".

**Mistakes:**
- `databricks fs cp` of a single file doesn't create the parent folder; `databricks fs mkdir` first.
- Logging in on the website doesn't log in the CLI; `databricks auth login` is separate.
- TODO(human): add your own.

**Interview questions:**
1. Why keep bronze as untyped strings instead of casting on ingestion?
2. How does Auto Loader know which files it has already processed, and what happens if a file is overwritten?
3. Why build bronze tables in a loop through a helper function rather than decorating inside the loop?

### 2026-11-07: Silver layer and data-quality expectations

**What we built:** [silver.py](../../pipelines/transformations/silver.py) defines six streaming tables that turn bronze's strings into real types with `TRY_CAST`. Each has a "has ID" drop rule. Invoices also have two drop rules (readable amount, readable date) and two warn rules (positive amount, not in the future), with no fail rule. A clean run passed all 50,001 invoices. Then we broke it on purpose: a 5-row `break_test.csv` with a negative amount, `abc`, `not-a-date`, a 2027 date and a missing ID. Bronze kept all 5, silver kept 2 (the warn rows), and the event log showed each rule's counts.

**Key concepts:**
- `TRY_CAST` versus `CAST`: serverless runs ANSI SQL, where a bad `CAST` crashes the run. `TRY_CAST` returns NULL, and the expectation decides.
- Warn, drop, fail: drop when the row is useless; warn when it may be legitimate (credit note); fail only when the whole load is broken.
- A NULL fails every rule that touches it: the `abc` row failed both `readable_amount` and `positive_amount`.
- Metrics live in the event log: `event_log(TABLE(sanad.silver.invoices))`, `details:flow_progress.data_quality.expectations`.
- The second run's metrics covered only the 5 new rows. That proves Auto Loader read only the new file.
- Business duplicates are kept in silver; removing them would destroy the agent's evidence.

**Mistakes:**
- TODO(human): add your own.

**Interview questions:**
1. When would you choose warn, drop or fail for a data-quality rule, and who should decide?
2. Why does one unreadable value show up as a failure under more than one expectation?
3. Where do dropped rows go, and how would you repair and reprocess them?
