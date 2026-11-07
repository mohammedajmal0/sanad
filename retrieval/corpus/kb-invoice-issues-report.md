# Reading the invoice issues report

## What it is

The invoice issues report lists every invoice that finance should check, one row per invoice, refreshed each time the data pipeline runs. Its source is the table gold.invoice_issues.

## Issue types

- duplicate: the invoice's order has two or more invoices. Every invoice of that order is listed, so you can see the pair. The column invoices_for_order shows how many invoices the order has.
- non_positive_amount: the invoice amount is zero or negative.
- future_dated: the invoice date is later than today.

## What to do next

Duplicates follow the Duplicate Invoice Handling Procedure. Zero, negative and future-dated invoices are usually keying errors: send them to the AR supervisor to correct in the ERP.

## Access

Ops managers can read the full report. Account managers see the number of open invoice issues per customer in the customer 360 view, limited to their own region.
