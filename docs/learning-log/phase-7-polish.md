# Phase 7 — Polish

**Goal:** a business-user chat surface (citations, approval, feedback) on the Agent Bricks UI, plus later dashboard / game-day work.

**Read first:** [CHAT_APP.md](../../agent/CHAT_APP.md), [AGENTKIT_CONTRACT.md](../../agent/AGENTKIT_CONTRACT.md), [success-metrics.md](../success-metrics.md).

## Entries

### 2026-11-10: Business chat UI (Answer card, approval, thumbs stub)

**What we built:** a Sanad-facing chat view in [agent/ui/](../../agent/ui/) with Answer cards (citations, confidence), a clearer approval card that still calls `resume()`, developer panes behind `?dev=1` / a Developer toggle, hard-coded Al-Faris samples (no live agent calls), and `POST /api/demo/feedback` in [runtime/ui.py](../../agent/runtime/ui.py) that returns 501 until a turn `trace_id` reaches the UI. Tests in [test_demo_ui.py](../../agent/tests/test_demo_ui.py).

**Key concepts:**
- Answer card: render `additional_kwargs.answer` (schema-checked), not only free-text Markdown.
- Approval: LangGraph interrupt + existing `input.resume` on the same session — Approve is not a new user message.
- Human feedback in MLflow 3.18: `mlflow.log_feedback(trace_id=..., name="user_thumbs", value=..., source=AssessmentSource(HUMAN, user))` — needs the turn’s `trace_id`, which invoke events do not expose today.

**Mistakes:**
- Assumed thumbs could be wired in `runtime/ui.py` alone; without emitting `span.trace_id` from the invoke path (`agent.py` / `adapter.py`), the UI cannot target the right trace. Session search and `get_last_active_trace_id()` are unsafe across turns/workers.

**Interview questions:**
1. A write tool pauses for approval in LangGraph. What does the client send to continue, and what must stay the same across that request?
2. You want a thumbs-up rate from production chat. Where does the feedback live in MLflow, and what identifier ties it to one turn?
3. Why is `mlflow.get_last_active_trace_id()` a bad way for a separate HTTP handler to find “the trace for the message the user just thumbed”?

### 2026-11-10: Thumbs wired to MLflow; real questions instead of canned answers

**What we built:**
- **The trace id rides with the answer.** `StructuredAnswer` runs inside the turn's MLflow trace (`run_agent`'s `start_trace`), so it adds `mlflow.get_current_active_span().trace_id` to the answer message's `additional_kwargs` ([agent/agent/answer.py](../../agent/agent/answer.py)). The UI reads it in `handleAgentMessage`. No new event type and no adapter change; the AgentKit contract is untouched.
- **`POST /api/demo/feedback` is real.** It calls `mlflow.log_feedback(name="user_thumbs", value=True|False, source=HUMAN <signed-in user>)` on that trace. It's a trust boundary: `trace_id` must look like an MLflow trace id (`tr-` plus hex), and `value` must be up or down; anything else is a 422 and never reaches MLflow.
- **The business view's buttons now ask the agent real questions.** The canned sample answers moved behind `?dev=1`: a business user would read made-up Al-Faris data as real.

These were written by Claude at my request (the first entry's UI too, in a second session); I must be able to defend them: the Answer card, the approval card, the dev toggle, the feedback route and its validation, and where the trace id comes from.

**Key concepts:**
- **Find the id where the work already happens.** The answer formatter runs inside the trace, so the id is one call away. Passing it through the existing message avoided changing the runtime contract.
- **Every input from the browser is untrusted.** Even a thumbs click carries an id that addresses MLflow; validate its shape before using it.

**Interview questions:**
1. How does a thumbs-up in your chat UI end up attached to the exact agent run that produced the answer?
2. What would go wrong if the UI showed hard-coded sample answers to business users?
3. Your feedback endpoint takes a trace id from the browser. What do you validate, and what can a malicious user still do?

### 2026-11-10: Deployed and verified; found production traces have no spans

**Verified live:** deployed `1b168b8`. "Write me a short poem" got `next_action: out_of_scope`, and the answer message carried `trace_id`. `POST /api/demo/feedback` on the deployed app returned `logged: true`. In MLflow, the trace record holds `user_thumbs = True` with source HUMAN. Thumbs work end to end.

**Found: no deployed trace has spans.** The app's log has had `WARNING mlflow.tracing.export: Failed to send trace … us-west-2.storage.cloud.databricks.com … Connection refused` on every turn today:
- A trace is saved in two parts: the **record** through the Databricks API (it works: id, status, assessments), and the **spans** uploaded straight to cloud storage. The app is refused at that second step, likely by Free Edition's outbound network rules.
- `mlflow.get_trace` returns nothing, and `get_trace_info` returns the record. `search_traces` on the app's experiment showed nothing after 9 Nov. Those older traces probably came from `agentbricks dev` on the laptop, which *can* reach storage, as can every evaluation run.
- Consequence: thumbs and metrics work, but a production answer can't be debugged from its trace.

**Key concepts:**
- **Monitor the monitoring.** Telemetry that fails with a WARNING fails silently. A canary that writes a trace and reads it back would have caught this on the first deploy.
- **"Logged" isn't "stored".** The feedback API succeeded because the trace record existed; the spans it should explain were never saved.

**Next (Phase 7):** check whether traces can go to Unity Catalog tables through Databricks APIs on Free Edition (MLflow 3's trace-to-UC option), and add a trace read-back check after each deploy.

**Interview questions:**
1. Your production agent's traces show up in the list but can't be opened. How do you find out why?
2. How would you detect that your observability pipeline has stopped working, before you need it during an incident?
