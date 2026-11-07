# Use-case roadmap

A one-page roadmap for Najm's three picked use cases, built from the [canvas and scoring](use-case-canvas.md). It's the first of the JD's "example outcomes in the first 12 months". Drafted by Claude at my request on 2026-11-07; I must be able to deliver the pitch without notes.

**Ship the read-only analytics first to earn trust with zero write risk, then the highest-value agent once retrieval and approvals exist, then the service desk once it can write tickets safely.**

| Horizon | Use case | Value metric | Depends on |
|---|---|---|---|
| Now | Ops Analytics: delivery questions in plain English (Genie agent on gold) | Time to answer "which region was late, and why" (days → minutes); analyst requests avoided | Gold tables and the region row filter (done, Phases 1–2) |
| Next | Customer Service: billing and delivery answers, credit notes after approval | Minutes per billing question (about 20 → under 3, estimated); duplicate invoices caught before the customer calls | Policy index (Phase 3), UC function tools and the approval step (Phases 4–5) |
| Later | Service Desk: triage with known fixes, tickets after approval | Time to resolve repeat incidents; share of tickets closed with a KB link | KB index (Phase 3), ITSM write API through MCP (Phase 5) |

## Two-minute pitch

Najm's account managers answer a billing question by opening three systems: the CRM, the ERP and a folder of policy PDFs. It takes about twenty minutes, and mistakes cost real money. In our data, Al-Faris Trading was billed twice for the same order, 1,440.71 riyals each time, and nobody noticed. At the same time, Jeddah's late-delivery rate jumped to 16% last quarter against under 2% everywhere else, most of it one carrier, and managers had to wait for an analyst to find that out.

Sanad is one assistant with three specialists. We ship the analytics part first: managers ask delivery questions in plain English and get the number and the SQL behind it. It's read-only, the data is already clean and governed, and it builds trust. Next comes the customer-service agent, which reads invoices, shipments and policies, explains the problem with evidence, and drafts a credit note that a person approves before anything is written. The service desk follows, reusing known fixes for repeat incidents like the VPN outage after Monday's update.

Success is measured, not claimed: billing answers in under three minutes instead of twenty, duplicates caught before the customer calls, and quality scores on a fixed test set in CI. The main risk is the agent being confidently wrong or showing data it shouldn't. That's controlled three ways: every write needs human approval, each user only sees their own region and no one sees personal data they don't need, and every answer cites its source.
