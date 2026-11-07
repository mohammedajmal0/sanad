---
name: adr
description: Draft an Architecture Decision Record from this conversation, after I chose between options.
---
Copy docs/adr/0000-template.md to docs/adr/<NNNN>-<short-slug>.md, where NNNN is one higher than the highest number in docs/adr/.
Fill Context, Options, Decision and Consequences from this conversation. Use real numbers where we measured something (recall@k, latency, cost).
List every option we actually considered, with one line on why it lost. Do not invent options we never discussed.
Set Status to Proposed and the date to today.
Under Decision, add a one-paragraph plain-language restatement of the reason, marked "Restated by Claude at my request". Set Status to Accepted only if I chose the option in this conversation.
Then ask me one question an interviewer would ask about this decision.
