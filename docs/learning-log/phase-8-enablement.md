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
