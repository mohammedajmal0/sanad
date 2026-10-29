# Sanad: project memory

## Why this repo exists
Portfolio project for a Senior AI Agent & Databricks Lakehouse Engineer role.
I must be able to explain every line in an interview. Learning beats speed.

## How to work with me
- Before code for a new concept: explain it in under 150 words, then ask me one check question.
- Plan first; wait for my OK before multi-file changes.
- Leave TODO(human) for: business rules, prompts, tool descriptions, eval scorers,
  data-quality expectations, grants and masks.
- After each task, append to docs/learning-log/<phase>.md: what we built,
  key concepts, mistakes, and 3 interview questions (questions only).
- Databricks names changed in 2026 (AI Search, Declarative Automation Bundles,
  Genie agents, Agent Bricks CLI). If unsure an API is current, say so and
  check the installed Databricks skills or docs before writing code.
- Never hard-code secrets, tokens or workspace URLs.

## Project facts
- Catalog: sanad; schemas: bronze, silver, gold, ai, ops
- Python 3.12, uv, ruff, pytest
- Agent: LangGraph via Agent Bricks CLI in agent/; tools declared in agent.toml
- Commands: uv run pytest | agentbricks dev | databricks bundle validate
- Plan: https://claude.ai/artifact/UND3Btf78UiXs1UUzjeQQT (phases, gates, reading list)

## Definition of done
Tests pass, docs updated, learning-log entry written, and I can explain it.
