# Phase 8: Enablement: agent template, walkthrough, demo scripts

**Goal:** coach others and explain the trade-offs.

**Done when:** the reusable agent template, a 30-minute walkthrough, and the 5-minute business and 20-minute technical demo scripts are written and rehearsed.

## Entries

### 2026-11-10: Template, walkthrough and demo scripts written

**What we built:**
- **[docs/agent-template.md](../agent-template.md):** Sanad's eleven reusable parts. Each row points to the working file, says why it exists and what to change; there's no copied code that could drift. Plus a day-one checklist and what *not* to copy.
- **[docs/walkthrough.md](../walkthrough.md):** "Give the agent a new tool in 30 minutes". It's the path `get_invoice` took, as an exercise on a real open gap (`fb-invoice-count`: no tool counts invoices across customers).
- **[docs/demo-scripts.md](../demo-scripts.md):** the 5-minute business and 20-minute technical scripts, with a warm-up checklist (Free Edition stops idle apps) and a fallback if the live demo fails.
- README and skill-coverage now link them.

These were written by Claude at my request; I must be able to present every line of the demo scripts and defend every row of the template.

**Not done: rehearsal.** That's mine: run each script against the clock at least once, then tick it on the tracker.

**Key concepts:**
- **A template made of pointers can't go stale.** Copied code drifts from what runs. A table of "copy this file, change this part" stays true as long as the files do.
- **Teach with a real gap.** An exercise that closes an actual failing case is more convincing than a toy, and it shows the whole loop: tool, prompt, evaluation, deploy.
- **A demo needs a fallback.** Live systems on Free Edition fall asleep. The evaluation traces and the dashboard tell the same story without the live app.

**Interview questions:**
1. How would you get a second team building agents on your platform in their first week?
2. In a 5-minute demo for a business audience, what do you leave out, and why?
3. Your live demo fails in front of the panel. What's your plan?

### 2026-11-11: Animated system tour

**What we built:** [docs/system-tour.html](../system-tour.html):
- One self-contained page (inline SVG, CSS and plain JavaScript, no libraries). The same file is published as a [claude.ai page](https://claude.ai/artifact/6xc6qgQ2bkupSLxLGjhj8E).
- 16 chapters in four acts: the data, the question, quality, recap.
- Each step zooms the map onto one part, dims the rest and moves dots along the lines.
- The side panel gives the analogy, the step, the real names and an exhibit: invoice rows, the Answer JSON, the approval card, the eval scoreboard.
- A red dot follows the Al-Faris duplicate invoice from `generate.py` to the eval gate.

**Written by Claude at my request:**
- the chapter wording and the analogies;
- which parts are labelled "runs by itself", "a person runs it" and "not yet".

I must be able to defend each label. Every number in the captions comes from the repo: `generate.py`, the governance log, ADR 0003, `gateway_daily`, run `bd0fd808` and the others.

**Caught along the way:** commits landed while the tour was being planned: the gateway model service, the CI deploy job and the Phase 8 docs. The facts were re-checked against `git log` before writing, so the tour shows the fallback model, the rate limits and the skipped deploy job.

**Key concepts:**
- **Show what isn't built.** The map uses three line styles:
  - solid: runs by itself;
  - dashed: a person runs it (uploads, `chunks.sql`, index sync, `refresh_metrics.py`, deploys);
  - dotted grey: wired but skipped (the red-team and deploy jobs in CI).

  Being open about the gaps makes the rest believable.
- **One thread through the system.** The seeded duplicate invoice is both the demo story and the evaluation's ground truth. One dot can therefore explain ingestion, governance, tools, citations, approval and evaluation.
- **The map is data.** Stations and lines are two tables in the script, and each chapter is a list of steps (focus, moves, caption). Changing the system means editing a row, not redrawing a picture.

**Interview questions:**
1. Walk me through what happens, end to end, when an account manager asks why a customer was billed twice.
2. Which parts of your system run by themselves and which still need a person, and what would you automate next?
3. Where exactly are permissions enforced when an agent reads a table, and how would you prove it?

### 2026-11-11: Consolidated learning guide in Simplified Technical English

**What we built:** [sanad-learning-guide.html](sanad-learning-guide.html), one self-contained page (inline CSS and SVG, system fonts, no libraries) that puts the nine phase logs into one study guide. The same content is published as a [claude.ai page](https://claude.ai/artifact/MwdhPeXkdXECvUz8baWex4).
- **Twelve lessons** that came back across phases, each with its rule, its reason and the tasks where it occurred.
- **Every phase as dated task cards:** what we built, key ideas, mistakes with their owner (only where the log names one), and the decisions Claude wrote that I must defend.
- **Six diagrams** (system map, diary against whiteboard, three locks, specialists as tools, one write end to end, the evaluation loop) and four small charts of the Phase 6 scores across the six runs, each with its floor.
- **A mistake catalogue** by kind, numbers to know, all 138 interview questions (one exact duplicate removed) and a glossary.
- **Two copies, one look:** the repo file is a full HTML document that opens in any browser; the published copy drops the first four wrapper lines.
- **README** links the guide.

These were written by Claude at my request; I must be able to defend them: the STE rewording, the twelve-lesson grouping, the mistake categories, and the diagrams.

**Checks:** a script flagged each sentence over 25 words and each paragraph over 6 sentences (the remaining flags are false alarms on closing quotes), confirmed that every number and ID in the guide appears in a phase file, and matched the question count for each phase.

**Not done:** the tracker row. The tracker belongs to another organization, and this account can't write its data.

**Key concepts:**
- **ASD-STE100 (Simplified Technical English)** is a controlled language from aerospace maintenance manuals: 20 words at most for an instruction, 25 for a description, active voice, simple tenses, one meaning for each word. Technical names stay as they are. Without the licensed dictionary, only the writing rules were applied.
- **A derived document is a snapshot.** Three Phase 7 entries and the Phase 8 file landed while the guide was being written. The phase files stay the source, and the guide states its date.
- **Check a rewrite by machine.** Rewording 1,400 lines by hand can change a fact. A script that looks up every number and ID in the sources catches that cheaply.

**Mistakes:**
- **Unreadable diagrams.** Claude's first draft scaled 980-pixel diagrams into the 575-pixel text column, so their labels were about 7 px. One screenshot showed it. Figures now use the full content width, and on a phone they scroll inside their frame.

**Interview questions:**
1. You consolidate many engineering logs into one guide. How do you make sure the rewrite did not change a fact?
2. Why write technical documentation in a controlled language like Simplified Technical English, and what does it cost?
3. A derived document and its source disagree. Which one wins, and how do you make that clear to readers?
