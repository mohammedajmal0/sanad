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

### 2026-11-10: First user feedback: a crashed turn, a false excuse, an unhelpful question

**What I saw in the UI (with 👎):**
- **"Duplicate Invoices"** got "which customer?". Rule 5 (ask when unclear) worked as designed: honest, but not helpful.
- **The follow-up "INV-027711, INV-050001" crashed** ("Agent invocation failed: Invalid json output"). The app log showed `StructuredAnswer`'s formatter returning **empty** output twice, after which our code failed the whole turn.
- **"How many invoices are there?"** got "the available data does not include invoice records", which is false. No tool counts invoices across customers, and the model invented an excuse.

**What we built:**
- **The formatter falls back instead of failing the turn** ([agent/agent/answer.py](../../agent/agent/answer.py)). After two failures it keeps the agent's own reply as a low-confidence Answer, marks it `unformatted` (the UI badge then says "not checked against the answer format"), and logs a WARNING. Citations are still added by code. I chose this over a friendly error, because the user keeps the answer and the badge says it wasn't checked.
- **Reproduced locally:** the same two turns, replayed four times, fell back once (inside the run, the WARNING fired and the user still got "Both invoices are duplicates … ORD-027711 … SAR 1,440.71"). The empty output is intermittent, and its cause in the model is still unknown.
- **The false excuse is now an evaluation case,** `fb-invoice-count` ([evals/cases.py](../../evals/cases.py)): never claim there's no invoice data; give a count from a tool, or ask which customer.

**Key concepts:**
- **Feedback → evaluation cases → fixes.** A 👎 from a real user became a test case the agent must pass on every run. That's the loop the thumbs exist for.
- **Graceful degradation is honest about itself.** The fallback answer reaches the user, labelled as unchecked, and the log records it. That's different from both crashing and silently passing an unchecked answer off as checked.
- **Without spans, the 👎 had no evidence.** I could see *that* I disliked the answer, but not what the agent did. The app log was the only record.

