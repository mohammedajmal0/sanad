# 0002: Run the medallion pipeline when files arrive, not from a generator job

- **Status:** Accepted
- **Date:** 2026-11-07
- **Phase:** 1

## Context

Phase 1 planned "a job that runs the generator and the pipeline". The generator is deterministic (seed 42), so every run rewrites the same file names with the same content. Auto Loader tracks ingested files by path and by default does not re-read a file it has already ingested, even when it is overwritten. A generator-then-pipeline job would therefore ingest 0 new rows on every run. Until now, each new batch also needed two manual steps: copy the file into `/Volumes/sanad/bronze/landing`, then `databricks bundle run sanad_medallion`.

Constraints: Free Edition (serverless only, one active pipeline, limited compute quota), and the bundle's dev target runs in development mode, which pauses all schedules and triggers unless a job sets `pause_status` itself.

## Options

1. **File-arrival trigger → pipeline**: a job with one `pipeline_task`, started when new files land anywhere under the landing volume. It won: it treats the generator as what it stands in for (outside CRM, ERP and ITSM systems that Databricks doesn't run), needs about 15 lines of YAML and no Python, and only uses compute when data arrives.
2. **Generator → pipeline, as planned**: two tasks, `generate.py` on serverless writing into the volume, then the pipeline. It lost because every run rewrites identical files and ingests nothing, so it shows that re-runs are safe but never shows new data arriving.
3. **Daily generator batch + schedule**: add a `--batch-date` mode that writes one new day of data under new file names, and run the job daily. It lost on cost of change for Phase 1: generator code and tests first, and new shipments would start "in transit", which the append-only `silver.shipments` can't update later without AUTO CDC.

## Decision

Option 1. The job `sanad_ingest` in [databricks.yml](../../databricks.yml) watches `/Volumes/sanad/bronze/landing/` (all subfolders, checked about once a minute) and runs `sanad_medallion` with `performance_target: STANDARD`. `pause_status: UNPAUSED` keeps the trigger live in development mode.

Timing: `wait_after_last_change_seconds: 60` and `min_time_between_triggers_seconds: 60`. 20 seconds was tried first; the Jobs API rejected it, because both settings have a 60-second minimum. 60 seconds of quiet still covers an ERP export whose three files land about 20 seconds apart, so it becomes one run, not three.

**In my own words:** the generator pretends to be Najm's ERP, CRM and IT systems. In real life Databricks doesn't run those systems; it waits for their exports. Putting the generator in the job would rewrite the same files every run, Auto Loader would skip them, and the job would run and do nothing. The doorbell runs only when real new data lands, and costs nothing while the mailbox is empty. 60/60 is the fastest the API allows, and 60 seconds of quiet is three times the 20-second gap between our export's files, so one export becomes one run. Nobody at Najm needs billing, delivery or ticket data fresher than the roughly 10 minutes it takes from file to gold.

## Consequences

- Easier: no manual `bundle run` after a file lands; no idle runs, so Free Edition quota is spent only when there's new data; the same YAML works for a future prod target, because the pipeline is referenced as `${resources.pipelines.sanad_medallion.id}`.
- Latency, measured on 2026-11-07 with a 3-row file: uploaded 10:00:21, job started 10:02:24 (trigger check plus 60 seconds of quiet), pipeline waited for serverless STANDARD compute for 4 min 12 s, and the actual run took 1 min. File to gold: about 10 minutes. Switch to `PERFORMANCE_OPTIMIZED` only if someone needs fresher data than that, and accept the higher cost.
- A batch whose files arrive more than 60 seconds apart is split into two runs. Gold is briefly half-updated between them.
- Watch the 10,000-file limit for triggers on locations without file events. Landing files are never deleted (about 20 today), so the count only grows; archive old files before it matters.
- If a source system stops sending files, nothing runs and nothing alerts. Add a freshness alert in Phase 7 ([runbook](../runbook.md)).
- The generator stays a local tool for seeding history. Generating fresh daily data (option 3) remains open if later phases need it.
