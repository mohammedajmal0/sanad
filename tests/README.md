# tests

Unit and integration tests, run with `uv run pytest`.

**Phase:** every phase

## What goes here

- Unit tests for graph nodes, tools, schemas and business rules. These run locally, without Databricks ([ADR 0001](../docs/adr/0001-isolate-beta-features.md)).
- A 20-question smoke test for the first agent (Phase 4).
- Integration tests against the mock systems (Phase 5).
- In CI, lint, these tests and an evaluation subset run as the gate (Phase 7).

## Done when

A pull request that worsens the prompt fails CI (Phase 7).
