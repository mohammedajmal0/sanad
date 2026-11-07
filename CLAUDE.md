# Sanad: project memory

## Why this repo exists
Portfolio project for a Senior AI Agent & Databricks Lakehouse Engineer role.
I must be able to explain every line in an interview. Learning beats speed.

## How to work with me
- Before code for a new concept: explain it in under 150 words, then ask me one check question.
- Plan first; wait for my OK before multi-file changes.
- Since 2026-11-07 Claude also writes the judgement calls (business rules, prompts, tool
  descriptions, eval scorers, data-quality expectations, grants and masks) instead of leaving
  TODO(human). Note each one in the learning log as Claude-written; I must still defend it.
- After each task, append to docs/learning-log/<phase>.md: what we built,
  key concepts, mistakes, and 3 interview questions (questions only).
- After each task, also update the tracker rows (db collections phases/, tasks/)
  with the ArtifactData tool. Never republish the page just to change data.
- Databricks names changed in 2026 (AI Search, Declarative Automation Bundles,
  Genie agents, Agent Bricks CLI). If unsure an API is current, say so and
  check the installed Databricks skills or docs before writing code.
- Never hard-code secrets, tokens or workspace URLs.

## Project facts
- Catalog: sanad; schemas: bronze, silver, gold, ai, ops
- Python 3.12, uv, ruff, pytest
- Agent: LangGraph via Agent Bricks CLI in agent/; tools declared in agent.toml
- Commands: uv run pytest | agentbricks dev | databricks bundle validate
- Tracker: https://claude.ai/artifact/Qmbx4MFBL9ZacyAP4JQSzV (phases, gates, tasks);
  reading list in docs/reading-list.md

## Definition of done
Tests pass, docs updated, learning-log entry written, tracker updated, and I can explain it.
