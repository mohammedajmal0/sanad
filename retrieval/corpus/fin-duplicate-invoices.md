# Duplicate Invoice Handling Procedure

## What counts as a duplicate

An order should be invoiced exactly once. When two or more invoices bill the same order number, every invoice after the first is a duplicate, even when the amounts differ slightly. Duplicates usually come from an ERP retry after a timeout, or from an invoice that was manually re-created.

## Detection

The invoice issues report flags every invoice on an order that has more than one invoice, with the issue type "duplicate". Finance reviews the report every business morning.

## Steps when a duplicate is found

1. Put a dunning hold on the duplicate invoice so the customer receives no payment reminders for it.
2. Confirm with the account manager which invoice the customer received first. That one stays valid.
3. If the duplicate has not been paid, cancel it in the ERP with reason code DUP.
4. If the duplicate has been paid, issue a credit note with reason code DUP under the Credit Note and Refund Policy, and agree on a refund or offset with the customer.
5. Tell the customer within 2 business days of detection, before they find it themselves.
6. Open an ERP ticket so the IT team can find the root cause.

## Ownership

The accounts receivable supervisor owns this procedure and reports the number of duplicates found each month to the finance manager.