**Mistakes:** "fail loudly" (Phase 4's choice in `StructuredAnswer`) was right for development and wrong for a user: the loud failure landed on the user, not on us.

**Interview questions:**
1. Your structured-output step sometimes returns empty output. What should the user see, and how do you make sure you find out it happened?
2. How do you turn a user's thumbs-down into something that prevents the same failure next release?
3. Your agent says "the data doesn't include invoice records" when it does. Is that a hallucination, a tool gap, or a prompt problem, and how do you tell?

### 2026-11-10: Production tracing kept simple (my decision)

**Decision:** no Unity Catalog trace storage for now. Production keeps trace records and thumbs, and debugging uses the app log or a local replay. Evaluations and local runs keep full traces. The gap and the upgrade path (MLflow traces in UC tables through the workspace's OpenTelemetry endpoint, which needs a preview) are in the agent card's Known limitations, which Claude filled in at my request.

**Key concept:** deferring is a decision when it's written down with its cost and its fix. The cost here: a 👎 on a production answer shows *what* happened but not *how*.

**Interview question:** you found that production traces are incomplete. Why might you choose not to fix it yet, and what would make you change your mind?

### 2026-11-10: Success-metrics dashboard, built to be frugal

**What we built:**
- **[monitoring/refresh_metrics.py](../../monitoring/refresh_metrics.py)** writes three small tables in `sanad.ops` in 50 seconds:
  - `eval_scores`: one row per full eval run, from `system.mlflow.runs_latest`;
  - `gateway_daily`: model requests per day, production (the app's principal) vs testing (me), from `system.ai_gateway.usage`;
  - `app_feedback`: questions, conversations and thumbs per day, from the app's trace records through the MLflow API.
- **Dashboard `Sanad success metrics`** ([dashboards/sanad_metrics.lvdash.json](../../dashboards/sanad_metrics.lvdash.json), in `databricks.yml`): 12 counters, a quality trend across runs, production vs testing traffic, and an honest "not measured yet" tile for effort saved and reuse.
- **Every query was tested before deploy.** The bundle deploy created 1 resource and changed 0 others.

These were written by Claude at my request; I must be able to defend them: the three tables and their grain, the production/testing split by requester, the baseline token correction, and the tile choices.

**Key concepts:**
- **Frugal means the expensive work happens once, when I choose.** A dashboard is queries that run on every open. Pointing it at tiny summary tables instead of growing system tables makes each open nearly free, and unchanged Delta tables let the warehouse serve repeat views from its result cache. The price is staleness until the next refresh.
- **Summaries are also a privacy boundary.** System tables hold e-mails and IP addresses; the summary tables hold counts. The dashboard can't leak what it never reads.
- **Fix bad history where it's consumed, and say so.** The baseline run's token metric used the old, inflated count. The refresh takes it from the re-score run, by run id, with a comment, so the trend doesn't show a fake 25× improvement.

**Mistakes:** the first version of `app_feedback_rows` grouped trace records by the second, not the day. That would have summed per-second distinct sessions, overcounting conversations. Caught by reading the code before the first run.

**Open:** warehouse auto-stop from 10 to 5 minutes. The CLI change was blocked by the permission check, so it's left for me to do in the UI.

**Interview questions:**
1. How would you build a metrics dashboard for an agent that doesn't wake a warehouse every time someone opens it?
2. Your system tables contain user e-mails and IP addresses. How do you build a dashboard on them without exposing those?
3. A historical metric was measured wrongly. Do you fix it at the source, or where it's consumed? What are the trade-offs?

### 2026-11-10: The agent's own model service: fallback, rate limits, inference table

**What we built:**
- **Unity Gateway model service `sanad.ai.sanad_agent_model`** ([governance/sanad_agent_model.json](../../governance/sanad_agent_model.json)):
  - **Routing:** primary `gpt-oss-120b`, fallback `llama_v3_3_70b_instruct`. That's another model family, and not the judge's qwen.
  - **Rate limits on the app's principal:** 120 calls/min (~17 questions) and 1M tokens/hour (~100 questions). Anyone else calling it directly gets 30 calls/min.
  - **Inference table** `sanad.ops.sanad_agent_model_payload`: the *gateway* logs every model call into UC. That partly closes the "no production spans" gap: we can't see tool calls, but we can see what the model was sent and what it returned.
- **Bound with `agentbricks experimental models bind`.** Deploy granted the app EXECUTE and set `AGENT_MODEL_SERVICE_AGENT`. A live question returned "Abha" through the service. Evaluations still call `system.ai.gpt-oss-120b` directly (no deploy env locally), so they never hit the app's rate limit.
- **No spend budget:** budgets are account-admin and only *notify*. Rate limits actually cap usage.

**Mistake:** the first create failed with "Destination model 'system.ai.meta-llama-3-3-70b-instruct' does not exist". Service names and model names differ, and the system service's own config showed the real model, `system.ai.llama_v3_3_70b_instruct`.

**Key concepts:**
- **A model service is a governed wrapper around models.** Who may call it (EXECUTE), where traffic goes (routing and fallback), how much (rate limits), and what's recorded (inference table) are set in one Unity Catalog securable, not in agent code.
- **Rate limits cap, budgets alert.** For runaway-loop protection, you want the thing that says no.

**Interview questions:**
1. Your primary model's provider has an outage. What happens to your agent, and where is that decided?
2. How did you size the rate limits, and what does a user see when one is hit?
3. Why log model calls at the gateway rather than in the app?

### 2026-11-10: Deploy from GitHub Actions (wired, skipped without credentials)

**What we built:** a `deploy` job in [.github/workflows/ci.yml](../../.github/workflows/ci.yml). It runs on `main` after `tests` and the red-team gate: `databricks bundle validate && databricks bundle deploy`, then `agentbricks deploy sanad-cs`. Like the red-team job, it prints a notice and skips while the repository has no Databricks credentials (Phase 6 decision: CI stays as is).

**Open before switching it on:** pin `databricks/setup-cli` to a release tag or commit SHA, because this job will hold deploy credentials.

**Key concept:** **deploy is gated by evaluation.** `needs: [tests, red-team]` means a prompt or code change that breaks a safety behaviour can't reach production from `main`.

**Interview question:** what stops a bad prompt change from being deployed automatically in your pipeline?
