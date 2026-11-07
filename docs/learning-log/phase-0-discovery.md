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
- `TODO(human)` marked every judgement call (scores, prompts, rules, thresholds) so Claude Code drafted plumbing and I owned decisions. Since 2026-11-07 Claude writes them too and the log records which ones.
- Skill coverage matrix: each JD line maps to a file in the repo; an empty Evidence cell is the next task.

**Mistakes:**
- None recorded.

**Interview questions:**
1. Why keep architecture docs and decision records in the repo rather than a wiki?
2. What belongs in an agent card, and who reads it?
3. Why isolate Beta platform features behind a thin layer, and what does that cost you?

### 2026-11-07: Canvas scoring, roadmap and pitch

**What we built:** the filled [use-case canvas](../00-discovery/use-case-canvas.md) (risks, value metrics and agent/workflow/retrieval for the three scenario cases, three more candidates, scores, picks, rejection reasons), the [roadmap](../00-discovery/roadmap.md) with the two-minute pitch, and [ADR 0001](../adr/0001-isolate-beta-features.md) accepted. All of it was drafted by Claude at my request after Phases 1 and 2 were built, so the pitch uses real numbers from the data (Al-Faris 1,440.71 SAR twice; Jeddah 16% late). I must be able to defend every score and deliver the pitch without notes. The job description is still empty: it has to be pasted from the real posting.

**Key concepts:**
- Not everything is an agent. Delivery analytics is NL-to-SQL retrieval (a Genie agent), invoice capture is a workflow, and forecasting is a model. Only billing and service-desk triage need tool choice plus actions.
- Score risk as safety (5 = safest) so "higher is better" holds for every column; weight value double because it is the reason to build.
- Roadmap order follows risk, not just score: read-only analytics first to earn trust, then write actions behind approval.
- Label estimated baselines as estimates until timed runs replace them.

**Mistakes:**
- None recorded.

**Interview questions:**
1. Your top-scoring use case ships second. Why would you not just ship the highest score first?
2. How do you decide whether a problem needs an agent, a workflow or plain retrieval?
3. Your pitch quotes "20 minutes per billing question". How would you defend or measure that number?
