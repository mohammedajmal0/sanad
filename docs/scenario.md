# Scenario and agents

Sanad serves **Najm Supply Co.**, a fictional B2B distributor based in Riyadh. It has CRM, ERP and IT service-desk systems, all filled with synthetic data. Three business pain points become three specialist agents behind one supervisor. Together they match the JD's list of CRM, ERP, service management and collaboration systems.

## The agents

| Agent | Users | Example request | Data and tools | Action it can take |
|---|---|---|---|---|
| Customer Service | Account managers, support | "Why was Al-Faris Trading invoiced twice in September, and is their shipment late?" | ERP orders, invoices, shipments (UC function tools); returns and SLA policy PDFs (retrieval); CRM account | Draft a credit note or open a case, only after a human approves |
| Ops Analytics | Managers | "Which region had the most late deliveries last quarter, and why?" | Gold tables through a Genie agent (natural language to SQL); metric definitions | Read-only |
| Service Desk | IT support | "VPN keeps dropping since Monday's update" | Past tickets (similar-incident search); KB articles (retrieval); mock ITSM REST API | Create, update or route a ticket, after approval |
| Supervisor | Everyone | Multi-part questions that need two agents | Routes, combines answers, asks clarifying questions | Posts a summary to a mock Teams channel |

## Synthetic data (Phase 1)

The sizes are kept small enough for Free Edition compute.

| Source | Volume | Shape | Why |
|---|---|---|---|
| CRM | about 2,000 customer accounts with contacts | Batch tables | There is PII to mask |
| ERP | about 50,000 orders with invoices and shipments | Batch tables | Holds the seeded billing and delivery problems |
| ITSM | about 10,000 tickets | JSON events landing in a UC volume over time | Practice for streaming ingestion |
| Documents | 30 to 40 policy and KB files | PDF, DOCX, Markdown | Retrieval corpus; a few in Arabic as a stretch goal |

## Seeded problems are the ground truth

The seeded problems are what the evaluation set checks against. They prove the agent finds the duplicate invoice, rather than just sounding confident.

| Seeded problem | Where it lives | Which agent must find it |
|---|---|---|
| Duplicate invoices (e.g. Al-Faris Trading, September) | ERP invoices → `gold.invoice_issues` | Customer Service |
| Late shipments | ERP shipments → `gold.delivery_sla_by_region` | Customer Service, Ops Analytics |
| VPN incident cluster after an update | ITSM ticket stream → `gold.ticket_trends` | Service Desk |
