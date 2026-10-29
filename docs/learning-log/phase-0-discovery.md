# Phase 0: Discovery and setup

**Goal:** decide what to build and why, the way you would at Grey Lines. Week 1, about 6 hours.

**Done when:** you can pitch the [roadmap](../00-discovery/roadmap.md) in two minutes.

## Read first

- [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
- [Databricks agent skills for coding assistants](https://docs.databricks.com/aws/en/dev-tools/cli/reference/aitools-commands)
- [Claude Code output styles](https://code.claude.com/docs/en/output-styles)
- [Claude Code docs map](https://code.claude.com/docs/en/claude_code_docs_map.md)

## Concepts to learn

- Use-case canvas: problem, users, data, actions, risks, value metric.
- Value-versus-feasibility scoring.
- When a problem needs an agent, a workflow or plain retrieval.

## Interview questions for this phase

1. How do you decide a problem needs an agent at all?
2. How would you run a discovery workshop with a team that wants "ChatGPT for everything"?

## Entries

### 2026-10-29: Repo skeleton and docs

**What we built:** the repo skeleton from the plan. It includes [CLAUDE.md](../../CLAUDE.md), the Learning output style in `.claude/settings.json`, and three skills (`explain-back`, `adr`, `interview-drill`). Also the `docs/` tree (scenario, architecture, agent card, skill coverage, success metrics, ADR template and [ADR 0001](../adr/0001-isolate-beta-features.md), runbook and access-matrix skeletons, discovery templates) and a README in each layer folder.

**Key concepts:**
- Docs as code: decisions, runbooks and the agent card live next to the code and change in the same pull request.
- ADR: a short record of context, options, decision and consequences, written when you choose between options.
- TODO(human): marks every judgement call (scores, prompts, rules, thresholds) so Claude Code drafts plumbing and you own decisions.
- Skill coverage matrix: each JD line maps to a file in the repo; an empty Evidence cell is the next task.

**Mistakes:**
- TODO(human): add anything you got wrong or had to look up while reviewing these files.

**Interview questions:**
1. Why keep architecture docs and decision records in the repo rather than a wiki?
2. What belongs in an agent card, and who reads it?
3. Why isolate Beta platform features behind a thin layer, and what does that cost you?
