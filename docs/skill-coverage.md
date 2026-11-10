# Skill coverage

Every responsibility and qualification in the JD has a concrete artifact you can point to. Use this table as the interview checklist. If a row's Evidence cell is still empty, that row is the next task.

| JD asks for | Where Sanad proves it | Phase | Evidence |
|---|---|---|---|
| Identify and prioritize use cases with stakeholders; discovery workshops | Use-case canvas for 6 candidates, value-versus-feasibility scoring, one-page roadmap | 0 | |
| Databricks, Spark, SQL, Delta Lake, medallion, batch and streaming | Lakeflow declarative pipeline: Auto Loader bronze, cleaned silver, business gold; ticket stream | 1 | |
| Data quality, lineage, Unity Catalog, access controls, privacy, audit | Pipeline expectations, row filters, column masks on PII, tags, lineage graph, audit queries on system tables | 1, 2 | |
| Preparing enterprise data for AI: parsing, chunking, embeddings, metadata | Document parsing with `ai_parse_document`, chunking strategy comparison, metadata columns for filtering | 3 | |
| RAG and vector search over governed data | Databricks AI Search (formerly Vector Search) hybrid index with metadata filters and reranking | 3 | |
| Agents that call tools and APIs, apply business rules, run multi-step tasks safely | LangGraph supervisor with three specialists; Unity Catalog function tools; MCP tools; approval step before any write | 4, 5 | |
| Integrate with CRM, ERP, service management, collaboration | Mock CRM/ERP/ITSM REST API and mock Teams webhook, exposed to the agent as a custom MCP server | 5 | |
| Structured outputs, prompt engineering, memory, human-in-the-loop, failure handling | Pydantic output schemas, versioned prompts, Lakebase-backed conversation memory, retries and fallbacks | 4, 5 | |
| Evaluation of quality, factuality, relevance, latency, cost, safety, task completion | MLflow 3 evaluation: built-in judges, custom scorers for tool-call correctness and cost, red-team set | 6 | |
| Automated testing and monitoring of prompts, retrieval, tool use, regressions, incidents | pytest unit tests, evaluation gate in CI, production monitoring on traces, alert and runbook | 6, 7 | |
| Prototype to secure, observable production service | Agent deployed on Databricks Apps behind Unity AI Gateway, with tracing and rate limits | 7 | |
| Git, code review, CI/CD, infrastructure as code | Declarative Automation Bundles (formerly Asset Bundles) with dev and prod targets, GitHub Actions | 7 | |
| Guardrails, red teaming, responsible AI | Gateway guardrail policies (PII, prompt injection, unsafe content) plus your own adversarial test cases | 6, 7 | |
| LLM providers (Anthropic, OpenAI, Azure OpenAI) | Claude on Databricks-hosted endpoints; second model behind the same gateway for fallback | 4, 7 | |
| Containers, microservices, event-driven design | Mock enterprise services in Docker for local dev; ticket events as a stream | 1, 5 | |
| Document architecture, data flows, prompts, tools, procedures, limitations | `docs/` folder: architecture, decision records, runbook, agent card with known limitations | every phase | [docs/](.) |
| Coach internal teams | Reusable agent template plus a 30-minute "build your first agent" walkthrough | 8 | [agent-template.md](agent-template.md), [walkthrough.md](walkthrough.md) |
| Explain trade-offs to technical and non-technical audiences | Two demo scripts: a 5-minute business version and a 20-minute technical deep dive | 8 | [demo-scripts.md](demo-scripts.md) |
