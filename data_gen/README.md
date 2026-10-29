# data_gen

Synthetic CRM, ERP, ITSM data and documents for Najm Supply Co., with seeded problems. See [docs/scenario.md](../docs/scenario.md).

**Phase:** 1 (the document corpus in Phase 3)

## What goes here

- Faker generators for about 2,000 CRM accounts with contacts, and about 50,000 ERP orders with invoices and shipments.
- A ticket generator that writes about 10,000 ITSM JSON events into a Unity Catalog volume over time, to feed the stream.
- 30 to 40 policy and KB documents in PDF, DOCX and Markdown (a few in Arabic as a stretch goal).

## You write

- TODO(human): the seeded problems (which accounts get duplicate invoices, which shipments run late, when the VPN incident cluster starts). They are the ground truth for evaluation.

## Done when

The pipeline graph is green, expectation metrics are visible, and the seeded duplicate invoice appears in `gold.invoice_issues`.
