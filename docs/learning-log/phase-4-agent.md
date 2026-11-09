# Phase 4: Agents: LangGraph supervisor, UC tools, structured output, memory

**Goal:** build agents that use tools and apply business rules safely.

**Done when:** the supervisor routes a question to one of three specialists, calls a UC function tool, returns a schema-validated answer, and asks for approval before any write.

**First milestone, Gate A:** the Customer Service agent finds the seeded duplicate invoice, cites the refund policy, and the trace shows every tool call.

## Read first

- [Agent Bricks CLI](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli)
- [Deploy agents on Databricks](https://docs.databricks.com/aws/en/agents/deploy/)

## Concepts to learn

- **Three layers.** The framework (LangGraph: which tool next, when to answer). The agent server (DurableAgentServer: HTTP, streaming, sessions). The runtime (Agent Runtime on Databricks Apps: hosting, URL, service principal).
- **Tools.** The model picks a tool by reading its name and description. The tool's output is the evidence the answer rests on.
- **Unity Catalog function tools run as the app's service principal** (`auth = "app"`), not as the person asking. Row filters and masks then see the service principal.
- **Tracing.** Every model call and tool call becomes a span in an MLflow trace, which is how Gate A proves what the agent did.
- **Human-in-the-loop.** A tool listed for approval pauses the graph, and a new request resumes it.

## Entries

### 2026-11-08: Scaffold the agent with the Agent Bricks CLI

**What we built:** the Agent Bricks project in [agent/](../../agent/), scaffolded with `agentbricks init --framework langgraph --name sanad-cs` (CLI 0.9.0, Beta).
- **Changes from the template:** the memory and session stores were unbound for now, and the model is `system.ai.gpt-oss-120b`.
- **Smoke tests:** it ran locally and was deployed once as the Databricks App `agent-bricks-sanad-cs`, now stopped. Both times the model called the sample tool. The deployed run left a trace in `/Shared/agentbricks_traces/sanad-cs-bevrqu`.
- **Lint and tests:** the root lint skips the template's `agent/runtime/`, and the root pytest runs only `tests/`.

The model choice and the README's run recipe were written by Claude at my request; I must be able to defend them.

**Key concepts:**
- The template already follows ADR 0001: `agent/agent.py:run_agent` uses no Agent Bricks types, and `runtime/` is the thin layer that serves it. A CLI change should touch `runtime/` and `agent.toml`, not the graph.
- **Free Edition shapes the platform choices:**
  - No Claude model is offered, so `experimental models list` decides what's possible.
  - Deploy works without memory and session stores.
  - An app keeps using compute until it is stopped.
- `agentbricks dev` is a convenience, not the agent. It wraps `databricks apps run-local` and adds a local MLflow server. The agent server alone (`uv run start-server`) uses about 380 MB.
- A tool result is evidence, so its format matters. `get_current_time` returns a time with no timezone, and the model labelled it "UTC" both times: wrong on the laptop (IST), right on the app (which runs in UTC). Sanad's tools must return values that can't be misread: timezones, currencies, units.
- Linux puts each app's processes in a cgroup. `systemd-oomd` kills the whole cgroup under memory pressure, so a child process can take its parent app down with it. `systemd-run --user -p MemoryMax=…` gives a process its own capped cgroup.

**Mistakes:**
- **VS Code was killed.** Claude ran `agentbricks dev` inside VS Code on a 7 GB laptop. It peaked above 2 GB at startup, and `systemd-oomd` killed the whole VS Code window twice, ending the session each time. The journal showed the cause. Fixed by running the agent server alone in a memory-capped user unit (recipe in the agent README).
- **Wrong Python version.** `uv` first built the agent's environment on Python 3.14. Pinned to 3.12 with `agent/.python-version`, matching the project standard.

**Interview questions:**
1. Your UC function tools run as the app's service principal. How do you make sure an account manager only sees their own region's customers through the agent?
2. Why keep the agent graph separate from the server that hosts it, and what does that buy you when the platform is in Beta?
3. A tool returns a timestamp without a timezone, and the model confidently calls it UTC. What does that teach you about designing tool outputs?

### 2026-11-08: Three UC function tools, run as the person asking

**What we built:** [tools/functions.sql](../../tools/functions.sql) with `get_customer_summary`, `get_invoices` and `get_shipment_status`.
- **Access:** `EXECUTE` goes to `account_managers` only. The tools are bound in `agent/agent.toml` with `auth = "user"`.
- **Decision:** [ADR 0004](../adr/0004-run-tools-as-the-asking-user.md) records running tools as the asking user. The proof is in [tools/README.md](../../tools/README.md).
- **Result:** the local agent and the deployed agent both answer "Why was Al-Faris Trading invoiced twice in September?" with `INV-027711` and `INV-050001`.

The functions, their descriptions (the `COMMENT`s), the region guard and the access-matrix row were written by Claude at my request; I must be able to defend them.

**Key concepts:**
- **A UC function tool is a stored query plus a description.** The model reads the `COMMENT` to pick the tool and fill its parameters. Agent Bricks serves the function through Databricks' managed MCP endpoint, where it appears as `sanad__ai__get_invoices`.
- **Owner's rights, caller's filter** (tested as the service principal): a function reads its tables with its owner's rights, so callers need only `EXECUTE`. The row filter inside it still checks the caller, so a caller who may not see an account gets 0 rows.
- **One filter guards every tool,** because each function keeps only accounts the caller can see in `customer_360`.
- **`auth = "user"` versus `auth = "app"`:**
  - With the user's forwarded token, Phase 2's rules apply unchanged.
  - With the app's identity, the agent sees nothing, or everything, and you would need a second permission system.
  - The model may choose *what* to look up (`account_id`), never *who* is asking.
- **The deployed run proved whose identity was used.** The service principal would have seen 0 rows, so a full answer proves the tool ran as me.
- **Tool output is evidence, and the model fills gaps.** Locally, the agent added "typical reasons" for the duplicate that no tool returned. The system prompt task must forbid claims without a source.
- **Previews needed:** managed MCP servers (profile menu → Previews, not Settings), plus the app's `mcp.functions` user scope.

**Mistakes:**
- **Hidden error.** The first local run failed with "Could not discover configured MCP tools". Calling the MCP endpoint directly showed the real cause: "Databricks managed MCP servers are not enabled". I enabled the preview, and it worked about a minute later.
- **Silent loop.** Claude's poll loop ended with `| tail -1 && break`. `tail` always succeeds, so the loop stopped after one try and reported nothing. Fixed by checking the probe's own exit code.
- **Deploy into stopped compute.** The redeploy waited 5 minutes for app compute that had been stopped on purpose earlier. `databricks apps start`, then deploy, fixed it.
- **Leftover warehouse permission.** The test's warehouse `CAN USE` for the service principal couldn't be removed. Replacing the warehouse's permission list requires an owner, and it has none. It's harmless and documented in the access matrix.

**Interview questions:**
1. Your agent's tools run as the user. What do you lose compared with running them as a service principal, and when would you choose the service principal anyway?
2. A SQL function reads a table the caller has no `SELECT` on, yet returns rows. Why, and what does that mean for who should own the function?
3. The model chooses the `account_id` it passes to a tool. Why is that safe here, and what parameter would you never let the model choose?

### 2026-11-08: Policy search as a fourth UC function tool

**What we built:** `sanad.ai.search_policies` in [tools/functions.sql](../../tools/functions.sql), bound like the other tools with `auth = "user"`.
- **How it searches:** `vector_search()` runs the ADR 0003 query (`whole` cards, hybrid). The function then keeps each caller's audience, set by `is_account_group_member()`.
- **Quality:** on the 40 eval questions through the function, all 29 that a non-IT user may see hit the top 5 (recall@5 1.00, MRR 0.90), and the 11 IT-only questions returned nothing.
- **Result:** the deployed agent answers "Al-Faris says they were invoiced twice. Is that true, and what does our policy say?" with both invoice ids and the `fin-duplicate-invoices` steps, including telling the customer within 2 business days.

I chose to give the three business groups `SELECT` on the index. The function, its description, the audience mapping and the flagged-first ordering of `get_invoices` were written by Claude at my request; I must be able to defend them.

**Key concepts:**
- **Not every call inside a function uses the owner's rights.** Table reads do. `vector_search()` makes a remote call to AI Search with the caller's identity, so callers need `SELECT` on the index. The service-principal test (`403`) showed it; the docs didn't say.
- **A filter is not a security boundary.** Once users can query the index, the `audience` filter only decides relevance. Real separation means separate indexes with their own grants, the same rule Agent Bricks gives for memory partitions.
- **Build the trusted part into the function.** The audience comes from `is_account_group_member()` inside SQL, never from a tool parameter, so the model can't widen it.
- **Searching without a filter argument:** `vector_search()` has none, so the function fetches the top 100 of all three strategies and filters to `whole`. The re-run of the eval checks this didn't cost quality.
- **Order tool output so the evidence comes first.** The model copied the wrong invoice id out of a 24-row list. With flagged invoices first, it got both right.

**Mistakes:**
- **Wrong expectation.** Claude's check comment said the duplicate-invoice policy would rank first. It ranked 4th for that question, so the comment was corrected.
- **Wrong invoice id.** The model reported `INV-019369` instead of `INV-050001` (local run). Fixed for now by ordering. The prompt and the Gate A eval must catch this kind of error for good.

**Interview questions:**
1. You wrapped a vector search in a SQL function and granted only `EXECUTE`, yet users got permission errors. Why, and how is that different from a table read inside the same function?
2. When is a metadata filter on a retrieval index good enough, and when do you need separate indexes?
3. The model had the right rows but quoted the wrong invoice id. What would you change in the tool, the prompt and the eval?

### 2026-11-08: Answer schema and the system prompt in the Prompt Registry

**What we built:**
- **Schema:** [agent/agent/schema.py](../../agent/agent/schema.py), the `Answer` (`answer`, `citations`, `confidence`, `next_action`). An answer without citations must say `low`.
- **Final step:** [agent/agent/answer.py](../../agent/agent/answer.py), middleware that turns each finished turn into an `Answer` with one extra call that has no tools.
- **Prompt:** the system prompt [customer_service.md](../../agent/agent/prompts/customer_service.md), registered as `sanad.prompts.customer_service@production` and bound in `agent.toml`.
- **Tests:** [test_answer_schema.py](../../agent/tests/test_answer_schema.py) checks the citation rule, the closed `next_action` list, and that the prompt names every bound tool.
- **Result:** the deployed agent returns the `Answer` with `INV-027711`, `INV-050001` and `fin-duplicate-invoices` cited, confidence `high`.

The schema fields and rule, the prompt's rules and the formatting instructions were written by Claude at my request; I must be able to defend them.

**Key concepts:**
- **Structured output has two built-in routes in LangChain:**
  - `ToolStrategy`: the model calls an "Answer" tool, forced with `tool_choice`.
  - `ProviderStrategy`: the model API constrains the reply to a JSON schema.
  - Both depend on the endpoint. gpt-oss behind the AI Gateway ignored the forced tool call and rejected `response_format` together with tools.
- **The fix is an extra step, not a hope.** The agent loop runs with tools, then one call with no tools applies the JSON schema. It costs one more model call per turn but always gives the shape. A validation error gets one retry, then the turn fails.
- **A schema rule can enforce a policy.** "No citations means `low` confidence" stops a sourceless answer from claiming certainty, the failure seen in p4-tools.
- **Prompts are versioned in Unity Catalog.** `@production` is an alias: you register a new version and move the alias, and the agent loads the alias every turn, so no redeploy is needed. A silent fallback to a local copy would hide which prompt ran, so loading fails loudly instead.
- **Least privilege for the app.** Binding a prompt makes deploy grant the app `MANAGE` on the prompt's whole schema, so prompts get their own schema (`sanad.prompts`). Checked afterwards: the app has nothing in `sanad.ai`.

**Mistakes:**
- **Two approaches that failed.** Claude tried `ToolStrategy`, then `ProviderStrategy`, before the extra-step design. Each was a 2-minute local test, and the reason each failed is recorded in `answer.py`, so it isn't tried again.

**Interview questions:**
1. Your model ignores `tool_choice` and rejects a JSON schema when tools are present. How do you still guarantee a structured answer, and what does it cost?
2. Why keep the system prompt in a registry with an alias instead of in the code?
3. What business rule would you put into the answer schema itself rather than the prompt, and why?

### 2026-11-08: Gate A passed

**What we built:** [evals/gate_a.py](../../evals/gate_a.py), which asks the agent "Why was Al-Faris Trading invoiced twice in September?" and checks three things: both duplicate invoices are cited, `fin-duplicate-invoices` is cited, and every tool call has a span in the MLflow trace. The pass/fail rule is in [tests/test_gate_a.py](../../tests/test_gate_a.py).

**Gate A passed on 2026-11-08**, local agent tracing to the workspace experiment: trace `tr-2402bfae449c7aebb2e8332738ea25b6`, 24 spans, calls `get_customer_summary` → `get_invoices` → `search_policies`. Reading "the refund policy" as `fin-duplicate-invoices`, the procedure that says when a duplicate is cancelled, credited or refunded, was Claude's call at my request.

**Key concepts:**
- **A gate is a script, not a demo.** It runs the same question, checks fixed facts, and exits non-zero on failure. Its rule is unit-tested, so the gate itself can't silently rot.
- **"The trace shows every tool call" is checked, not eyeballed.** Every tool call in the answer must appear as a span name in the trace.
- **Traces are written in two parts:** the summary (`trace_info`: request, response, token usage) goes through the API, and the spans go to cloud storage. A trace can be listed before its spans exist, so the gate waits.
- **The runtime namespaces session ids per user,** so a client can't find its own trace by session id. The gate matches on time and the question text instead.
- **Read the token use per span.** Here the four tool-loop calls used about 28k input tokens, and the final formatting call reported **296k in and 19k out**, for a request of about 12k characters and a reply under 1k. A small structured call costs normal amounts (568 in, about 340 out), so something in the real turn inflates it. To investigate with the Phase 6 cost scorer.

**Mistakes:**
- **No spans on the deployed agent.** The deployed app's trace exporter can't reach `us-west-2.storage.cloud.databricks.com`, so deployed traces have no spans. Found from `agentbricks deployments logs`, not from the error the gate printed. Gate A uses the local agent; the deployed gap is in the agent README.
- **Bugs found while building the gate:**
  - The first lookup assumed the session id would appear in the trace.
  - It also assumed `mlflow.search_traces` would list the traces; MLflow 3.18 returned nothing, so the gate reads them over REST.
  - Two 502s were a cold start: the app reinstalls 183 packages after `start`. The gate now retries a 502 for up to a minute.

**Interview questions:**
1. How do you prove an agent used its tools rather than its memory, and what would you check automatically?
2. Your deployed agent's traces have metadata but no spans. Where would you look, and what does it tell you about the platform?
3. One model call in a turn reports 10 times the tokens of the rest. How do you find out why, and how would you catch it before it reaches the bill?

### 2026-11-09: Ops Analytics as a Genie agent on gold

**What we built:** the Genie agent *Sanad Ops Analytics* over `gold.delivery_sla_by_region`.
- **Definition and deploy:** the space is defined in [genie/ops_analytics.geniespace.json](../../genie/ops_analytics.geniespace.json). The bundle deploys it (`genie_spaces` in [databricks.yml](../../databricks.yml)) with `CAN_RUN` for `ops_managers`.
- **Check:** [evals/ops_genie.py](../../evals/ops_genie.py) asks "Which region had the most late deliveries last quarter, and why?". It passes when the answer names Jeddah and Red Sea Cargo and the SQL doesn't average `late_rate`. The rule is tested in [tests/test_ops_genie.py](../../tests/test_ops_genie.py).
- **Result:** passed twice on 2026-11-09. One query found Jeddah (414 of 2,559 late, 16.2%) and Red Sea Cargo (381 of 642, 59.3%).
- **Not yet bound to the agent:** the supervisor task does that.

These were written by Claude at my request; I must be able to defend them: the table choice, the column descriptions and synonyms, the three example SQLs, the two text-instruction sections, reading "last quarter" as the last complete calendar quarter, the `ops_managers`-only permission, and the check's facts.

**Key concepts:**
- **A Genie agent is a curated space.** It writes SQL from the question plus what we give it. In order of trust: the tables, column descriptions, example SQL, and text instructions as a last resort. Genie One searches everything, with no curation.
- **Non-additive measures:**
  - `late_rate` is per region × carrier × month, so a group's rate is `SUM(late) / SUM(delivered)`.
  - `AVG(late_rate)` gives a 10-delivery row the same weight as a 600-delivery row.
  - On this data the two agree to one decimal place, because the rows are similar in size. So the check reads the SQL, not just the number.
- **Examples teach a query shape, and the eval question stays unseen.** The example SQLs use other regions and periods, and the check asks the pitch question. Otherwise a pass would only prove Genie remembers its examples.
- **Chat-mode Genie writes one query per question.** A "why" needs the drill-down inside that query: a CTE finds the top region, then breaks it down by carrier.
- **When a text instruction is the right tool:** an example with a "why" question didn't change Genie's behavior, and one `DISAMBIGUATION` rule did. Text instructions are for rules that span questions and that no column or example can carry.
- **Genie spaces are bundle resources** in CLI v1.23: `genie_spaces`, with `file_path` pointing to a `.geniespace.json`. The Genie skill still described an export/import script. `bundle plan` showed 2 to add and 5 unchanged before the first deploy.
- **The serialized space is strict.** Every list item needs a 32-hex `id`, lists are sorted by `id`, and text fields are arrays of strings.
- **Development mode renames resources.** The space is titled "[dev ajmal] Sanad Ops Analytics", so the check matches the end of the title.

**Mistakes:**
- **The "why" failed twice.** The first run named Jeddah with the right formula but said the data showed no reason. Adding a "why" example SQL gave the same result. Adding the `DISAMBIGUATION` rule made it pass, and a repeat run passed too.
- **The summary rule isn't always followed.** One passing answer said "the last quarter covered by the query" instead of the month range. The check doesn't test this.
- **A badly built check question.** Claude's AVG-trap example used two Jeddah rows of equal size, so AVG and SUM/SUM agreed and the trap didn't show. It was redone with rows of unequal size.

**Interview questions:**
1. A Genie agent picks the right region but averages a rate column. Where do you fix it: the table, the space or the instructions? In what order, and why?
2. How do you evaluate a natural-language-to-SQL agent so that a pass doesn't just prove it memorized your examples?
3. Genie runs as the person asking. What does `CAN_RUN` on the space grant, and what still decides which rows they see?

### 2026-11-09: The supervisor routes to Customer Service and Ops Analytics

**What we built** ([ADR 0005](../adr/0005-supervisor-calls-specialists-as-tools.md)):
- **Supervisor:** [agent/agent/agent.py](../../agent/agent/agent.py).
  - The old agent is now the Customer Service sub-agent: the UC tools, its prompt and the `Answer` schema, wrapped as one tool, `customer_service(question)`.
  - The Genie agent is bound with `agentbricks tools add genie-agent <space id> --name ops_analytics --auth user`. That gives the supervisor `ops_analytics_ask`, `_poll` and `_query_result`.
- **Prompts:** the routing rules are in [prompts/supervisor.md](../../agent/agent/prompts/supervisor.md), registered as `sanad.prompts.supervisor@production` and bound with `agentbricks experimental prompts bind`. [prompt.py](../../agent/agent/prompt.py) loads and registers prompts by name.
- **Customer Service prompt, version 2:** the summary only counts issues, so look at the invoices; and a flagged record needs its policy before the answer.
- **Citations:**
  - a third type, `query`, cited by Genie's `deep_link`;
  - [answer.py](../../agent/agent/answer.py) now carries the specialists' citations over in code.
- **Tests:**
  - each prompt names the tools it owns;
  - a `query` citation is valid;
  - specialist citations are taken from the current turn only.
- **Results on the local agent:**
  - Gate A passed 4 of 4 with Customer Service prompt v2, against 1 of 3 with v1;
  - the Jeddah question went only to Genie;
  - a two-part question was split into two self-contained questions and the answers combined.
- **Deployed:** with `--allow-user-scope-update`, which added the `genie` user scope. Asked the Jeddah question, the deployed agent called only `ops_analytics_ask` and answered as me.

These were written by Claude at my request; I must be able to defend them: the routing rules, the `customer_service` tool description, the `query` citation and its `deep_link` reference, the two new Customer Service rules, and carrying citations over in code.

**Key concepts:**
- **Specialists as tools.** A specialist is a tool whose body is another agent, and the supervisor routes by reading tool descriptions.
  - A router node would cost one model call instead of three, but it can't send a two-part question to two specialists.
  - Genie is already an agent, so it needs no wrapper.
- **Stateless specialists.**
  - The sub-agent runs with `checkpointer=False`, so the supervisor has to write self-contained questions. In practice, "…and which carrier had the worst late-delivery rate in Jeddah last quarter?" went out as two complete questions.
  - `checkpointer=None` means "inherit the parent's"; `False` means "none".
- **A gate run once is a sample of one.** Gate A passed once on 2026-11-08. Today the same prompt, model and question passed 1 of 3. Run a gate several times; Phase 6 runs each eval case more than once.
- **Read the trace before changing anything.** All three failures came from the specialist stopping early (summary only, or no `search_policies`), not from routing. The `customer_service` span's output showed exactly what the supervisor received.
- **Copying is a model's weak spot, so code carries provenance.** The supervisor's format step was told to keep the specialists' citations and still dropped a policy when merging two answers. This is the same lesson as the answer schema: the fix is an extra step, not a hope.
- **The model picks the question, never the scope.** The Genie space id comes from `agent.toml`, and the credentials are the asking user's.

**Mistakes:**
- **LangGraph crash.** The first run failed with `'AsyncPregelLoop' object has no attribute '_put_checkpoint_fut'`. The nested graph inherited `durability="sync"` from `run_agent`, but with `checkpointer=False` it never starts a save. The server journal showed it. Fixed by passing `durability="async"` to the sub-agent.
- **Flaky Gate A.** It passed 1 of 3 until the two Customer Service rules were made explicit (version 2), then 4 of 4. These are small samples.
- **A dropped citation.** The supervisor's format step dropped the specialist's policy citation on a two-part question. It's now merged in code.
- **Still open: the specialist under-cites.** In one run the Customer Service format step cited only one of the two duplicate invoices. Gate A passed regardless. Left for a Phase 6 citation scorer.
- **The supervisor misread a percentage.** On the deployed run it wrote "381 of those late shipments (59.3% of Jeddah's deliveries)". 59.3% is Red Sea Cargo's own late rate (381 of 642); 381 of Jeddah's 2,559 deliveries is 14.9%. Genie's numbers were right, and the rewording broke them. Left for the Phase 6 correctness judge.
- **Deploy into starting compute.** Claude started the app with `--no-wait` and deployed straight away, so the scope update failed: "Could not reconcile Apps user scopes". Calling the same Apps API directly showed the real cause: compute must be `ACTIVE` or `STOPPED` to update. Waited for `ACTIVE`, then redeployed.
- **Stale systemd unit.** Yesterday's local-server unit was left "failed": exit 143 when stopped. That blocked a new start until `systemctl --user reset-failed sanad-agent-dev`.

**Interview questions:**
1. Router node or specialists as tools: when would you choose each, and what does each cost per question?
2. Your specialist agents are stateless, and a user asks a follow-up that says "it". Where does that get resolved, and how would you test it?
3. A gate passed yesterday and fails 2 of 3 today with no code change. What do you conclude, and what changes in how you run gates?
