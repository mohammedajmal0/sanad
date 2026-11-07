# Use-case canvas and scoring

Six candidate use cases for Najm Supply Co., each scored on four criteria. Three go forward. This is the record you'd produce after a discovery workshop.

Candidates 1 to 3 are the pain points named in the [scenario](../scenario.md). Candidates 4 to 6, the risks, value metrics, scores, picks and rejection reasons were drafted by Claude at my request on 2026-11-07; I must be able to defend them. Baseline minutes are estimates, labelled as such, until timed runs replace them in Phase 7.

## Canvas

For each candidate, decide whether it needs an **agent** (multi-step, tool choice, actions), a **workflow** (fixed steps, no model choice), or **plain retrieval** (answer from documents). Not everything should be an agent.

### 1. Billing and delivery questions for account managers

| Field | |
|---|---|
| Problem | Account managers search three systems (CRM, ERP, policy PDFs) to answer one billing question |
| Users | Account managers, support |
| Data | ERP orders, invoices, shipments; CRM accounts; returns and SLA policies |
| Actions | Draft a credit note or open a case, after approval |
| Risks | A wrong credit note costs real money; a confident answer about the wrong customer; contact PII leaking across regions. Controls: human approval before any write, region row filter and PII mask (Phase 2), every answer cites the invoice IDs and the policy passage |
| Value metric | Minutes per billing question (about 20 today, estimated; target under 3); duplicate invoices caught before the customer calls |
| Agent, workflow or retrieval? | **Agent.** It has to pick tools (invoices, shipments, policy search), chain them, and propose an action |

### 2. Delivery performance analytics for managers

| Field | |
|---|---|
| Problem | Managers wait on analysts for questions like "which region had the most late deliveries last quarter, and why?" |
| Users | Ops managers |
| Data | Gold tables (delivery SLA by region, orders); metric definitions |
| Actions | None (read-only) |
| Risks | Plausible but wrong SQL, e.g. averaging rates instead of `sum(late) / sum(delivered)`; stale numbers between pipeline runs. Controls: governed metric definitions, show the SQL with every answer, a "data as of" time |
| Value metric | Analyst requests avoided per week; time to answer from days to minutes |
| Agent, workflow or retrieval? | **Retrieval over data**: a Genie agent (natural language to SQL) on gold. No custom multi-tool agent, because there are no actions and one tool covers it |

### 3. IT service-desk triage

| Field | |
|---|---|
| Problem | IT support re-solves incidents that already have a known fix, e.g. "VPN keeps dropping since Monday's update" |
| Users | IT support |
| Data | Past tickets; KB articles; ITSM API |
| Actions | Create, update or route a ticket, after approval |
| Risks | A wrong fix applied to many machines; mass ticket creation during an incident; routing to the wrong team. Controls: approval for every write, a rate limit on ticket creation, the KB article linked in every suggestion |
| Value metric | Time to resolve repeat incidents; share of tickets closed with a KB link |
| Agent, workflow or retrieval? | **Agent.** It searches similar incidents and the KB, then chooses between create, update and route |

### 4. Supplier invoice capture for accounts payable

| Field | |
|---|---|
| Problem | AP clerks key supplier invoice PDFs into the ERP by hand |
| Users | Accounts payable |
| Data | Supplier invoice PDFs, ERP purchase orders |
| Actions | Create draft AP entries for review |
| Risks | A misread amount posts straight to the ledger; supplier bank details are sensitive |
| Value metric | Keying hours saved per month; posting error rate |
| Agent, workflow or retrieval? | **Workflow**: `ai_extract` in a pipeline, then human review. Fixed steps, no tool choice |

### 5. Follow-up email drafts for account managers

| Field | |
|---|---|
| Problem | Account managers write the same follow-up emails after orders and complaints |
| Users | Account managers |
| Data | CRM accounts and contacts, order history |
| Actions | Draft an email for the manager to send |
| Risks | Promises the company can't keep (discounts, dates); customer PII sent to a model |
| Value metric | Minutes saved per email |
| Agent, workflow or retrieval? | **Workflow**: one templated model call. No tool choice needed |

### 6. Stock demand forecasting

| Field | |
|---|---|
| Problem | Warehouses run out of fast-moving items before reorders arrive |
| Users | Warehouse and purchasing managers |
| Data | Order lines per SKU, stock levels (neither exists in Najm's data today) |
| Actions | Suggest reorder quantities |
| Risks | Over-ordering ties up cash; a forecast trusted without its error band |
| Value metric | Stock-out days per month; inventory carrying cost |
| Agent, workflow or retrieval? | **Neither**: a forecasting model (`ai_forecast` or ML), not an agent |

## Scoring

Scale is 1 to 5 for each criterion. **Risk is scored as safety: 5 = lowest risk**, so a higher number is always better. Total = 2 × Value + Feasibility + Data readiness + Risk (maximum 25). Value counts double because it is the reason to build at all; the other three only say whether we can.

| # | Use case | Value | Feasibility | Data readiness | Risk | Total | Picked |
|---|---|---|---|---|---|---|---|
| 1 | Billing and delivery questions | 5 | 4 | 4 | 3 | 21 | ✓ |
| 2 | Delivery performance analytics | 4 | 5 | 5 | 4 | 22 | ✓ |
| 3 | IT service-desk triage | 4 | 4 | 4 | 3 | 19 | ✓ |
| 4 | Supplier invoice capture | 3 | 4 | 2 | 2 | 14 | |
| 5 | Follow-up email drafts | 2 | 5 | 4 | 3 | 16 | |
| 6 | Stock demand forecasting | 4 | 3 | 1 | 4 | 16 | |

## Why the rejected cases lost

- **4. Supplier invoice capture:** sunk by data readiness and risk. Najm has no supplier invoice documents to train or test on, and a misread amount posts straight to the ledger. It returns when AP shares a sample of a few hundred real invoices, and even then it is a workflow, not an agent.
- **5. Follow-up email drafts:** sunk by value. It saves a few minutes on low-stakes emails, and a mail-merge template does most of it. It returns if account managers ask for drafts once the Customer Service agent is live.
- **6. Stock demand forecasting:** sunk by data readiness. There are no SKU-level order lines or stock levels, and it is a forecasting problem, not an agent. It returns when the ERP exposes order lines.
