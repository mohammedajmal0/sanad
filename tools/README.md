# tools

Unity Catalog functions the agents call as tools. They run under UC permissions, so the agent never touches tables directly.

**Phase:** 4

## What goes here

- `get_customer_summary`, `get_invoices`, `get_shipment_status` for the Customer Service agent.
- More functions as Phase 5 needs them.

## You write

- TODO(human): every tool description. The model chooses tools by reading them.

## Done when

Gate A: the agent finds the seeded duplicate invoice, cites the refund policy, and the trace shows every tool call.
