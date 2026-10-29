# Sanad

A governed multi-agent copilot for **Najm Supply Co.**, a fictional B2B distributor in Riyadh. It is built end to end on Databricks: raw CRM, ERP and service-desk data goes in, and evaluated, monitored agents in production come out.

> "I took a business problem from use-case canvas to a production agent with measured quality, cost and adoption."

**Status:** Phase 0, discovery and setup. See the [plan](https://claude.ai/artifact/UND3Btf78UiXs1UUzjeQQT) for all nine phases and the three gates.

## What this repo will show

- A live chat app where three agents answer questions, look up live data, and propose actions that a human approves.
- A medallion Lakehouse with data-quality rules, PII masking and lineage you can click through.
- An evaluation report and monitoring dashboard: accuracy, groundedness, safety, latency and cost per request.
- CI/CD with an evaluation gate that blocks a bad prompt from shipping, plus architecture docs, decision records and a runbook.
- A one-page use-case roadmap.

## Where things live

| Folder | What's in it | Phase |
|---|---|---|
| [docs/00-discovery/](docs/00-discovery/) | Use-case canvas, scoring, roadmap one-pager | 0 |
| [data_gen/](data_gen/) | Synthetic CRM, ERP, ITSM data and documents, with seeded problems | 1 |
| [pipelines/](pipelines/) | Lakeflow declarative pipeline: bronze, silver, gold | 1 |
| [governance/](governance/) | Grants, row filters, column masks, tags (SQL) | 2 |
| [retrieval/](retrieval/) | Parsing, chunking, index build, retrieval eval | 3 |
| [tools/](tools/) | Unity Catalog functions used as agent tools | 4 |
| [agent/](agent/) | Agent Bricks project: `agent.toml`, LangGraph graph, prompts, schemas | 4, 5 |
| [mock_systems/](mock_systems/) | FastAPI CRM/ERP/ITSM/Teams mock and MCP server | 5 |
| [evals/](evals/) | Datasets, scorers, red-team set, `run_eval.py` | 6 |
| [monitoring/](monitoring/) | Production monitoring config, dashboard queries | 7 |
| [tests/](tests/) | Unit and integration tests | every phase |
| [.github/workflows/](.github/workflows/) | `ci.yml` (lint, test, eval gate) and `deploy.yml` | 7 |
| `databricks.yml` | Bundle: pipelines, jobs, apps, dashboards; dev and prod targets | 7 |

## Docs

- [Scenario and agents](docs/scenario.md): who Sanad serves, the four agents, the synthetic data
- [Architecture](docs/architecture.md): layers, data flows, governance rules
- [Agent card](docs/agent-card.md): purpose, tools, data, limits, latest eval scores
- [Skill coverage](docs/skill-coverage.md): every JD line mapped to evidence in this repo
- [Success metrics](docs/success-metrics.md): how each JD success measure is reported
- [Decision records](docs/adr/) · [Runbook](docs/runbook.md) · [Access matrix](docs/access-matrix.md)
- [Reading list](docs/reading-list.md): official docs to read before each phase
- [Learning log](docs/learning-log/): notes, mistakes and interview questions, one file per phase

## Working on this repo

[CLAUDE.md](CLAUDE.md) sets the rules for Claude Code here. It works in the Learning output style and leaves `TODO(human)` for every judgement call. Each task follows the same loop: read first, plan, build, break it on purpose, explain back (`/explain-back`), record (`/adr`).

Screenshots and a recorded 5-minute demo arrive in Phase 8.
